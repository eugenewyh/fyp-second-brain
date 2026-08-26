"""Retrieval scope: where agents may search for a given run."""

from __future__ import annotations

from typing import Literal

RetrievalScope = Literal["local", "hybrid", "web"]

SCOPE_VALUES: tuple[str, ...] = ("local", "hybrid", "web")

SCOPE_LABELS: dict[str, str] = {
    "local": "Library",
    "hybrid": "Library + Web",
    "web": "Web",
}

# Which backend tags are allowed for each scope
SCOPE_ALLOWED_SOURCES: dict[str, frozenset[str]] = {
    "local": frozenset({"personal"}),
    "hybrid": frozenset({"personal", "web", "arxiv"}),
    "web": frozenset({"web", "arxiv"}),
}


def normalize_scope(value: str | None) -> RetrievalScope:
    if not value:
        return "hybrid"
    v = value.strip().lower()
    if v in ("library", "personal", "vault"):
        return "local"
    if v in ("library+web", "both", "all"):
        return "hybrid"
    if v in ("external",):
        return "web"
    if v in SCOPE_VALUES:
        return v  # type: ignore[return-value]
    return "hybrid"


def allowed_sources(scope: str | None) -> frozenset[str]:
    return SCOPE_ALLOWED_SOURCES[normalize_scope(scope)]


def planner_scope_instructions(scope: str | None) -> str:
    s = normalize_scope(scope)
    if s == "local":
        return (
            "RETRIEVAL SCOPE for this run: LOCAL LIBRARY ONLY.\n"
            "- Emit search queries tagged ONLY with [personal].\n"
            "- Do NOT use [web] or [arxiv] tags.\n"
            "- All investigation must use the user's own documents."
        )
    if s == "web":
        return (
            "RETRIEVAL SCOPE for this run: WEB / ACADEMIC ONLY (no personal vault).\n"
            "- Emit search queries tagged ONLY with [web] and/or [arxiv].\n"
            "- Do NOT use [personal] tags.\n"
            "- Prefer [web] for current info and [arxiv] for formal research."
        )
    return (
        "RETRIEVAL SCOPE for this run: HYBRID (personal library + web + arXiv).\n"
        "- Use [personal], [web], and [arxiv] tags as appropriate.\n"
        "- Include at least one [personal] query when the user may have local notes."
    )


def filter_queries_for_scope(query_lines: list[str], scope: str | None) -> list[str]:
    """Drop planner lines whose source tag is not allowed (defense in depth)."""
    from second_brain.agents.utils import parse_retrieval_query

    allowed = allowed_sources(scope)
    kept: list[str] = []
    for line in query_lines:
        parsed = parse_retrieval_query(line)
        if parsed.source in allowed:
            kept.append(line)
    return kept
