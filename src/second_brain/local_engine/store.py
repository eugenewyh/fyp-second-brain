from __future__ import annotations

import fcntl
import json
import os
import threading
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
MANIFEST_NAME = "manifest.json"
RUN_RECORD_NAME = "run.json"
SPAWN_LOCK_NAME = "spawn.lock"


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


def run_record_path() -> Path:
    return home() / RUN_RECORD_NAME


def read_run_record() -> RunRecord | None:
    if _run_record is not None:
        return _run_record
    return _parse_run_record(run_record_path())


def write_run_record(rec: RunRecord) -> None:
    global _run_record
    _run_record = rec
    path = run_record_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name(f"{RUN_RECORD_NAME}.{os.getpid()}.tmp")
    staging.write_text(json.dumps(asdict(rec)), encoding="utf-8")
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
