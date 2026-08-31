from __future__ import annotations

import logging
import shutil
from datetime import datetime, timezone

import chromadb
from langchain_core.documents import Document

from second_brain.config import CHROMA_PATH, COLLECTION_NAME
from second_brain.memory.bm25_index import reset_bm25_index, update_bm25_index
from second_brain.memory.embeddings import get_embeddings, write_fingerprint
from second_brain.memory.locks import chroma_write_lock

logger = logging.getLogger(__name__)

_client: chromadb.PersistentClient | None = None


def get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return _client


def reset_client() -> None:
    """Drop in-memory client so the next call re-opens from disk."""
    global _client
    _client = None


def get_collection():
    client = get_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def collection_count() -> int:
    return get_collection().count()


def is_hnsw_corruption_error(err: BaseException) -> bool:
    text = str(err).lower()
    return (
        "nothing found on disk" in text
        or "hnsw segment" in text
        or "error creating hnsw" in text
        or "segment reader" in text
    )


def reset_vector_store(*, wipe_files: bool = True) -> None:
    """Delete the Chroma collection / on-disk index (fixes corrupt HNSW).

    Call before a full re-ingest when query fails with
    "Nothing found on disk" or similar segment-reader errors.
    """
    global _client
    with chroma_write_lock:
        _reset_vector_store_unlocked(wipe_files=wipe_files)


def _reset_vector_store_unlocked(*, wipe_files: bool = True) -> None:
    global _client
    if wipe_files:
        # Wiping the directory makes delete_collection unnecessary; calling it first
        # leaves Chroma 1.x sqlite bindings read-only in-process until exit.
        _client = None
        if CHROMA_PATH.exists():
            try:
                shutil.rmtree(CHROMA_PATH)
            except OSError as e:
                logger.warning("Could not remove %s: %s", CHROMA_PATH, e)
    else:
        try:
            client = get_client()
            try:
                client.delete_collection(COLLECTION_NAME)
            except Exception as e:
                logger.warning("delete_collection failed: %s", e)
        finally:
            _client = None

    reset_bm25_index()

    reset_client()
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    get_collection()  # recreate empty collection
    logger.info("Vector store reset at %s", CHROMA_PATH)


def upsert_documents(documents: list[Document]) -> int:
    if not documents:
        return 0

    collection = get_collection()
    embeddings_model = get_embeddings()

    texts = [doc.page_content for doc in documents]
    logger.info("Embedding %d chunk(s)…", len(texts))
    embeddings = embeddings_model.embed_documents(texts)
    logger.info("Embedding complete — upserting to Chroma")
    if embeddings:
        write_fingerprint(dims=len(embeddings[0]))

    ids = []
    metadatas = []
    for doc in documents:
        source = doc.metadata.get("source", "unknown")
        chunk_index = doc.metadata.get("chunk_index", 0)
        source_hash = doc.metadata.get("source_hash", "")
        doc_id = f"{source_hash}_{chunk_index}" if source_hash else f"{source}_{chunk_index}"
        ids.append(doc_id)

        metadata = {
            "source": source,
            "source_path": doc.metadata.get("source_path", ""),
            "source_hash": source_hash,
            "page": doc.metadata.get("page", -1),
            "chunk_index": chunk_index,
            "ingested_at": doc.metadata.get(
                "ingested_at",
                datetime.now(timezone.utc).isoformat(),
            ),
        }
        # Optional type tags for agent memory recall boosting
        for key in ("doc_type", "type", "source_type"):
            val = doc.metadata.get(key)
            if val is not None and str(val).strip():
                metadata[key] = str(val)[:64]
        metadatas.append(metadata)

    with chroma_write_lock:
        collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        update_bm25_index(documents)
    return len(documents)
