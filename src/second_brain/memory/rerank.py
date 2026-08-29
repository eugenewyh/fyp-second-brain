"""Lightweight rerank: token overlap blended with embedding distance."""

from __future__ import annotations

import re

from langchain_core.documents import Document

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
    "how",
    "why",
    "when",
    "where",
    "who",
    "does",
    "do",
    "about",
    "me",
    "my",
}


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w for w in words if len(w) > 2 and w not in _STOP}


def _overlap_score(query: str, doc: Document) -> float:
    qt = _tokens(query)
    if not qt:
        return 0.0
    meta = doc.metadata or {}
    blob = " ".join(
        [
            doc.page_content or "",
            str(meta.get("source") or ""),
            str(meta.get("source_path") or ""),
        ]
    )
    dt = _tokens(blob)
    if not dt:
        return 0.0
    return len(qt & dt) / len(qt)


def _distance_score(doc: Document) -> float:
    raw = (doc.metadata or {}).get("distance")
    try:
        dist = float(raw)
    except (TypeError, ValueError):
        return 0.5
    # Chroma cosine distance: lower is better; map to 0..1 relevance
    return max(0.0, min(1.0, 1.0 - dist))


def rerank_documents(query: str, documents: list[Document], *, top_k: int) -> list[Document]:
    """Re-score candidates: 60% token overlap + 40% embedding proximity."""
    if not documents or top_k <= 0:
        return []
    if len(documents) <= top_k:
        return documents

    scored: list[tuple[float, Document]] = []
    for doc in documents:
        score = 0.6 * _overlap_score(query, doc) + 0.4 * _distance_score(doc)
        scored.append((score, doc))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [doc for _, doc in scored[:top_k]]
