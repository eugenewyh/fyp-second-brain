"""Persisted BM25 index aligned with Chroma doc IDs."""

from __future__ import annotations

import logging
import pickle
import re
from dataclasses import dataclass, field
from pathlib import Path

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from second_brain.config import CHROMA_PATH
from second_brain.memory.locks import chroma_write_lock

logger = logging.getLogger(__name__)

BM25_PATH = CHROMA_PATH / "bm25_corpus.pkl"
_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass
class _Bm25Entry:
    doc_id: str
    text: str
    metadata: dict[str, str | int | float] = field(default_factory=dict)


@dataclass
class _Bm25State:
    entries: list[_Bm25Entry] = field(default_factory=list)
    tokenized: list[list[str]] = field(default_factory=list)
    index: BM25Okapi | None = None

    def rebuild_index(self) -> None:
        self.tokenized = [_tokenize(e.text) for e in self.entries]
        self.index = BM25Okapi(self.tokenized) if self.tokenized else None


_state: _Bm25State | None = None


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or "").lower())


def _doc_id_for_chunk(doc: Document) -> str:
    meta = doc.metadata or {}
    source_hash = meta.get("source_hash", "")
    chunk_index = meta.get("chunk_index", 0)
    source = meta.get("source", "unknown")
    if source_hash:
        return f"{source_hash}_{chunk_index}"
    return f"{source}_{chunk_index}"


def _load_state() -> _Bm25State:
    global _state
    if _state is not None:
        return _state

    if BM25_PATH.is_file():
        try:
            raw = pickle.loads(BM25_PATH.read_bytes())
            if isinstance(raw, _Bm25State):
                _state = raw
                if _state.index is None and _state.entries:
                    _state.rebuild_index()
                return _state
        except Exception:
            logger.warning("Failed to load BM25 index from %s", BM25_PATH, exc_info=True)

    _state = _Bm25State()
    return _state


def _save_state(state: _Bm25State) -> None:
    global _state
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    BM25_PATH.write_bytes(pickle.dumps(state))
    _state = state


def reset_bm25_index() -> None:
    """Delete persisted BM25 corpus (call on vector store reset)."""
    global _state
    _state = _Bm25State()
    if BM25_PATH.exists():
        try:
            BM25_PATH.unlink()
        except OSError:
            logger.warning("Could not remove BM25 index at %s", BM25_PATH, exc_info=True)


def update_bm25_index(documents: list[Document]) -> None:
    """Upsert chunk documents into the BM25 corpus."""
    if not documents:
        return

    with chroma_write_lock:
        state = _load_state()
        by_id = {e.doc_id: e for e in state.entries}

        for doc in documents:
            doc_id = _doc_id_for_chunk(doc)
            meta = {
                k: v
                for k, v in (doc.metadata or {}).items()
                if isinstance(v, (str, int, float))
            }
            by_id[doc_id] = _Bm25Entry(
                doc_id=doc_id,
                text=doc.page_content or "",
                metadata=meta,
            )

        state.entries = list(by_id.values())
        state.rebuild_index()
        _save_state(state)


def rebuild_bm25_from_collection() -> None:
    """Rebuild BM25 corpus from all documents in Chroma."""
    from second_brain.memory.chroma_store import get_collection

    collection = get_collection()
    count = collection.count()
    if count == 0:
        reset_bm25_index()
        return

    result = collection.get(include=["documents", "metadatas"])
    entries: list[_Bm25Entry] = []
    for doc_id, text, meta in zip(
        result["ids"],
        result["documents"],
        result["metadatas"],
    ):
        entries.append(
            _Bm25Entry(
                doc_id=doc_id,
                text=text or "",
                metadata={
                    k: v
                    for k, v in (meta or {}).items()
                    if isinstance(v, (str, int, float))
                },
            )
        )

    with chroma_write_lock:
        state = _Bm25State(entries=entries)
        state.rebuild_index()
        _save_state(state)
    logger.info("Rebuilt BM25 index with %d chunk(s)", len(entries))


def search_bm25(query: str, top_k: int) -> list[tuple[str, float]]:
    """Return (doc_id, bm25_score) pairs ranked best-first."""
    state = _load_state()
    if not state.index or not state.entries or top_k <= 0:
        return []

    tokens = _tokenize(query)
    if not tokens:
        return []

    scores = state.index.get_scores(tokens)
    ranked = [
        (state.entries[i].doc_id, float(scores[i]))
        for i in range(len(state.entries))
    ]
    if not any(score > 0 for _, score in ranked):
        # BM25 IDF collapses on very small corpora; use token overlap instead.
        ranked = []
        for i, entry in enumerate(state.entries):
            doc_tokens = set(state.tokenized[i])
            overlap = sum(1 for token in tokens if token in doc_tokens)
            ranked.append((entry.doc_id, float(overlap)))

    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked[:top_k]


def documents_for_ids(doc_ids: list[str]) -> dict[str, Document]:
    """Map doc IDs to LangChain documents from the BM25 corpus."""
    state = _load_state()
    by_id = {e.doc_id: e for e in state.entries}
    out: dict[str, Document] = {}
    for doc_id in doc_ids:
        entry = by_id.get(doc_id)
        if not entry:
            continue
        meta = dict(entry.metadata)
        meta.setdefault("source_type", "personal")
        out[doc_id] = Document(page_content=entry.text, metadata=meta)
    return out
