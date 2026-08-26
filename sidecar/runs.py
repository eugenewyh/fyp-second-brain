"""In-memory research run registry for plan → execute HITL."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from typing import Literal

RunStatus = Literal[
    "pending_approval",
    "executing",
    "completed",
    "cancelled",
    "expired",
]

TTL_SECONDS = 30 * 60  # 30 minutes
MAX_CONCURRENT_RUNS = 4


def _norm_project_path(project_path: str | None) -> str | None:
    if not project_path or not str(project_path).strip():
        return None
    return str(project_path).strip().rstrip("/\\")


@dataclass
class RunRecord:
    run_id: str
    query: str
    composed_query: str
    plan: str
    retrieval_queries: list[str]
    status: RunStatus
    created_at: float
    expires_at: float
    retrieval_scope: str = "hybrid"
    project_path: str | None = None
    session_id: str | None = None

    def public_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "query": self.query,
            "composed_query": self.composed_query,
            "plan": self.plan,
            "retrieval_queries": self.retrieval_queries,
            "status": self.status,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "retrieval_scope": self.retrieval_scope,
            "project_path": self.project_path,
            "session_id": self.session_id,
        }

    def is_expired(self, now: float | None = None) -> bool:
        return (now or time.time()) >= self.expires_at


class RunRegistry:
    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._lock = threading.Lock()
        # run_id -> project_path (None = unscoped). Includes auto-* tokens.
        self._active: dict[str, str | None] = {}
        # Daily-review scheduler: acquire/release may run on different threads.
        self._scheduler_token: str | None = None

    def gc(self) -> None:
        now = time.time()
        with self._lock:
            expired = [rid for rid, r in self._runs.items() if r.is_expired(now)]
            for rid in expired:
                rec = self._runs[rid]
                if rec.status == "pending_approval":
                    rec.status = "expired"
                if rec.status in {"expired", "completed", "cancelled"}:
                    del self._runs[rid]
                    self._active.pop(rid, None)

    def create(
        self,
        *,
        query: str,
        composed_query: str,
        plan: str,
        retrieval_queries: list[str],
        replace_run_id: str | None = None,
        retrieval_scope: str = "hybrid",
        project_path: str | None = None,
        session_id: str | None = None,
    ) -> RunRecord:
        self.gc()
        with self._lock:
            if replace_run_id and replace_run_id in self._runs:
                old = self._runs[replace_run_id]
                if old.status == "pending_approval":
                    old.status = "expired"
                    del self._runs[replace_run_id]
            now = time.time()
            run_id = uuid.uuid4().hex
            rec = RunRecord(
                run_id=run_id,
                query=query,
                composed_query=composed_query,
                plan=plan,
                retrieval_queries=list(retrieval_queries),
                status="pending_approval",
                created_at=now,
                expires_at=now + TTL_SECONDS,
                retrieval_scope=retrieval_scope,
                project_path=project_path,
                session_id=session_id,
            )
            self._runs[run_id] = rec
            return rec

    def get(self, run_id: str) -> RunRecord | None:
        self.gc()
        with self._lock:
            rec = self._runs.get(run_id)
            if not rec:
                return None
            if rec.is_expired() and rec.status == "pending_approval":
                rec.status = "expired"
                return rec
            return rec

    def begin_execute(self, run_id: str) -> tuple[RunRecord | None, str | None]:
        """Mark run executing. Returns (record, error_code).

        error_code: not_found | expired | bad_status | busy
        """
        self.gc()
        with self._lock:
            rec = self._runs.get(run_id)
            if not rec:
                return None, "not_found"
            if rec.status == "expired" or rec.is_expired():
                rec.status = "expired"
                return rec, "expired"
            if rec.status != "pending_approval":
                return rec, "bad_status"
            if len(self._active) >= MAX_CONCURRENT_RUNS:
                return rec, "busy"
            rec.status = "executing"
            self._active[run_id] = _norm_project_path(rec.project_path)
            return rec, None

    def finish(self, run_id: str, status: RunStatus = "completed") -> None:
        with self._lock:
            rec = self._runs.get(run_id)
            if rec:
                rec.status = status
            self._active.pop(run_id, None)

    def cancel(self, run_id: str) -> bool:
        self.gc()
        with self._lock:
            rec = self._runs.get(run_id)
            if not rec:
                return False
            if rec.status == "pending_approval":
                rec.status = "cancelled"
                del self._runs[run_id]
                return True
            return False

    def active_run_id(self) -> str | None:
        with self._lock:
            return next(iter(self._active), None)

    def active_run_ids(self) -> set[str]:
        with self._lock:
            return set(self._active)

    def topic_has_run(self, project_path: str | None) -> str | None:
        """Return an active run id for this topic, if any."""
        want = _norm_project_path(project_path)
        if not want:
            return None
        with self._lock:
            for rid, path in self._active.items():
                if path == want:
                    return rid
        return None

    def begin_auto(
        self, project_path: str | None = None
    ) -> tuple[str | None, str | None]:
        """Reserve a concurrent slot.

        Returns (token, busy_id). token is set on success; busy_id is set at cap.
        """
        with self._lock:
            if len(self._active) >= MAX_CONCURRENT_RUNS:
                return None, next(iter(self._active), "busy")
            token = f"auto-{uuid.uuid4().hex[:8]}"
            self._active[token] = _norm_project_path(project_path)
            return token, None

    def try_begin_auto(self, project_path: str | None = None) -> str | None:
        """Scheduler-compatible: None on success, busy run id at cap.

        Daily review is vault-wide, so this only fails at the concurrent cap —
        not because another topic's graph is running.
        """
        token, busy = self.begin_auto(project_path)
        if busy:
            return busy
        with self._lock:
            self._scheduler_token = token
        return None

    def end_auto(self, token: str | None = None) -> None:
        with self._lock:
            rid = token if token is not None else self._scheduler_token
            if token is None:
                self._scheduler_token = None
            if rid:
                self._active.pop(rid, None)


# Process-wide registry
RUNS = RunRegistry()
