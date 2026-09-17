from __future__ import annotations

import os
import threading
import time

from .health import mint_endpoint
from .runtimes import Refused, resolve
from .runtimes.stub import AcquireCrash, AcquireCancelled
from .state import (
    Acquiring,
    EngineState,
    Failed,
    NotInstalled,
    Progress,
    Ready,
    Starting,
    Unsupported,
)
from .store import (
    InstallPlan,
    RunRecord,
    acquire,
    home,
    install_plan,
    reap_run_record,
    write_run_record,
)


def _target_model_id(runtime: object) -> str:
    catalog = runtime.catalog()  # type: ignore[attr-defined]
    wanted = (os.getenv("LLM_MODEL") or "").strip()
    if wanted and any(m.id == wanted for m in catalog):
        return wanted
    if catalog:
        return catalog[0].id
    return wanted


class _Supervisor:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: EngineState | None = None
        self._worker: threading.Thread | None = None

    def snapshot(self) -> EngineState:
        with self._lock:
            if self._worker is not None and self._worker.is_alive() and self._state is not None:
                return self._state
            if isinstance(self._state, (Failed, Ready)):
                return self._state
            return self._observe()

    def converge(self) -> EngineState:
        with self._lock:
            if self._worker is not None and self._worker.is_alive() and self._state is not None:
                return self._state
            if isinstance(self._state, Ready):
                return self._state
            runtime = resolve()
            cap = runtime.capability()
            if isinstance(cap, Refused):
                self._state = Unsupported(reason=cap.reason, detail=cap.detail)
                return self._state
            model_id = _target_model_id(runtime)
            if not model_id:
                self._state = Failed(
                    stage="precheck",
                    message="runtime catalog is empty",
                    retryable=True,
                )
                return self._state
            try:
                plan = install_plan(model_id, runtime)
            except KeyError:
                self._state = Failed(
                    stage="precheck",
                    message=f"unknown model {model_id}",
                    retryable=True,
                )
                return self._state
            done = plan.total_bytes - sum(a.size_bytes for a in plan.missing)
            self._state = Acquiring(
                model=plan.model,
                step="weights",
                progress=Progress(
                    done_bytes=done,
                    total_bytes=plan.total_bytes,
                    bytes_per_s=None,
                    eta_s=None,
                ),
            )
            if runtime.name == "stub":
                from .runtimes.stub import note_worker_start

                note_worker_start()
            self._worker = threading.Thread(
                target=self._run,
                args=(plan, runtime),
                daemon=True,
            )
            self._worker.start()
            return self._state

    def _observe(self) -> EngineState:
        runtime = resolve()
        cap = runtime.capability()
        if isinstance(cap, Refused):
            return Unsupported(reason=cap.reason, detail=cap.detail)
        model_id = _target_model_id(runtime)
        if not model_id:
            return Failed(
                stage="precheck",
                message="runtime catalog is empty",
                retryable=True,
            )
        try:
            plan = install_plan(model_id, runtime)
        except KeyError:
            return Failed(
                stage="precheck",
                message=f"unknown model {model_id}",
                retryable=True,
            )
        if plan.missing:
            return NotInstalled(model=plan.model, download_bytes=plan.total_bytes)
        return NotInstalled(model=plan.model, download_bytes=0)

    def _run(self, plan: InstallPlan, runtime: object) -> None:
        try:
            def on_progress(progress: Progress) -> None:
                with self._lock:
                    self._state = Acquiring(
                        model=plan.model,
                        step="weights",
                        progress=progress,
                    )

            if plan.missing:
                acquire(plan, on_progress)
            started = time.time()
            with self._lock:
                self._state = Starting(model=plan.model, elapsed_s=0.0)
            from .runtimes.stub import StubRuntime, models_payload, token as stub_token

            port = 9
            token = "stub-token"
            payload: object
            if isinstance(runtime, StubRuntime):
                token = stub_token()
                payload = models_payload(plan.model.id)
            else:
                raise RuntimeError("this unit only converges the stub runtime")
            pid = runtime.spawn(plan.model, home=home(), port=port, token=token)
            write_run_record(
                RunRecord(
                    pid=pid,
                    port=port,
                    token=token,
                    model_id=plan.model.id,
                    runtime_version=runtime.version,
                    started_at=started,
                )
            )
            endpoint = mint_endpoint(
                payload,
                expect_model=plan.model.id,
                base_url=f"http://127.0.0.1:{port}/v1",
                token=token,
            )
            with self._lock:
                self._state = Ready(
                    model=plan.model,
                    endpoint=endpoint,
                    started_at=started,
                )
        except AcquireCancelled:
            return
        except Exception as exc:
            stage = "weights" if isinstance(exc, AcquireCrash) else "spawn"
            with self._lock:
                self._state = Failed(stage=stage, message=str(exc), retryable=True)

    def stop(self) -> EngineState:
        from .runtimes.stub import clear_gate, stop_child

        stop_child()
        worker = self._worker
        if worker is not None:
            worker.join()
        clear_gate()
        reap_run_record()
        with self._lock:
            self._worker = None
            self._state = self._observe()
            return self._state


_supervisor = _Supervisor()


def engine_state() -> EngineState:
    """Current state. Cheap. At most one cached localhost health ping."""
    return _supervisor.snapshot()


def ensure_ready() -> EngineState:
    """Drive one step toward Ready and report where we are.

    Level-triggered. Returns immediately. Long work runs on a
    supervisor-owned thread. Concurrent callers join the same
    in-flight work. Reads LOCAL_ENGINE_RUNTIME at call time.
    Uses LLM_MODEL only when that id is in the runtime catalog.
    """
    return _supervisor.converge()


def stop() -> EngineState:
    """Stand down. Terminate the child and cancel any in-flight acquisition.

    Partial downloads stay so a later ensure_ready resumes them.
    """
    return _supervisor.stop()


def join_worker() -> None:
    worker = _supervisor._worker
    if worker is not None:
        worker.join()


def _reset() -> None:
    global _supervisor
    from .runtimes.stub import clear_gate, stop_child

    stop_child()
    worker = _supervisor._worker
    if worker is not None:
        worker.join()
    clear_gate()
    _supervisor = _Supervisor()
