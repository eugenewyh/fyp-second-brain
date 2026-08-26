"""Structured self-critique schemas for the Verifier agent and UI."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class CritiqueSeverity(str, Enum):
    info = "info"
    minor = "minor"
    major = "major"
    blocking = "blocking"


# Closed set for S2 UI chips — extend only with review
CRITIQUE_CODES = (
    "invalid_citation",
    "academic_mislabel",
    "hallucination",
    "missing_evidence",
    "citation_error",
    "logical_gap",
    "other",
)


class CritiqueIssue(BaseModel):
    code: str = "other"
    severity: CritiqueSeverity = CritiqueSeverity.major
    message: str
    citation_indices: list[int] = Field(default_factory=list)


class CritiqueVerdict(str, Enum):
    approved = "approved"
    revise = "revise"


class StructuredCritique(BaseModel):
    verdict: CritiqueVerdict
    summary: str
    issues: list[CritiqueIssue] = Field(default_factory=list)
    grounding_passed: bool = True
    source: str  # "grounding" | "llm" | "forced_max_revisions"
    raw: str | None = None

    def free_text(self) -> str:
        """Analyst-facing free-text critique (legacy contract)."""
        return self.summary


class CritiqueRevision(BaseModel):
    revision_index: int
    critique: StructuredCritique
    analysis_char_count: int = 0
    analysis_excerpt: str = ""
    ts: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )

    def to_history_dict(self) -> dict:
        return self.model_dump(mode="json")
