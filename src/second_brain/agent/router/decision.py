"""Unified routing decision — replaces split ManagerTurn routing + ActDecision."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

RouteKind = Literal["dispatch", "meta", "clarify"]
RouteTier = Literal["forced", "rule", "meta", "topic", "local", "llm", "fallback"]
RouteJob = Literal[
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
class RouteDecision:
    kind: RouteKind
    text: str
    job: RouteJob | None = None
    instruction: str | None = None
    retrieval_scope: Literal["local", "hybrid", "web"] | None = None
    route_tier: RouteTier = "fallback"
    confidence: float = 0.0
    reason: str = ""
    focus: AskFocus | None = None
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
            "job": self.job,
            "instruction": self.instruction,
            "retrieval_scope": self.retrieval_scope,
            "route_tier": self.route_tier,
            "confidence": self.confidence,
            "reason": self.reason,
            "focus": self.focus,
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
