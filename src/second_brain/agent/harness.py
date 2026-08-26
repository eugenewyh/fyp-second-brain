"""Shared run spec for Agent goals and Watch — allow-list + budget, then the graph."""

from __future__ import annotations

import os
import threading
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

RunKind = Literal["goal", "watch"]

_SCOPES = frozenset({"local", "hybrid", "web"})


@dataclass
class HarnessTools:
    web: bool = True
    arxiv: bool = True
    write_memory: bool = True

    def to_dict(self) -> dict[str, bool]:
        return asdict(self)


@dataclass
class RunSpec:
    kind: RunKind
    instruction: str
    project_path: str | None = None
    session_id: str | None = None
    claim_origin: str = "research"
    retrieval_scope: str = "hybrid"
    max_passes: int = 2
    min_confidence: float = 0.65
    persist_memory: bool = True
    also_project_paths: list[str] = field(default_factory=list)
    tools: HarnessTools = field(default_factory=HarnessTools)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "instruction": self.instruction,
            "project_path": self.project_path,
            "session_id": self.session_id,
            "claim_origin": self.claim_origin,
            "retrieval_scope": self.retrieval_scope,
            "max_passes": self.max_passes,
            "min_confidence": self.min_confidence,
            "persist_memory": self.persist_memory,
            "also_project_paths": list(self.also_project_paths),
            "tools": self.tools.to_dict(),
        }


class HarnessError(ValueError):
    """Harness ended without a result (or the stream reported an error)."""


def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() == "true"


def _env_int(name: str, default: int, *, lo: int = 1, hi: int = 4) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return max(lo, min(hi, int(str(raw).strip())))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return float(str(raw).strip())
    except ValueError:
        return default


def live_allow_list() -> HarnessTools:
    """Tool allow-list from live process env (settings writes refresh os.environ)."""
    return HarnessTools(
        web=_env_bool("ENABLE_WEB_SEARCH", True),
        arxiv=_env_bool("ENABLE_ARXIV", True),
        write_memory=_env_bool("AUTO_MEMORY", True),
    )


def live_max_passes(kind: RunKind) -> int:
    if kind == "watch":
        return _env_int("WATCH_MAX_PASSES", 1)
    return _env_int("MAX_GOAL_PASSES", 2)


def live_min_confidence() -> float:
    v = _env_float("MIN_GOAL_CONFIDENCE", 0.65)
    return max(0.0, min(1.0, v))


def clamp_scope(scope: str | None, *, web: bool) -> str:
    s = (scope or "hybrid").strip().lower()
    if s not in _SCOPES:
        s = "hybrid"
    if not web:
        return "local"
    return s


def resolve_run_spec(
    *,
    kind: RunKind,
    instruction: str,
    project_path: str | None = None,
    session_id: str | None = None,
    retrieval_scope: str | None = None,
    max_passes: int | None = None,
    min_confidence: float | None = None,
    persist_memory: bool | None = None,
    claim_origin: str | None = None,
    also_project_paths: list[str] | None = None,
) -> RunSpec:
    """Build a clamped spec. Request overrides win when provided; env fills the rest."""
    tools = live_allow_list()
    origin = claim_origin or ("watch" if kind == "watch" else "research")
    default_passes = live_max_passes(kind)
    if max_passes is None:
        passes = default_passes
    else:
        try:
            passes = max(1, min(4, int(max_passes)))
        except (TypeError, ValueError):
            passes = default_passes
    if min_confidence is None:
        min_c = live_min_confidence()
    else:
        try:
            min_c = max(0.0, min(1.0, float(min_confidence)))
        except (TypeError, ValueError):
            min_c = live_min_confidence()
    persist = tools.write_memory if persist_memory is None else (
        bool(persist_memory) and tools.write_memory
    )
    scope = clamp_scope(retrieval_scope, web=tools.web)
    return RunSpec(
        kind=kind,
        instruction=(instruction or "").strip(),
        project_path=project_path,
        session_id=session_id,
        claim_origin=origin,
        retrieval_scope=scope,
        max_passes=passes,
        min_confidence=min_c,
        persist_memory=persist,
        also_project_paths=list(also_project_paths or []),
        tools=tools,
    )


def run_harness_stream(
    spec: RunSpec,
    *,
    cancel_flag: threading.Event | None = None,
) -> Iterator[tuple[str, Any]]:
    """Run the research graph under this spec (multi-pass goal loop)."""
    from second_brain.agent.goal_loop import run_goal_stream

    yield from run_goal_stream(
        spec.instruction,
        retrieval_scope=spec.retrieval_scope,
        project_path=spec.project_path,
        session_id=spec.session_id,
        max_passes=spec.max_passes,
        min_confidence=spec.min_confidence,
        cancel_flag=cancel_flag,
        claim_origin=spec.claim_origin,
        persist_memory=spec.persist_memory,
        also_project_paths=spec.also_project_paths or None,
    )


def run_harness(spec: RunSpec) -> dict[str, Any]:
    """Blocking wrapper: last `complete` payload, or HarnessError."""
    final: dict[str, Any] | None = None
    error: str | None = None
    for kind, payload in run_harness_stream(spec):
        if kind == "complete" and isinstance(payload, dict):
            final = dict(payload)
        elif kind == "error":
            if isinstance(payload, dict):
                error = str(payload.get("message") or "Harness error")
            else:
                error = str(payload)
    if final is None:
        raise HarnessError(error or "Harness ended without a result")
    return final
