"""Grok-short router: dispatch when the task is clear; ask at most twice when vague."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from second_brain.agent.router.decision import RouteDecision
from second_brain.agent.router.turn import route_turn
from second_brain.agent.router.voice import apply_voice

ManagerKind = Literal["ask", "dispatch", "meta"]
ManagerJob = Literal[
    "file",
    "answer",
    "research",
    "refuse",
    "watch",
    "retarget",
    "merge",
    "split",
]
AskFocus = Literal["clarify", "confirm"]


@dataclass
class ManagerTurn:
    kind: ManagerKind
    text: str
    focus: AskFocus | None = None
    job: ManagerJob | None = None
    instruction: str | None = None
    retrieval_scope: Literal["local", "hybrid", "web"] | None = None
    reason: str = ""
    route_tier: str = ""
    confidence: float = 0.0
    refuse_message: str | None = None
    matching_claim_count: int = 0
    topic: str = ""
    create_topic: str = ""
    retarget_topic: str = ""
    merge_source: str = ""
    merge_dest: str = ""
    also_topics: list[str] = field(default_factory=list)
    also_project_paths: list[str] = field(default_factory=list)
    new_topic: str = ""
    idea: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "text": self.text,
            "focus": self.focus,
            "job": self.job,
            "instruction": self.instruction,
            "retrieval_scope": self.retrieval_scope,
            "reason": self.reason,
            "route_tier": self.route_tier,
            "confidence": self.confidence,
            "refuse_message": self.refuse_message,
            "matching_claim_count": self.matching_claim_count,
            "topic": self.topic,
            "create_topic": self.create_topic,
            "retarget_topic": self.retarget_topic,
            "merge_source": self.merge_source,
            "merge_dest": self.merge_dest,
            "also_topics": self.also_topics,
            "also_project_paths": self.also_project_paths,
            "new_topic": self.new_topic,
            "idea": self.idea,
        }


def _manager_kind(decision: RouteDecision) -> ManagerKind:
    if decision.kind == "clarify":
        return "ask"
    if decision.kind == "meta":
        return "meta"
    return "dispatch"


def _from_route(decision: RouteDecision) -> ManagerTurn:
    return ManagerTurn(
        kind=_manager_kind(decision),
        text=decision.text,
        focus=decision.focus,
        job=decision.job,  # type: ignore[arg-type]
        instruction=decision.instruction,
        retrieval_scope=decision.retrieval_scope,
        reason=decision.reason,
        route_tier=decision.route_tier,
        confidence=decision.confidence,
        refuse_message=decision.refuse_message,
        matching_claim_count=decision.matching_claim_count,
        topic=decision.topic,
        create_topic=decision.create_topic,
        retarget_topic=decision.retarget_topic,
        merge_source=decision.merge_source,
        merge_dest=decision.merge_dest,
        also_topics=list(decision.also_topics),
        also_project_paths=list(decision.also_project_paths),
        new_topic=decision.new_topic,
        idea=decision.idea,
    )


def take_turn(
    message: str,
    *,
    project_path: str | None = None,
    has_attachments: bool = False,
    clarify_count: int = 0,
    history: list[dict[str, str]] | None = None,
    topics: list[dict[str, str]] | None = None,
    forced_job: str | None = None,
) -> ManagerTurn:
    """One router turn. Thin wrapper over ``route_turn`` for API compat."""
    decision = route_turn(
        message,
        project_path=project_path,
        has_attachments=has_attachments,
        clarify_count=clarify_count,
        history=history,
        topics=topics,
        forced_job=forced_job,
    )
    decision = apply_voice(decision, user_message=message)
    return _from_route(decision)


__all__ = [
    "ManagerTurn",
    "take_turn",
]
