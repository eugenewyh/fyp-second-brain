from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import threading
import time
import urllib.request
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .state import ModelCard, Progress

if TYPE_CHECKING:
    from .runtimes import Runtime

OBJECTS_DIR = "objects"
PARTIAL_DIR = "partial"
LAYOUTS_DIR = "layouts"
MANIFEST_NAME = "manifest.json"
RUN_RECORD_NAME = "run.json"
SPAWN_LOCK_NAME = "spawn.lock"

_CHUNK_BYTES = 1 << 20
_HTTP_TIMEOUT_S = 30.0


@dataclass(frozen=True, slots=True)
class Artifact:
    name: str
    sha256: str
    size_bytes: int
    url: str


@dataclass(frozen=True, slots=True)
class InstallPlan:
    model: ModelCard
    missing: tuple[Artifact, ...]
    total_bytes: int


@dataclass(frozen=True, slots=True)
class RunRecord:
    pid: int
    port: int
    token: str
    model_id: str
    runtime_version: str
    started_at: float


_memory_bytes: dict[str, int] = {}
_run_record: RunRecord | None = None


class AcquireCrash(Exception):
    pass


class AcquireCancelled(Exception):
    pass


class AcquireError(Exception):
    """Disk acquire failed. The supervisor maps this to Failed(stage="weights")."""


class ShaMismatch(AcquireError):
    def __init__(self, *, name: str, expected: str, actual: str) -> None:
        super().__init__(f"{name} hashed to {actual}, expected {expected}")
        self.name = name
        self.expected = expected
        self.actual = actual


