from __future__ import annotations

import os
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol

from ..state import ModelCard, Progress, UnsupportedReason
from ..store import Artifact

if TYPE_CHECKING:
    from ..health import HealthReport
    from ..store import InstallPlan, RunRecord


@dataclass(frozen=True, slots=True)
class Refused:
    reason: UnsupportedReason
    detail: str


@dataclass(frozen=True, slots=True)
class Unavailable:
    detail: str


Capability = Literal["ok"] | Refused | Unavailable


class Runtime(Protocol):
    name: str
    version: str

    def capability(self) -> Capability: ...
    def catalog(self) -> tuple[ModelCard, ...]: ...
    def artifacts(self, model: ModelCard) -> tuple[Artifact, ...]: ...

    def acquire(
        self,
        plan: InstallPlan,
        on_progress: Callable[[Progress], None],
        *,
        cancel: threading.Event,
    ) -> None: ...

    def spawn(self, model: ModelCard, *, home: Path, port: int, token: str) -> int: ...

    def health(
        self,
        rec: RunRecord,
        *,
        expect_model: str,
        timeout_s: float,
    ) -> HealthReport: ...

    def terminate(self, pid: int) -> None: ...

    def is_alive(self, pid: int) -> bool: ...


def resolve() -> Runtime:
    name = (os.getenv("LOCAL_ENGINE_RUNTIME") or "stub").strip().lower()
    if name == "stub":
        from .stub import runtime

        return runtime
    if name == "external":
        from .external import runtime

        return runtime
    from .edge0 import runtime

    return runtime
