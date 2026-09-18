from __future__ import annotations

import json
import os
import shutil
import signal
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import pytest

from second_brain.local_engine import (
    Failed,
    NotInstalled,
    Ready,
    Starting,
    engine_state,
    ensure_ready,
    stop,
)
from second_brain.local_engine import engine, store
from second_brain.local_engine.engine import _reset, join_worker
from second_brain.local_engine.runtimes import Refused, Unavailable, edge0
from second_brain.local_engine.store import RunRecord, read_run_record, reset_memory

FAKE_CLI_DIR = Path(__file__).resolve().parent / "fake_edge0"
GB = 1024**3
APPLE_SILICON = edge0.Host(os="Darwin", arch="arm64", ram_bytes=32 * GB)

REAL_CLI = shutil.which("edge0")
REAL_CHECKPOINT = (os.getenv("EDGE0_8B_MODEL") or "").strip()


@pytest.fixture(autouse=True)
def _isolate_local_engine(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("LOCAL_ENGINE_RUNTIME", "edge0")
    monkeypatch.setenv("LLM_PROVIDER", "local")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("EDGE0_8B_MODEL", raising=False)
    monkeypatch.delenv("EDGE0_35B_MODEL", raising=False)
    monkeypatch.delenv("EDGE0_CLI", raising=False)
    monkeypatch.setenv("LOCAL_ENGINE_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("PATH", f"{FAKE_CLI_DIR}{os.pathsep}{os.environ['PATH']}")
    reset_memory()
    _reset()
    yield
    _reset()
    reset_memory()


def _checkpoint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "checkpoint"
    path.mkdir()
    (path / "config.json").write_text(json.dumps({"model_type": "edge0"}))
    monkeypatch.setenv("EDGE0_8B_MODEL", str(path))
    return path


def _cli_flags(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *flags: str) -> None:
    shim = tmp_path / "edge0-shim"
    shim.write_text(f'#!/bin/sh\nexec "{FAKE_CLI_DIR / "edge0"}" {" ".join(flags)} "$@"\n')
    shim.chmod(0o755)
    monkeypatch.setenv("EDGE0_CLI", str(shim))


def _apple_silicon(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(edge0, "_host", lambda: APPLE_SILICON)


def _restart_sidecar(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stand up a fresh sidecar process over a child that keeps running.

    A new process has no supervisor, no in-memory RunRecord, and no Popen
    handles. Only run.json and the child survive.
    """
    engine._supervisor._cancel.set()
    monkeypatch.setattr(store, "_run_record", None)
    monkeypatch.setattr(edge0, "_children", {})
    monkeypatch.setattr(engine, "_supervisor", engine._Supervisor())


def _await_record(timeout_s: float = 5.0) -> RunRecord:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        rec = read_run_record()
        if rec is not None:
            return rec
        time.sleep(0.02)
    raise AssertionError("supervisor wrote no RunRecord")


def test_capability_refuses_by_host():
    cli = "/usr/local/bin/edge0"
    assert edge0.capability_for(edge0.Host(os="Linux", arch="x86_64", ram_bytes=64 * GB), cli) == (
        Refused(reason="os", detail="Edge0 runs on macOS only. Use a cloud provider on this machine.")
    )
    assert edge0.capability_for(edge0.Host(os="Darwin", arch="x86_64", ram_bytes=64 * GB), cli) == (
        Refused(reason="arch", detail="Edge0 needs an Apple silicon Mac. This one is Intel.")
    )
    assert edge0.capability_for(edge0.Host(os="Darwin", arch="arm64", ram_bytes=8 * GB), cli) == (
        Refused(reason="memory", detail="Edge0 needs at least 16 GB of memory to run edge0-8b.")
    )
    assert edge0.capability_for(APPLE_SILICON, cli) == "ok"
    assert isinstance(edge0.capability_for(APPLE_SILICON, None), Unavailable)


def test_missing_cli_fails_precheck(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    _apple_silicon(monkeypatch)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    state = engine_state()
    assert isinstance(state, Failed)
    assert state.stage == "precheck"
    assert state.retryable is True
    assert "edge0" in state.message


def test_edge0_reaches_ready_with_fake_cli(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    _apple_silicon(monkeypatch)
    _checkpoint(tmp_path, monkeypatch)

    assert engine_state() == NotInstalled(model=edge0.EDGE0_8B.card, download_bytes=0)

    ensure_ready()
    join_worker()
    state = engine_state()
    assert isinstance(state, Ready), state
    assert state.model.id == "edge0-8b"

    rec = read_run_record()
    assert rec is not None
    assert urlparse(state.endpoint.base_url).port == rec.port
    with urllib.request.urlopen(f"{state.endpoint.base_url}/models", timeout=5) as resp:
        assert resp.status == 200
        assert json.loads(resp.read())["data"][0]["id"] == "edge0-8b"


def test_stop_kills_the_child(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    _apple_silicon(monkeypatch)
    _checkpoint(tmp_path, monkeypatch)

    ensure_ready()
    join_worker()
    rec = read_run_record()
    assert rec is not None

    assert stop() == NotInstalled(model=edge0.EDGE0_8B.card, download_bytes=0)
    with pytest.raises(ProcessLookupError):
        os.kill(rec.pid, 0)


def test_stop_is_idempotent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    _apple_silicon(monkeypatch)
    _checkpoint(tmp_path, monkeypatch)

    ensure_ready()
    join_worker()
    first = stop()
    assert stop() == first


def test_missing_checkpoint_offers_download_then_fails_on_weights(
    monkeypatch: pytest.MonkeyPatch,
):
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


def test_child_that_exits_fails_at_health_immediately(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    _apple_silicon(monkeypatch)
    _checkpoint(tmp_path, monkeypatch)
    _cli_flags(tmp_path, monkeypatch, "--die")
    monkeypatch.setenv("LOCAL_ENGINE_START_TIMEOUT_S", "30")

    ensure_ready()
    join_worker()
    state = engine_state()
    assert isinstance(state, Failed), state
    assert state.stage == "health"
    assert "failed to load checkpoint" in state.message


def test_wrong_served_model_is_not_ready(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    _apple_silicon(monkeypatch)
    _checkpoint(tmp_path, monkeypatch)
    _cli_flags(tmp_path, monkeypatch, "--serve-id", "other-model,third-model")
    monkeypatch.setenv("LOCAL_ENGINE_START_TIMEOUT_S", "30")

    ensure_ready()
    join_worker()
    state = engine_state()
    assert isinstance(state, Failed), state
    assert state.stage == "health"
    assert "other-model" in state.message


def test_lone_served_id_is_adopted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    _apple_silicon(monkeypatch)
    _checkpoint(tmp_path, monkeypatch)
    _cli_flags(tmp_path, monkeypatch, "--serve-id", "edge0-8b-mlx-q4")

    ensure_ready()
    join_worker()
    state = engine_state()
    assert isinstance(state, Ready), state
    assert state.model.id == "edge0-8b"


def test_run_json_records_the_live_child(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    _apple_silicon(monkeypatch)
    _checkpoint(tmp_path, monkeypatch)

    ensure_ready()
    join_worker()
    state = engine_state()
    assert isinstance(state, Ready), state

    saved = json.loads((store.home() / "run.json").read_text())
    assert saved["model_id"] == "edge0-8b"
    assert saved["runtime_version"] == "0"
    assert saved["port"] == urlparse(state.endpoint.base_url).port
    assert edge0.runtime.is_alive(saved["pid"]) is True


def test_restart_reattaches_to_the_running_child(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    _apple_silicon(monkeypatch)
    _checkpoint(tmp_path, monkeypatch)

    ensure_ready()
    join_worker()
    first = engine_state()
    assert isinstance(first, Ready), first
    rec = read_run_record()
    assert rec is not None

    _restart_sidecar(monkeypatch)

    again = engine_state()
    assert isinstance(again, Ready), again
    assert again.model.id == "edge0-8b"
    assert again.started_at == first.started_at
    assert urlparse(again.endpoint.base_url).port == rec.port
    assert read_run_record() == rec
    assert engine.worker_starts() == 0
    with urllib.request.urlopen(f"{again.endpoint.base_url}/models", timeout=5) as resp:
        assert json.loads(resp.read())["data"][0]["id"] == "edge0-8b"


def test_stop_after_restart_kills_the_adopted_child(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    _apple_silicon(monkeypatch)
    _checkpoint(tmp_path, monkeypatch)

    ensure_ready()
    join_worker()
    rec = read_run_record()
    assert rec is not None

    _restart_sidecar(monkeypatch)
    assert isinstance(engine_state(), Ready)

    assert stop() == NotInstalled(model=edge0.EDGE0_8B.card, download_bytes=0)
    assert edge0.runtime.is_alive(rec.pid) is False
    assert read_run_record() is None
    assert not (store.home() / "run.json").exists()


def test_restart_over_a_dead_child_reaps_the_record(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    _apple_silicon(monkeypatch)
    _checkpoint(tmp_path, monkeypatch)

    ensure_ready()
    join_worker()
    rec = read_run_record()
    assert rec is not None

    _restart_sidecar(monkeypatch)
    os.kill(rec.pid, signal.SIGKILL)
    os.waitpid(rec.pid, 0)

    assert engine_state() == NotInstalled(model=edge0.EDGE0_8B.card, download_bytes=0)
    assert read_run_record() is None
    assert not (store.home() / "run.json").exists()


def test_restart_mid_load_waits_instead_of_spawning_again(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    _apple_silicon(monkeypatch)
    _checkpoint(tmp_path, monkeypatch)
    _cli_flags(tmp_path, monkeypatch, "--load-s", "2")
    monkeypatch.setenv("LOCAL_ENGINE_START_TIMEOUT_S", "30")

    ensure_ready()
    rec = _await_record()

    _restart_sidecar(monkeypatch)
    starting = ensure_ready()
    assert isinstance(starting, Starting), starting
    assert starting.model.id == "edge0-8b"

    join_worker()
    state = engine_state()
    assert isinstance(state, Ready), state
    assert read_run_record() == rec
    assert urlparse(state.endpoint.base_url).port == rec.port


@pytest.mark.edge0_real
def test_edge0_real_checkpoint_serves(monkeypatch: pytest.MonkeyPatch):
    if not REAL_CHECKPOINT or REAL_CLI is None:
        pytest.skip("needs a real edge0 CLI and EDGE0_8B_MODEL")
    monkeypatch.setenv("EDGE0_8B_MODEL", REAL_CHECKPOINT)
    monkeypatch.setenv("EDGE0_CLI", REAL_CLI)

    ensure_ready()
    join_worker()
    state = engine_state()
    assert isinstance(state, Ready), state
    config = json.loads((Path(REAL_CHECKPOINT) / "config.json").read_text())
    assert state.model.context_window == config.get("max_position_embeddings")
