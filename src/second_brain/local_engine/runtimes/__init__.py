from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from ..state import ModelCard, UnsupportedReason
from ..store import Artifact


@dataclass(frozen=True, slots=True)
class Refused:
    reason: UnsupportedReason
    detail: str


Capability = Literal["ok"] | Refused


class Runtime(Protocol):
    name: str
    version: str

    def capability(self) -> Capability: ...
    def catalog(self) -> tuple[ModelCard, ...]: ...
    def artifacts(self, model: ModelCard) -> tuple[Artifact, ...]: ...
    def spawn(self, model: ModelCard, *, home: Path, port: int, token: str) -> int: ...


def resolve() -> Runtime:
    """LOCAL_ENGINE_RUNTIME: edge0 (default) | external | stub. Read at call time."""
    name = (os.getenv("LOCAL_ENGINE_RUNTIME") or "edge0").strip().lower()
    if name == "stub":
        from .stub import runtime

        return runtime
    if name == "external":
        from .external import runtime

        return runtime
    from .edge0 import runtime

    return runtime
