"""Process-wide locks for Chroma writes and per-topic file ingest."""

from __future__ import annotations

import threading

chroma_write_lock = threading.Lock()

_ingest_locks: dict[str, threading.RLock] = {}
_ingest_guard = threading.Lock()


def ingest_lock(project_path: str | None) -> threading.RLock:
    """Return a lock for claim/learning file writes in one topic folder."""
    key = (project_path or "").strip().rstrip("/\\") or "__none__"
    with _ingest_guard:
        lock = _ingest_locks.get(key)
        if lock is None:
            lock = threading.RLock()
            _ingest_locks[key] = lock
        return lock
