"""LLM chat-title generation (Gemini Flash-Lite) with sanitization."""

from __future__ import annotations

import logging
import re

from second_brain.memory.gemini_lite import (
    gemini_api_key,
    gemini_lite_configured,
    gemini_lite_model,
    invoke_gemini_lite,
)

logger = logging.getLogger(__name__)

TITLE_MAX_CHARS = 36
TITLE_MAX_WORDS = 6

# Back-compat aliases for callers / tests
gemini_title_configured = gemini_lite_configured
session_title_model = gemini_lite_model

_TITLE_PROMPT = """Write a short chat sidebar title for the user message below.

Rules:
- 3 to 5 words, Title Case
- Topic only (what the chat is about)
- No quotes, no trailing punctuation, no emoji
- Max {max_chars} characters
- Reply with the title only

User message:
{message}
"""


def sanitize_session_title(raw: str | None) -> str | None:
    """Normalize model output into a safe sidebar title."""
    if not raw:
        return None
    text = str(raw).strip()
    if not text:
        return None

    # Keep first line only (models sometimes add explanations)
    text = text.splitlines()[0].strip()
    text = text.strip("\"'`“”‘’")
    text = re.sub(r"^[Tt]itle\s*:\s*", "", text).strip()
    lower_early = text.lower().strip(" .!?,;:-")
    if lower_early in {"new chat", "untitled", "title", "chat", "none", "n/a", "na"}:
        return None

    text = re.sub(r"[\\/:*?\"<>|]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" .!?,;:-")
    if not text or len(text) < 2:
        return None

    words = text.split()
    if len(words) > TITLE_MAX_WORDS:
        text = " ".join(words[:TITLE_MAX_WORDS])
    if len(text) > TITLE_MAX_CHARS:
        clipped = text[:TITLE_MAX_CHARS].rsplit(" ", 1)[0].strip()
        text = clipped or text[:TITLE_MAX_CHARS].strip()

    lower = text.lower()
    if lower in {"new chat", "untitled", "title", "chat", "none", "n/a", "na", "n a"}:
        return None
    return text


def generate_session_title(message: str) -> str | None:
    """Call Gemini Flash-Lite for a short title. Returns None on any failure."""
    text = (message or "").strip()
    if not text:
        return None
    if not gemini_api_key():
        logger.debug("Session title skipped: GEMINI_API_KEY not set")
        return None

    from langchain_core.messages import HumanMessage

    prompt = _TITLE_PROMPT.format(max_chars=TITLE_MAX_CHARS, message=text[:1500])
    raw = invoke_gemini_lite([HumanMessage(content=prompt)], max_tokens=24)
    return sanitize_session_title(raw)
