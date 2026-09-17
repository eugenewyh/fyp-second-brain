from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

UnsupportedReason = Literal["os", "arch", "memory"]
AcquireStep = Literal["runtime", "weights"]
Stage = Literal["precheck", "runtime", "weights", "spawn", "health"]


@dataclass(frozen=True, slots=True)
class Endpoint:
    base_url: str
    token: str
    _proof: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        from second_brain.local_engine.health import _ENDPOINT_PROOF

        if self._proof is not _ENDPOINT_PROOF:
            raise TypeError("Endpoint is minted only from a successful health parse")


@dataclass(frozen=True, slots=True)
class ModelCard:
    id: str
    display_name: str
    disk_bytes: int
    context_window: int
    active_params_b: float
    total_params_b: float


@dataclass(frozen=True, slots=True)
class Progress:
    done_bytes: int
    total_bytes: int
    bytes_per_s: float | None
    eta_s: float | None


@dataclass(frozen=True, slots=True)
class Unsupported:
    reason: UnsupportedReason
    detail: str


@dataclass(frozen=True, slots=True)
class NotInstalled:
    model: ModelCard
    download_bytes: int


@dataclass(frozen=True, slots=True)
class Acquiring:
    model: ModelCard
    step: AcquireStep
    progress: Progress


@dataclass(frozen=True, slots=True)
class Starting:
    model: ModelCard
    elapsed_s: float


@dataclass(frozen=True, slots=True)
class Ready:
    model: ModelCard
    endpoint: Endpoint
    started_at: float


@dataclass(frozen=True, slots=True)
class Failed:
    stage: Stage
    message: str
    retryable: bool


EngineState = Unsupported | NotInstalled | Acquiring | Starting | Ready | Failed
