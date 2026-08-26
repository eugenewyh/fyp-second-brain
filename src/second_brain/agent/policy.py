"""Deterministic tool gate for the supervisor. Code, not the model."""

from __future__ import annotations

import re
from typing import Literal

Job = Literal["file", "answer", "research", "refuse"]

_SEARCH_INTENT = re.compile(
    r"\b("
    r"look\s*up|looking\s*up|find\s+papers?|arxiv|search\s+the\s+web|"
    r"what['\u2019]?s\s+new|latest"
    r")\b",
    re.I,
)
_DEEPEN = re.compile(
    r"\b(go\s+deeper|dig\s+(in|into)|expand\s+on|more\s+sources|research\s+this)\b",
    re.I,
)
_SYNTHESIS = re.compile(
    r"\b("
    r"synthesi[sz]e|synthesis|stance\s+on|write[- ]?up|"
    r"literature\s+review|report\s+on|multi[- ]?part"
    r")\b",
    re.I,
)
_NOTES_INTENT = re.compile(
    r"\b("
    r"according to my notes|in my notes|from my notes|"
    r"my notes say|based on my notes|from my library|cite my notes"
    r")\b",
    re.I,
)
_QUESTION_START = re.compile(
    r"^(what|why|how|when|where|who|which|does|do|did|is|are|can|could|"
    r"should|would|explain|summarise|summarize|synthesi[sz]e|compare)\b",
    re.I,
)
_SENTENCE = re.compile(r"[.!?]+")


def has_search_intent(text: str) -> bool:
    return bool(_SEARCH_INTENT.search((text or "").strip()))


def has_notes_intent(text: str) -> bool:
    """User asked to stay grounded in vault notes (may still synthesise as research)."""
    return bool(_NOTES_INTENT.search((text or "").strip()))


def has_synthesis_intent(text: str) -> bool:
    """Multi-part stance / report — prefer Research over a one-shot Ask."""
    return bool(_SYNTHESIS.search((text or "").strip()))


def is_question(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if "?" in t:
        return True
    return bool(_QUESTION_START.match(t))


def is_long_dump(text: str) -> bool:
    """Same bar as the client: long paste, not a question or lookup."""
    t = (text or "").strip()
    if not t or has_search_intent(t) or is_question(t):
        return False
    paragraphs = [p for p in re.split(r"\n\s*\n", t) if len(p.strip()) > 40]
    return len(t) >= 800 or len(paragraphs) >= 3


def sentence_count(text: str) -> int:
    parts = [p.strip() for p in _SENTENCE.split(text or "") if p.strip()]
    return max(len(parts), 1 if (text or "").strip() else 0)


def research_allowed(text: str, *, matching_claim_count: int) -> bool:
    """Research with explicit lookup, in-topic deepen, or synthesis over notes."""
    if has_search_intent(text):
        return True
    if matching_claim_count > 0 and (
        _DEEPEN.search(text or "") or has_synthesis_intent(text)
    ):
        return True
    # Notes-grounded simple recall stays Ask — not Research.
    if has_notes_intent(text) and not has_synthesis_intent(text):
        return False
    return False


def force_file(*, text: str, has_attachments: bool) -> bool:
    if has_attachments:
        return True
    return is_long_dump(text)


def apply_policy(
    job: Job,
    *,
    text: str,
    matching_claim_count: int,
    has_attachments: bool = False,
    forced: bool = False,
) -> Job:
    """Clamp a proposed job to what policy allows.

    When ``forced`` is True (Shift+Tab / plus menu), keep the user's job unless
    attachments force Teach or Ask/Research has nothing to retrieve.
    """
    if force_file(text=text, has_attachments=has_attachments):
        return "file"
    if forced and job in {"file", "answer", "research"}:
        if job == "file":
            return "file"
        if job == "answer" and matching_claim_count <= 0:
            return "refuse"
        if (
            job == "research"
            and matching_claim_count <= 0
            and not has_search_intent(text)
        ):
            return "refuse"
        return job
    if has_search_intent(text):
        return "research"
    # Notes-grounded synthesis → research; plain recall → answer.
    if has_notes_intent(text):
        if matching_claim_count <= 0:
            return "refuse"
        if job == "research" and research_allowed(text, matching_claim_count=matching_claim_count):
            return "research"
        if has_synthesis_intent(text):
            return "research"
        return "answer"
    if job == "research":
        if research_allowed(text, matching_claim_count=matching_claim_count):
            return "research"
        return "refuse"
    if job == "answer":
        if matching_claim_count > 0:
            return "answer"
        return "refuse"
    if job == "file":
        if is_question(text) and not has_attachments:
            if has_synthesis_intent(text) and matching_claim_count > 0:
                return "research"
            return "answer" if matching_claim_count > 0 else "refuse"
        return "file"
    return "refuse"


def fallback_job(
    *,
    text: str,
    matching_claim_count: int,
    has_attachments: bool = False,
) -> Job:
    """Used when the fast model is unavailable."""
    if force_file(text=text, has_attachments=has_attachments):
        return "file"
    if has_search_intent(text):
        return "research"
    if has_synthesis_intent(text) and matching_claim_count > 0:
        return "research"
    if has_notes_intent(text):
        return "answer" if matching_claim_count > 0 else "refuse"
    if is_question(text):
        return "answer" if matching_claim_count > 0 else "refuse"
    t = (text or "").strip()
    if len(t) >= 160 or sentence_count(t) >= 2:
        return "file"
    return "answer" if matching_claim_count > 0 else "refuse"
