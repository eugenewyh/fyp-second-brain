from __future__ import annotations

import os
from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from pathlib import Path

from .state import ModelCard, Progress

OBJECTS_DIR = "objects"
PARTIAL_DIR = "partial"
MANIFEST_NAME = "manifest.json"


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


def install_plan(model_id: str, runtime: object) -> InstallPlan:
    catalog = runtime.catalog()  # type: ignore[attr-defined]
    model = next((m for m in catalog if m.id == model_id), None)
    if model is None:
        raise KeyError(model_id)
    artifacts: tuple[Artifact, ...] = runtime.artifacts(model)  # type: ignore[attr-defined]
    missing = tuple(a for a in artifacts if installed_bytes(a.sha256) < a.size_bytes)
    total = sum(a.size_bytes for a in artifacts)
    return InstallPlan(model=model, missing=missing, total_bytes=total)


def acquire(plan: InstallPlan, on_progress: Callable[[Progress], None]) -> None:
    from .runtimes import resolve

    runtime = resolve()
    if runtime.name == "stub":
        from .runtimes import stub as stub_mod

        stub_mod.run_acquire(plan, on_progress)
        return
    raise NotImplementedError("disk acquire is not in this unit")


def read_run_record() -> RunRecord | None:
    return _run_record


def write_run_record(rec: RunRecord) -> None:
    global _run_record
    _run_record = rec


def reap_run_record() -> None:
    global _run_record
    _run_record = None


def acquire_spawn_lock() -> AbstractContextManager[None]:
    return nullcontext()


def reset_memory() -> None:
    global _run_record
    _memory_bytes.clear()
    _run_record = None
