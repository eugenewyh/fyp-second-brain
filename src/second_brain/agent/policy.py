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
_RESEARCH_INTENT = re.compile(
    r"(?ix)"
    r"(^\s*research\b)"
    r"|(\b(?:investigate|explore|survey|deep\s+dive|write\s+(?:a\s+)?report)\b)"
    r"|(\b(?:file\s+(?:a\s+)?report|compile\s+(?:a\s+)?report|run\s+(?:a\s+)?report)\b)"
    r"|(\b(?:find\s+sources|gather\s+sources|source\s+review)\b)"
    r"|(\b(?:pros\s+and\s+cons|state\s+of\s+the\s+art|literature\s+review)\b)"
    r"|(\b(?:compare|contrast)\s+.+\s+(?:vs\.?|versus|and)\b)"
    r"|(\b(?:what\s+(?:are|is)\s+(?:the\s+)?(?:latest|current|recent))\b)"
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
# "Teach me about X" = explain from notes (Ask), not remember new notes (Teach/file).
_LEARN_INTENT = re.compile(
    r"\b("
    r"teach\s+me(?:\s+everything)?\s+about|"
    r"teach(?:\s+me)?\s+(?:everything\s+)?about|"
    r"walk\s+me\s+through|"
    r"help\s+me\s+(?:understand|learn)(?:\s+about|\s+what|\s+how|\s+why|\s+the|\s+everything|\s+all|\s+\w|$)|"
    r"explain\s+(?:to\s+me\s+)?(?:everything\s+)?about"
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


def has_research_intent(text: str) -> bool:
    """Mission-style research without explicit lookup verbs (Research chip / Auto)."""
    return bool(_RESEARCH_INTENT.search((text or "").strip()))


def has_notes_intent(text: str) -> bool:
    """User asked to stay grounded in vault notes (may still synthesise as research)."""
    return bool(_NOTES_INTENT.search((text or "").strip()))


def has_learn_intent(text: str) -> bool:
    """User wants an explanation from existing notes — not a Teach / remember dump."""
    return bool(_LEARN_INTENT.search((text or "").strip()))


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
    if not t or has_search_intent(t) or is_question(t) or has_learn_intent(t):
        return False
    paragraphs = [p for p in re.split(r"\n\s*\n", t) if len(p.strip()) > 40]
    return len(t) >= 800 or len(paragraphs) >= 3


def sentence_count(text: str) -> int:
    parts = [p.strip() for p in _SENTENCE.split(text or "") if p.strip()]
    return max(len(parts), 1 if (text or "").strip() else 0)


def research_allowed(text: str, *, matching_claim_count: int) -> bool:
    """Research with explicit lookup, mission phrasing, in-topic deepen, or synthesis."""
    if has_search_intent(text) or has_research_intent(text):
        return True
    if matching_claim_count > 0 and (
        _DEEPEN.search(text or "") or has_synthesis_intent(text)
    ):
        return True
    # Notes-grounded simple recall stays Ask — not Research.
    if (has_notes_intent(text) or has_learn_intent(text)) and not has_synthesis_intent(text):
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
        # Composer Research chip / forced research — user consent to look outside.
        if job == "research":
            return "research"
        return job
    if has_search_intent(text) or has_research_intent(text):
        return "research"
    # Notes-grounded synthesis → research; plain recall → answer.
    if has_notes_intent(text) or has_learn_intent(text):
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
        if (is_question(text) or has_learn_intent(text)) and not has_attachments:
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
    if has_search_intent(text) or has_research_intent(text):
        return "research"
    if has_synthesis_intent(text) and matching_claim_count > 0:
        return "research"
    if has_notes_intent(text) or has_learn_intent(text):
        return "answer" if matching_claim_count > 0 else "refuse"
    if is_question(text):
        return "answer" if matching_claim_count > 0 else "refuse"
    t = (text or "").strip()
    if len(t) >= 160 or sentence_count(t) >= 2:
        return "file"
    return "answer" if matching_claim_count > 0 else "refuse"
