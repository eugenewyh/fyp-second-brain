from __future__ import annotations

import hashlib
import json
import os
import threading
import urllib.request
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from second_brain.local_engine import (
    Failed,
    NotInstalled,
    Ready,
    engine_state,
    ensure_ready,
    stop,
)
from second_brain.local_engine import store
from second_brain.local_engine.engine import _reset, join_worker
from second_brain.local_engine.runtimes import edge0
from second_brain.local_engine.store import (
    AcquireCancelled,
    Artifact,
    download_artifacts,
    home,
    install_plan,
    object_path,
    partial_path,
    read_run_record,
    reset_memory,
)

FAKE_CLI_DIR = Path(__file__).resolve().parent / "fake_edge0"
GB = 1024**3
APPLE_SILICON = edge0.Host(os="Darwin", arch="arm64", ram_bytes=32 * GB)

CONFIG_BODY = b'{"model_type":"edge0-fake-88b"}\n'
WEIGHTS_BODY = b"edge0-tiny-wgts\n"
FILES = {"config.json": CONFIG_BODY, "weights.bin": WEIGHTS_BODY}
TOTAL_BYTES = 48


def test_the_fixtures_stay_tiny():
    assert (len(CONFIG_BODY), len(WEIGHTS_BODY)) == (32, 16)
    assert sum(len(b) for b in FILES.values()) == TOTAL_BYTES


@dataclass(frozen=True, slots=True)
class Origin:
    url: str
    requests: list[tuple[str, str | None]]


