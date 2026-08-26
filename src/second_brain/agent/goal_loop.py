"""Multi-pass goal supervisor around the research graph."""

from __future__ import annotations

import logging
import threading
from collections.abc import Iterator
from typing import Any

from second_brain.config import MAX_GOAL_PASSES, MIN_GOAL_CONFIDENCE
from second_brain.memory.learning import extract_open_questions

logger = logging.getLogger(__name__)


def _should_continue(
    *,
    pass_index: int,
    max_passes: int,
    confidence: float,
    min_confidence: float,
    open_questions: list[str],
) -> tuple[bool, str]:
    if pass_index >= max_passes:
        return False, "max_passes_reached"
    if confidence >= min_confidence and len(open_questions) < 2:
        return False, "goal_satisfied"
    if confidence >= min_confidence + 0.1:
        return False, "high_confidence"
    if not open_questions and confidence >= min_confidence - 0.05:
        return False, "no_open_questions"
    return True, "deepen_open_questions"


def _follow_up_query(goal: str, open_questions: list[str], prior_summary: str) -> str:
    qs = open_questions[:3]
    bullets = "\n".join(f"- {q}" for q in qs) if qs else "- Deepen coverage and evidence quality"
    prior = (prior_summary or "")[:800]
    return (
        f"{goal}\n\n"
        "Focus this pass on remaining gaps and open questions:\n"
        f"{bullets}\n\n"
        "Prior findings to build on (do not merely repeat):\n"
        f"{prior or '(see memory)'}"
    )


def run_goal_stream(
    goal: str,
    *,
    retrieval_scope: str = "hybrid",
    project_path: str | None = None,
    session_id: str | None = None,
    max_passes: int | None = None,
    min_confidence: float | None = None,
    cancel_flag: threading.Event | None = None,
    claim_origin: str = "research",
    persist_memory: bool = True,
    also_project_paths: list[str] | None = None,
) -> Iterator[tuple[str, Any]]:
    """
    Run up to max_passes research streams for a single user goal.

    Yields the same events as stream_research plus:
    - goal_pass {pass, max_passes, reason}
    - goal_status {status, passes, confidence, ...} before final complete
    """
    max_p = max(1, min(4, max_passes if max_passes is not None else MAX_GOAL_PASSES))
    min_c = min_confidence if min_confidence is not None else MIN_GOAL_CONFIDENCE
    goal = (goal or "").strip()
    if not goal:
        yield ("error", {"message": "goal must be non-empty"})
        return

    from second_brain.graph import stream_research

    passes: list[dict[str, Any]] = []
    query = goal
    prior_context: str | None = None

    for pass_i in range(1, max_p + 1):
        if cancel_flag is not None and cancel_flag.is_set():
            yield ("error", {"message": "Research cancelled"})
            return

        yield (
            "goal_pass",
            {
                "pass": pass_i,
                "max_passes": max_p,
                "reason": "initial" if pass_i == 1 else "deepen_open_questions",
                "query": query[:240],
                "detail": f"Goal pass {pass_i}/{max_p}",
            },
        )

        final: dict[str, Any] | None = None
        for kind, payload in stream_research(
            query,
            cancel_flag=cancel_flag,
            retrieval_scope=retrieval_scope,
            project_path=project_path,
            prior_context=prior_context,
            persist_memory=persist_memory,
            session_id=session_id,
            claim_origin=claim_origin,
            also_project_paths=also_project_paths,
        ):
            if kind == "complete":
                final = dict(payload) if isinstance(payload, dict) else {}
                # Defer complete until after goal decision
                continue
            if kind == "error":
                yield (kind, payload)
                return
            yield (kind, payload)

        if not final:
            yield ("error", {"message": "Goal pass ended without a result"})
            return

        conf = float(final.get("confidence") or 0.0)
        open_q = list(final.get("open_questions") or extract_open_questions(final.get("report") or ""))
        pass_summary = {
            "pass": pass_i,
            "query": query,
            "confidence": conf,
            "open_questions": open_q,
            "learning_path": final.get("learning_path"),
            "report_path": final.get("report_path"),
            "revision_count": final.get("revision_count", 0),
        }
        passes.append(pass_summary)

        cont, reason = _should_continue(
            pass_index=pass_i,
            max_passes=max_p,
            confidence=conf,
            min_confidence=min_c,
            open_questions=open_q,
        )

        if not cont or pass_i >= max_p:
            status = "completed" if conf >= min_c else "partial"
            if reason == "max_passes_reached" and conf < min_c:
                status = "partial"
            merged = {
                **final,
                "query": goal,
                "goal": goal,
                "goal_status": status,
                "goal_stop_reason": reason,
                "passes": passes,
                "pass_count": len(passes),
            }
            yield (
                "goal_status",
                {
                    "status": status,
                    "stop_reason": reason,
                    "pass_count": len(passes),
                    "max_passes": max_p,
                    "confidence": conf,
                    "detail": f"Goal {status} after {len(passes)} pass(es)",
                },
            )
            yield ("complete", merged)
            return

        # Prepare next pass
        prior_context = (final.get("report") or "")[:3500]
        query = _follow_up_query(goal, open_q, final.get("report") or "")
        logger.info("Goal continue pass %s → %s (%s)", pass_i, pass_i + 1, reason)
