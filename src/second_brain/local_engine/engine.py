from __future__ import annotations

import os
import secrets
import socket
import threading
import time

from .health import Exited, Malformed, Serving, WrongModel, mint_endpoint
from .runtimes import Refused, Runtime, Unavailable, resolve
from .state import (
    Acquiring,
    EngineState,
    Failed,
    NotInstalled,
    Progress,
    Ready,
    Stage,
    Starting,
    Unsupported,
)
from .store import (
    AcquireCancelled,
    InstallPlan,
    RunRecord,
    acquire,
    home,
    install_plan,
    read_run_record,
    reap_run_record,
    write_run_record,
)

DEFAULT_START_TIMEOUT_S = 180.0
_HEALTH_TIMEOUT_S = 2.0
_HEALTH_INTERVAL_S = 0.5


class HealthTimeout(Exception):
    pass


def _target_model_id(runtime: Runtime) -> str:
    catalog = runtime.catalog()
    wanted = (os.getenv("LLM_MODEL") or "").strip()
    if wanted and any(m.id == wanted for m in catalog):
        return wanted
    if catalog:
        return catalog[0].id
    return wanted


def _start_timeout_s() -> float:
    raw = (os.getenv("LOCAL_ENGINE_START_TIMEOUT_S") or "").strip()
    try:
        return float(raw) if raw else DEFAULT_START_TIMEOUT_S
    except ValueError:
        return DEFAULT_START_TIMEOUT_S


def _reserve_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class _Supervisor:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: EngineState | None = None
        self._worker: threading.Thread | None = None
        self._cancel = threading.Event()
        self.worker_starts = 0

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
            if isinstance(cap, Unavailable):
                self._state = Failed(stage="precheck", message=cap.detail, retryable=True)
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
            self.worker_starts += 1
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
        if isinstance(cap, Unavailable):
            return Failed(stage="precheck", message=cap.detail, retryable=True)
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

    def _run(self, plan: InstallPlan, runtime: Runtime) -> None:
        try:
            def on_progress(progress: Progress) -> None:
                with self._lock:
                    self._state = Acquiring(
                        model=plan.model,
                        step="weights",
                        progress=progress,
                    )

            if plan.missing:
                try:
                    acquire(plan, on_progress, runtime=runtime, cancel=self._cancel)
                except AcquireCancelled:
                    raise
                except Exception as exc:
                    self._fail("weights", str(exc))
                    return

            started = time.time()
            with self._lock:
                self._state = Starting(model=plan.model, elapsed_s=0.0)

            port = _reserve_port()
            token = secrets.token_urlsafe(32)
            pid = runtime.spawn(plan.model, home=home(), port=port, token=token)
            rec = RunRecord(
                pid=pid,
                port=port,
                token=token,
                model_id=plan.model.id,
                runtime_version=runtime.version,
                started_at=started,
            )
            write_run_record(rec)

            report = self._await_serving(rec, plan, runtime, started)
            endpoint = mint_endpoint(
                report,
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
        except HealthTimeout as exc:
            self._fail("health", str(exc))
        except Exception as exc:
            self._fail("spawn", str(exc))

    def _await_serving(
        self,
        rec: RunRecord,
        plan: InstallPlan,
        runtime: Runtime,
        started: float,
    ) -> Serving:
        deadline = started + _start_timeout_s()
        while True:
            report = runtime.health(
                rec,
                expect_model=plan.model.id,
                timeout_s=_HEALTH_TIMEOUT_S,
            )
            if isinstance(report, Serving):
                return report
            if isinstance(report, Exited):
                raise HealthTimeout(
                    f"{plan.model.id} exited with code {report.code}: {report.detail}"
                )
            if isinstance(report, WrongModel):
                raise HealthTimeout(
                    f"expected {plan.model.id}, server reports "
                    f"{', '.join(report.served_ids)}"
                )
            if isinstance(report, Malformed):
                raise HealthTimeout(f"malformed health response: {report.detail}")
            now = time.time()
            if now >= deadline:
                raise HealthTimeout(
                    f"{plan.model.id} did not serve within {_start_timeout_s():.0f}s"
                )
            if self._cancel.is_set():
                raise AcquireCancelled()
            with self._lock:
                self._state = Starting(model=plan.model, elapsed_s=now - started)
            time.sleep(_HEALTH_INTERVAL_S)

    def _fail(self, stage: Stage, message: str) -> None:
        with self._lock:
            self._state = Failed(stage=stage, message=message, retryable=True)

    def stop(self) -> EngineState:
        runtime = resolve()
        self._cancel.set()
        rec = read_run_record()
        if rec is not None:
            runtime.terminate(rec.pid)
        worker = self._worker
        if worker is not None:
            worker.join()
        reap_run_record()
        with self._lock:
            self._cancel = threading.Event()
            self._worker = None
            self._state = self._observe()
            return self._state


_supervisor = _Supervisor()


def engine_state() -> EngineState:
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


def worker_starts() -> int:
    return _supervisor.worker_starts


def _reset() -> None:
    global _supervisor
    _supervisor._cancel.set()
    rec = read_run_record()
    if rec is not None:
        resolve().terminate(rec.pid)
    worker = _supervisor._worker
    if worker is not None:
        worker.join()
    reap_run_record()
    _supervisor = _Supervisor()
