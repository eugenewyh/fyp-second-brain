"""Hidden product LLM: Gemini Flash-Lite for titles + Auto routing.

Uses GEMINI_API_KEY from .env (not exposed in Settings). Independent of the
user-visible research provider (OpenRouter / Groq / …).
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_GEMINI_LITE_MODEL = "gemini-3.5-flash-lite"
GEMINI_OPENAI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"


def gemini_api_key() -> str:
    return (
        os.getenv("GEMINI_API_KEY", "").strip()
        or os.getenv("GOOGLE_API_KEY", "").strip()
    )


def gemini_lite_configured() -> bool:
    return bool(gemini_api_key())


def gemini_lite_model() -> str:
    """Model for product helpers (Auto route + chat rename)."""
    return (
        os.getenv("GEMINI_LITE_MODEL", "").strip()
        or os.getenv("SESSION_TITLE_MODEL", "").strip()
        or DEFAULT_GEMINI_LITE_MODEL
    )


def _content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("text"):
                parts.append(str(block["text"]))
            else:
                text = getattr(block, "text", None)
                if text:
                    parts.append(str(text))
        return "".join(parts)
    return str(content)


def invoke_gemini_lite(
    messages: list[Any],
    *,
    max_tokens: int = 64,
    temperature: float = 0.2,
) -> str | None:
    """Invoke Gemini Flash-Lite. Returns text or None if unconfigured / failed."""
    key = gemini_api_key()
    if not key:
        logger.debug("Gemini lite skipped: GEMINI_API_KEY not set")
        return None

    model = gemini_lite_model()
    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=key,
            base_url=GEMINI_OPENAI_BASE,
        )
        resp = llm.invoke(messages)
        text = _content_to_text(getattr(resp, "content", None)).strip()
        return text or None
    except Exception:
        logger.warning("Gemini lite invoke failed (model=%s)", model, exc_info=True)
        return None