@pytest.fixture(autouse=True)
def _isolate_local_engine(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("LOCAL_ENGINE_RUNTIME", "edge0")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("EDGE0_8B_MODEL", raising=False)
    monkeypatch.delenv("EDGE0_35B_MODEL", raising=False)
    monkeypatch.delenv("EDGE0_CLI", raising=False)
    monkeypatch.setenv("LOCAL_ENGINE_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("PATH", f"{FAKE_CLI_DIR}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("LOCAL_ENGINE_START_TIMEOUT_S", "30")
    reset_memory()
    edge0.clear_test_catalog()
    _reset()
    yield
    _reset()
    edge0.clear_test_catalog()
    reset_memory()


@pytest.fixture
def serve():
    """Start loopback origins that answer Range and log what was asked for."""
    started: list[ThreadingHTTPServer] = []

    def start(bodies: dict[str, bytes]) -> Origin:
        log: list[tuple[str, str | None]] = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                asked = self.headers.get("Range")
                log.append((self.path, asked))
                body = bodies.get(self.path.lstrip("/"))
                if body is None:
                    self.send_error(404)
                    return
                first = 0
                if asked and asked.startswith("bytes="):
                    first = int(asked.removeprefix("bytes=").split("-")[0])
                tail = body[first:]
                self.send_response(206 if first else 200)
                if first:
                    self.send_header(
                        "Content-Range", f"bytes {first}-{len(body) - 1}/{len(body)}"
                    )
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(len(tail)))
                self.end_headers()
                self.wfile.write(tail)

            def log_message(self, *_args: object) -> None:
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        started.append(server)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return Origin(url=f"http://127.0.0.1:{server.server_port}", requests=log)

    yield start
    for server in started:
        server.shutdown()
        server.server_close()


def _catalog(origin: Origin, bodies: dict[str, bytes]) -> tuple[Artifact, ...]:
    return tuple(
        Artifact(
            name=name,
            sha256=hashlib.sha256(body).hexdigest(),
            size_bytes=len(body),
            url=f"{origin.url}/{name}",
        )
        for name, body in bodies.items()
    )


def _install(origin: Origin, bodies: dict[str, bytes] = FILES) -> tuple[Artifact, ...]:
    artifacts = _catalog(origin, bodies)
    edge0.install_test_catalog("edge0-8b", artifacts)
    return artifacts


def _apple_silicon(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(edge0, "_host", lambda: APPLE_SILICON)


def test_download_reaches_ready_over_http(monkeypatch: pytest.MonkeyPatch, serve):
    _apple_silicon(monkeypatch)
    origin = serve(dict(FILES))
    artifacts = _install(origin)

    assert engine_state() == NotInstalled(
        model=edge0.EDGE0_8B.card,
        download_bytes=TOTAL_BYTES,
    )

    ensure_ready()
    join_worker()
    state = engine_state()
    assert isinstance(state, Ready), state
    assert state.model.id == "edge0-8b"

    layout = store.layout_path("edge0-8b")
    for artifact, body in zip(artifacts, FILES.values(), strict=True):
        assert object_path(artifact.sha256).read_bytes() == body
        assert (layout / artifact.name).read_bytes() == body
        assert not partial_path(artifact.sha256).exists()

    assert json.loads((home() / "manifest.json").read_text()) == {
        "model_id": "edge0-8b",
        "files": [
            {"name": "config.json", "sha256": artifacts[0].sha256, "size_bytes": 32},
            {"name": "weights.bin", "sha256": artifacts[1].sha256, "size_bytes": 16},
        ],
    }

    rec = read_run_record()
    assert rec is not None
    assert edge0.runtime.is_alive(rec.pid) is True
    with urllib.request.urlopen(f"{state.endpoint.base_url}/models", timeout=5) as resp:
        assert json.loads(resp.read())["data"][0]["id"] == "edge0-8b"


def test_resume_asks_only_for_the_missing_range(monkeypatch: pytest.MonkeyPatch, serve):
    _apple_silicon(monkeypatch)
    origin = serve(dict(FILES))
    artifacts = _install(origin)

    staging = partial_path(artifacts[0].sha256)
    staging.parent.mkdir(parents=True, exist_ok=True)
    staging.write_bytes(CONFIG_BODY[:20])

    ensure_ready()
    join_worker()
    assert isinstance(engine_state(), Ready), engine_state()

    assert origin.requests == [
        ("/config.json", "bytes=20-"),
        ("/weights.bin", None),
    ]
    assert object_path(artifacts[0].sha256).read_bytes() == CONFIG_BODY


def test_cancel_between_chunks_keeps_the_partial(monkeypatch: pytest.MonkeyPatch, serve):
    origin = serve({"config.json": CONFIG_BODY})
    artifacts = _install(origin, {"config.json": CONFIG_BODY})
    monkeypatch.setattr(store, "_CHUNK_BYTES", 16)
    sha = artifacts[0].sha256

    cancel = threading.Event()
    with pytest.raises(AcquireCancelled):
        download_artifacts(
            install_plan("edge0-8b", edge0.runtime),
            lambda _progress: cancel.set(),
            cancel=cancel,
        )

    assert partial_path(sha).read_bytes() == CONFIG_BODY[:16]
    assert not object_path(sha).exists()

    download_artifacts(
        install_plan("edge0-8b", edge0.runtime),
        lambda _progress: None,
        cancel=threading.Event(),
    )
    assert object_path(sha).read_bytes() == CONFIG_BODY
    assert origin.requests == [
        ("/config.json", None),
        ("/config.json", "bytes=16-"),
    ]


def test_a_tampered_body_fails_on_weights(monkeypatch: pytest.MonkeyPatch, serve):
    _apple_silicon(monkeypatch)
    origin = serve({"config.json": CONFIG_BODY, "weights.bin": b"tampered-bytes!!"})
    artifacts = _install(origin)

    ensure_ready()
    join_worker()
    state = engine_state()
    assert isinstance(state, Failed), state
    assert state.stage == "weights"
    assert "weights.bin" in state.message
    assert not object_path(artifacts[1].sha256).exists()
    assert not partial_path(artifacts[1].sha256).exists()


def test_a_restart_serves_the_objects_without_refetching(
    monkeypatch: pytest.MonkeyPatch, serve
):
    _apple_silicon(monkeypatch)
    origin = serve(dict(FILES))
    _install(origin)

    ensure_ready()
    join_worker()
    assert isinstance(engine_state(), Ready), engine_state()
    assert len(origin.requests) == 2

    assert stop() == NotInstalled(model=edge0.EDGE0_8B.card, download_bytes=0)

    ensure_ready()
    join_worker()
    assert isinstance(engine_state(), Ready), engine_state()
    assert len(origin.requests) == 2


def test_a_checkpointless_tier_still_refuses_to_fetch(monkeypatch: pytest.MonkeyPatch):
    _apple_silicon(monkeypatch)

    assert engine_state() == NotInstalled(
        model=edge0.EDGE0_8B.card,
        download_bytes=4_200_000_000,
    )

    ensure_ready()
    join_worker()
    state = engine_state()
    assert isinstance(state, Failed), state
    assert state.stage == "weights"
    assert "EDGE0_8B_MODEL" in state.message
