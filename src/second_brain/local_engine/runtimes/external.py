from __future__ import annotations

import os
import threading
from collections.abc import Callable
from pathlib import Path

from ..health import HealthReport
from ..state import ModelCard, Progress
from ..store import Artifact, InstallPlan, RunRecord
from . import Capability, Refused


class ExternalRuntime:
    name = "external"
    version = "0"

    def capability(self) -> Capability:
        if not (os.getenv("LOCAL_ENGINE_BASE_URL") or "").strip():
            return Refused(
                reason="os",
                detail="LOCAL_ENGINE_BASE_URL is not set",
            )
        return "ok"

    def catalog(self) -> tuple[ModelCard, ...]:
        return ()

    def artifacts(self, model: ModelCard) -> tuple[Artifact, ...]:
        del model
        return ()

    def acquire(
        self,
        plan: InstallPlan,
        on_progress: Callable[[Progress], None],
        *,
        cancel: threading.Event,
    ) -> None:
        del plan, on_progress, cancel
        raise NotImplementedError("external runtime adopt is not in this unit")

    def spawn(self, model: ModelCard, *, home: Path, port: int, token: str) -> int:
        del model, home, port, token
        raise NotImplementedError("external runtime adopt is not in this unit")

    def health(
        self,
        rec: RunRecord,
        *,
        expect_model: str,
        timeout_s: float,
    ) -> HealthReport:
        del rec, expect_model, timeout_s
        raise NotImplementedError("external runtime adopt is not in this unit")

    def terminate(self, pid: int) -> None:
        del pid

    def is_alive(self, pid: int) -> bool:
        del pid
        return False


runtime = ExternalRuntime()
