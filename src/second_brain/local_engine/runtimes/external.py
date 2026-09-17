from __future__ import annotations

import os
from pathlib import Path

from ..state import ModelCard
from ..store import Artifact
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

    def spawn(self, model: ModelCard, *, home: Path, port: int, token: str) -> int:
        del model, home, port, token
        raise NotImplementedError("external runtime adopt is not in this unit")


runtime = ExternalRuntime()
