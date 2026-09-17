from __future__ import annotations

import hashlib
import threading
from collections.abc import Callable
from pathlib import Path

from ..health import HealthReport, parse_models_payload
from ..state import ModelCard, Progress
from ..store import AcquireCancelled, AcquireCrash, Artifact, InstallPlan, RunRecord, remember_bytes
from . import Capability

TINY_MOE = ModelCard(
    id="stub/tiny-moe",
    display_name="Stub Tiny MoE",
    disk_bytes=1024,
    context_window=2048,
    active_params_b=0.1,
    total_params_b=1.0,
)

_WEIGHTS_SHA = hashlib.sha256(b"stub/tiny-moe").hexdigest()
_WEIGHTS = Artifact(
    name="weights.bin",
    sha256=_WEIGHTS_SHA,
    size_bytes=TINY_MOE.disk_bytes,
    url="memory://stub/tiny-moe",
)

total_bytes = TINY_MOE.disk_bytes
bytes_refetched = 0
acquire_starts = 0

_have_bytes = 0
_instruction: str | None = None
_crash_frac = 0.0
_crash_step = "weights"
_instruction_event = threading.Event()
_lock = threading.Lock()
_pid = 0
_alive = False
_port = 9
_token = "stub-token"


class StubRuntime:
    name = "stub"
    version = "0"

    def capability(self) -> Capability:
        return "ok"

    def catalog(self) -> tuple[ModelCard, ...]:
        return (TINY_MOE,)

    def artifacts(self, model: ModelCard) -> tuple[Artifact, ...]:
        if model.id != TINY_MOE.id:
            return ()
        return (_WEIGHTS,)

    def acquire(
        self,
        plan: InstallPlan,
        on_progress: Callable[[Progress], None],
        *,
        cancel: threading.Event,
    ) -> None:
        run_acquire(plan, on_progress, cancel=cancel)

    def spawn(self, model: ModelCard, *, home: Path, port: int, token: str) -> int:
        del home
        global _pid, _alive, _port, _token
        _port = port
        _token = token
        _pid = 4242
        _alive = True
        return _pid

    def health(
        self,
        rec: RunRecord,
        *,
        expect_model: str,
        timeout_s: float,
    ) -> HealthReport:
        del rec, timeout_s
        return parse_models_payload(
            models_payload(expect_model),
            expect_model=expect_model,
        )

    def terminate(self, pid: int) -> None:
        del pid
        stop_child()


runtime = StubRuntime()


def models_payload(model_id: str) -> dict[str, object]:
    return {
        "object": "list",
        "data": [
            {
                "id": model_id,
                "object": "model",
                "created": 0,
                "owned_by": "stub",
            }
        ],
    }


def is_alive(pid: int) -> bool:
    return _alive and pid == _pid


def port() -> int:
    return _port


def token() -> str:
    return _token


def run_acquire(
    plan: InstallPlan,
    on_progress: Callable[[Progress], None],
    *,
    cancel: threading.Event,
) -> None:
    global acquire_starts, bytes_refetched, _have_bytes, _instruction
    with _lock:
        acquire_starts += 1
    while not _instruction_event.wait(0.01):
        if cancel.is_set():
            raise AcquireCancelled()
    with _lock:
        instruction = _instruction
        frac = _crash_frac
        step = _crash_step
        have = _have_bytes
        _instruction = None
        _instruction_event.clear()
    if instruction != "settle" and instruction != "crash":
        raise AcquireCancelled()
    if instruction == "crash":
        target = int(plan.total_bytes * frac)
        take = max(0, target - have)
        have += take
        _have_bytes = have
        bytes_refetched = take
        remember_bytes(_WEIGHTS_SHA, have)
        on_progress(
            Progress(
                done_bytes=have,
                total_bytes=plan.total_bytes,
                bytes_per_s=None,
                eta_s=None,
            )
        )
        raise AcquireCrash(f"crashed during {step} at {frac}")
    take = plan.total_bytes - have
    _have_bytes = plan.total_bytes
    bytes_refetched = take
    remember_bytes(_WEIGHTS_SHA, plan.total_bytes)
    on_progress(
        Progress(
            done_bytes=plan.total_bytes,
            total_bytes=plan.total_bytes,
            bytes_per_s=None,
            eta_s=None,
        )
    )


def settle() -> None:
    global _instruction
    with _lock:
        _instruction = "settle"
        _instruction_event.set()
    _join_supervisor()


def crash_during(*, step: str, at_fraction: float) -> None:
    global _instruction, _crash_frac, _crash_step
    with _lock:
        _instruction = "crash"
        _crash_frac = at_fraction
        _crash_step = step
        _instruction_event.set()
    _join_supervisor()


def reset() -> None:
    global bytes_refetched, acquire_starts, _have_bytes
    global _instruction, _crash_frac, _crash_step, _pid, _alive
    with _lock:
        bytes_refetched = 0
        acquire_starts = 0
        _have_bytes = 0
        _instruction = "cancel"
        _crash_frac = 0.0
        _crash_step = "weights"
        _pid = 0
        _alive = False
        _instruction_event.set()
    _join_supervisor()
    clear_gate()
    from ..store import reset_memory

    reset_memory()


def stop_child() -> None:
    global _alive, _instruction
    with _lock:
        _alive = False
        _instruction = "cancel"
        _instruction_event.set()


def clear_gate() -> None:
    global _instruction
    with _lock:
        _instruction = None
        _instruction_event.clear()


def _join_supervisor() -> None:
    from second_brain.local_engine.engine import join_worker

    join_worker()