def home() -> Path:
    raw = (os.getenv("LOCAL_ENGINE_HOME") or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    from second_brain.config import data_root

    return data_root() / "local-engine"


def object_path(sha256: str) -> Path:
    return home() / OBJECTS_DIR / sha256


def partial_path(sha256: str) -> Path:
    return home() / PARTIAL_DIR / sha256


def layout_path(model_id: str) -> Path:
    return home() / LAYOUTS_DIR / model_id


def is_http_url(url: str) -> bool:
    return url.startswith(("http://", "https://"))


def remember_bytes(sha256: str, n: int) -> None:
    _memory_bytes[sha256] = n


def installed_bytes(sha256: str) -> int:
    if sha256 in _memory_bytes:
        return _memory_bytes[sha256]
    promoted = object_path(sha256)
    if promoted.is_file():
        return promoted.stat().st_size
    staging = partial_path(sha256)
    if staging.is_file():
        return staging.stat().st_size
    return 0


def install_plan(model_id: str, runtime: Runtime) -> InstallPlan:
    catalog = runtime.catalog()
    model = next((m for m in catalog if m.id == model_id), None)
    if model is None:
        raise KeyError(model_id)
    artifacts: tuple[Artifact, ...] = runtime.artifacts(model)
    missing = tuple(a for a in artifacts if installed_bytes(a.sha256) < a.size_bytes)
    total = sum(a.size_bytes for a in artifacts)
    return InstallPlan(model=model, missing=missing, total_bytes=total)


def acquire(
    plan: InstallPlan,
    on_progress: Callable[[Progress], None],
    *,
    runtime: Runtime,
    cancel: threading.Event,
) -> None:
    runtime.acquire(plan, on_progress, cancel=cancel)


def download_artifacts(
    plan: InstallPlan,
    on_progress: Callable[[Progress], None],
    *,
    cancel: threading.Event,
) -> None:
    """Fetch every missing artifact into objects/, resuming any partial/ bytes.

    Rerunning after a cancel, a crash, or a full success converges on the same
    objects/ contents, so the caller retries by calling this again.
    """
    settled = plan.total_bytes - sum(a.size_bytes for a in plan.missing)
    current = 0
    fetched = 0
    started = time.time()

    def report() -> None:
        done = settled + current
        elapsed = time.time() - started
        rate = fetched / elapsed if fetched and elapsed > 0 else None
        on_progress(
            Progress(
                done_bytes=done,
                total_bytes=plan.total_bytes,
                bytes_per_s=rate,
                eta_s=max(0, plan.total_bytes - done) / rate if rate else None,
            )
        )

    for artifact in plan.missing:
        if not is_http_url(artifact.url):
            raise AcquireError(f"{artifact.name} has no HTTP url to fetch: {artifact.url}")
        if cancel.is_set():
            raise AcquireCancelled()
        staging = partial_path(artifact.sha256)
        staging.parent.mkdir(parents=True, exist_ok=True)
        have = staging.stat().st_size if staging.is_file() else 0
        current = 0
        if have < artifact.size_bytes:
            request = urllib.request.Request(artifact.url)
            if have:
                request.add_header("Range", f"bytes={have}-")
            with urllib.request.urlopen(request, timeout=_HTTP_TIMEOUT_S) as response:
                # A server may ignore Range and answer 200 with the whole body, so
                # only a 206 lets us keep the bytes already on disk.
                current = have if response.status == 206 else 0
                with staging.open("ab" if current else "wb") as sink:
                    try:
                        while chunk := response.read(_CHUNK_BYTES):
                            sink.write(chunk)
                            current += len(chunk)
                            fetched += len(chunk)
                            report()
                            if cancel.is_set():
                                raise AcquireCancelled()
                    finally:
                        sink.flush()
                        os.fsync(sink.fileno())
            if current < artifact.size_bytes:
                raise AcquireError(
                    f"{artifact.name} stopped at {current} of {artifact.size_bytes} bytes"
                )
        _promote(artifact, staging)
        settled += artifact.size_bytes
        current = 0


def _promote(artifact: Artifact, staging: Path) -> None:
    digest = _sha256_file(staging)
    if digest != artifact.sha256:
        staging.unlink(missing_ok=True)
        raise ShaMismatch(name=artifact.name, expected=artifact.sha256, actual=digest)
    promoted = object_path(artifact.sha256)
    promoted.parent.mkdir(parents=True, exist_ok=True)
    os.replace(staging, promoted)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def materialize_layout(model_id: str, artifacts: tuple[Artifact, ...]) -> Path:
    """Lay verified objects out as the directory edge0 serve expects."""
    layout = layout_path(model_id)
    for artifact in artifacts:
        source = object_path(artifact.sha256)
        if not source.is_file():
            raise AcquireError(f"{artifact.name} is missing from the object store")
        target = layout / artifact.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.unlink(missing_ok=True)
        try:
            os.link(source, target)
        except OSError:
            shutil.copyfile(source, target)
    _replace_json(
        home() / MANIFEST_NAME,
        {
            "model_id": model_id,
            "files": [
                {"name": a.name, "sha256": a.sha256, "size_bytes": a.size_bytes}
                for a in artifacts
            ],
        },
    )
    return layout


def run_record_path() -> Path:
    return home() / RUN_RECORD_NAME


def read_run_record() -> RunRecord | None:
    if _run_record is not None:
        return _run_record
    return _parse_run_record(run_record_path())


def write_run_record(rec: RunRecord) -> None:
    global _run_record
    _run_record = rec
    _replace_json(run_record_path(), asdict(rec))


def _replace_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    staging.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(staging, path)


def reap_run_record() -> None:
    global _run_record
    _run_record = None
    run_record_path().unlink(missing_ok=True)


def _parse_run_record(path: Path) -> RunRecord | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(raw, dict):
        return None
    try:
        return RunRecord(
            pid=int(raw["pid"]),
            port=int(raw["port"]),
            token=str(raw["token"]),
            model_id=str(raw["model_id"]),
            runtime_version=str(raw["runtime_version"]),
            started_at=float(raw["started_at"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


@contextmanager
def acquire_spawn_lock() -> Iterator[None]:
    path = home() / SPAWN_LOCK_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield


def reset_memory() -> None:
    global _run_record
    _memory_bytes.clear()
    _run_record = None
