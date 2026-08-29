"""Grok-style supervisor shim — delegates to route_act."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from second_brain.agent.policy import Job
from second_brain.agent.router.copy import REFUSE_MESSAGE
from second_brain.agent.router.recall import RecallSnapshot, recall_snapshot, topic_name
from second_brain.agent.router.turn import route_act

__all__ = [
    "REFUSE_MESSAGE",
    "ActDecision",
    "RecallSnapshot",
    "decide_act",
    "recall_snapshot",
    "topic_name",
]


@dataclass
class ActDecision:
    job: Job
    reason: str
    matching_claim_count: int
    topic: str
    refuse_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job": self.job,
            "reason": self.reason,
            "matching_claim_count": self.matching_claim_count,
            "topic": self.topic,
            "refuse_message": self.refuse_message,
        }


def decide_act(
    message: str,
    *,
    project_path: str | None = None,
    has_attachments: bool = False,
    also_project_paths: list[str] | None = None,
    forced_job: Job | None = None,
    choose_fn=None,
) -> ActDecision:
    """Recall, pick a job, clamp with policy — via unified router."""
    decision = route_act(
        message,
        project_path=project_path,
        has_attachments=has_attachments,
        also_project_paths=also_project_paths,
        forced_job=forced_job,
        choose_fn=choose_fn,
    )
    return ActDecision(
        job=decision.job or "refuse",  # type: ignore[arg-type]
        reason=decision.reason or (decision.job or ""),
        matching_claim_count=decision.matching_claim_count,
        topic=decision.topic,
        refuse_message=decision.refuse_message,
    )
