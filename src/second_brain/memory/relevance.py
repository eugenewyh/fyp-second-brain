"""Whether a research query belongs in this topic's durable memory."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

SKIP_FILE_DETAIL = "Answered in chat — not filed into this topic"

_GENERIC_README = re.compile(
    r"^#\s+\S+\s*\n+Project notes and sources\.?\s*$",
    re.I | re.S,
)
_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "of",
    "to",
    "in",
    "on",
    "for",
    "is",
    "are",
    "was",
    "were",
    "be",
    "with",
    "that",
    "this",
    "as",
    "by",
    "from",
    "it",
    "its",
    "what",
    "which",
    "who",
    "how",
    "why",
    "when",
    "where",
    "best",
    "small",
    "look",
    "lookup",
    "looking",
    "find",
    "paper",
    "papers",
    "arxiv",
    "search",
    "web",
    "latest",
    "news",
    "new",
    "use",
    "want",
    "collect",
    "notes",
    "topic",
    "project",
    "focus",
    "pass",
    "remaining",
    "gaps",
    "prior",
    "findings",
    "deepen",
    "coverage",
    "sources",
    "library",
}

# Watch/Teach already scoped the job to this topic.
_ALWAYS_FILE = {"watch", "dump"}


def _tokens(text: str) -> set[str]:
    words = _TOKEN.findall((text or "").lower())
    return {w for w in words if len(w) > 2 and w not in _STOP}


def _read_text(path: Path, limit: int = 4000) -> str:
    try:
        return path.read_text(encoding="utf-8")[:limit]
    except OSError:
        return ""


def _strip_frontmatter(text: str) -> str:
    if not (text or "").startswith("---"):
        return text
    parts = text.split("---", 2)
    return parts[2] if len(parts) >= 3 else text


def topic_scope_text(project_path: str | None) -> str:
    """IDEA.md + non-stub README + project.md + claim sentences."""
    if not project_path:
        return ""
    root = Path(project_path)
    if not root.is_dir():
        return ""
    chunks: list[str] = []
    idea = _read_text(root / "IDEA.md")
    if idea.strip():
        chunks.append(idea)
    readme = _read_text(root / "README.md", limit=1500)
    if readme.strip() and not _GENERIC_README.match(readme.strip()):
        chunks.append(readme)
    project_md = _strip_frontmatter(_read_text(root / "memory" / "project.md"))
    if project_md.strip():
        chunks.append(project_md)
    try:
        from second_brain.memory.claims import list_claims

        for card in list_claims(project_path, status="active")[:30]:
            if (card.claim or "").strip():
                chunks.append(card.claim.strip())
    except Exception:
        logger.debug("Claim scope skipped", exc_info=True)
    return "\n".join(chunks).strip()


def _llm_on_topic(query: str, scope: str) -> bool | None:
    """True/False when the fast model answers; None if unavailable."""
    user = (
        f"Topic notes:\n{scope[:2200]}\n\n"
        f"User query:\n{query[:800]}\n\n"
        'Return JSON: {"on_topic": true|false, "reason": "short"}\n'
        "on_topic is true only if the query is about the same research subject as the topic notes."
    )
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from second_brain.memory.llm import invoke_llm

        resp = invoke_llm(
            [
                SystemMessage(
                    content="You decide if a question belongs in a personal research topic. JSON only."
                ),
                HumanMessage(content=user),
            ],
            role="fast",
        )
        raw = resp.content if isinstance(resp.content, str) else str(resp.content)
        text = (raw or "").strip()
        obj = json.loads(text) if text.startswith("{") else None
        if obj is None:
            m = re.search(r"\{.*\}", text, re.S)
            obj = json.loads(m.group(0)) if m else None
        if isinstance(obj, dict) and "on_topic" in obj:
            return bool(obj["on_topic"])
    except Exception:
        logger.debug("Topic relevance LLM skipped", exc_info=True)
    return None


def should_file_research(
    query: str,
    project_path: str | None,
    *,
    origin: str = "research",
    llm_fn=None,
) -> tuple[bool, str]:
    """Whether findings should be written into this topic's memory.

    Watch/dump always file. Empty topics file (research can define them).
    Otherwise require overlap with IDEA/claims, or an LLM yes. No overlap and
    no LLM yes → skip, so espresso lookups do not pollute a DLM topic.
    """
    if (origin or "").strip().lower() in _ALWAYS_FILE:
        return True, "scoped job"
    q = (query or "").strip()
    if not q:
        return True, "empty query"
    scope = topic_scope_text(project_path)
    if len(_tokens(scope)) < 4:
        return True, "no topic identity yet"
    try:
        from second_brain.memory.claims import claims_matching_query

        if claims_matching_query(q, project_path, limit=3):
            return True, "matching claims"
    except Exception:
        logger.debug("Claim overlap skipped", exc_info=True)
    overlap = _tokens(q) & _tokens(scope)
    if overlap:
        return True, "overlaps topic notes"
    decide = llm_fn if llm_fn is not None else _llm_on_topic
    verdict = decide(q, scope)
    if verdict is True:
        return True, "on-topic"
    return False, "off-topic for this project"
