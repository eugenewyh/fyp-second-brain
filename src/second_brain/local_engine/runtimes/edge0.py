from __future__ import annotations

from pathlib import Path

from ..state import ModelCard
from ..store import Artifact
from . import Capability, Refused


class Edge0Runtime:
    name = "edge0"
    version = "0"

    def capability(self) -> Capability:
        return Refused(
            reason="os",
            detail="Edge0 runtime is not implemented",
        )

    def catalog(self) -> tuple[ModelCard, ...]:
        return ()

    def artifacts(self, model: ModelCard) -> tuple[Artifact, ...]:
        del model
        return ()

    def spawn(self, model: ModelCard, *, home: Path, port: int, token: str) -> int:
        del model, home, port, token
        raise NotImplementedError("Edge0 CLI is not in this unit")


runtime = Edge0Runtime()
