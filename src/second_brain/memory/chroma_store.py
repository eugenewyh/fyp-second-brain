from __future__ import annotations

from datetime import datetime, timezone

import chromadb
from langchain_core.documents import Document

from second_brain.config import CHROMA_PATH, COLLECTION_NAME
from second_brain.memory.embeddings import get_embeddings

_client: chromadb.PersistentClient | None = None


def get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return _client


def get_collection():
    client = get_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def collection_count() -> int:
    return get_collection().count()


def upsert_documents(documents: list[Document]) -> int:
    if not documents:
        return 0

    collection = get_collection()
    embeddings_model = get_embeddings()

    texts = [doc.page_content for doc in documents]
    embeddings = embeddings_model.embed_documents(texts)

    ids = []
    metadatas = []
    for doc in documents:
        source = doc.metadata.get("source", "unknown")
        chunk_index = doc.metadata.get("chunk_index", 0)
        doc_id = f"{source}_{chunk_index}"
        ids.append(doc_id)

        metadata = {
            "source": source,
            "source_path": doc.metadata.get("source_path", ""),
            "page": doc.metadata.get("page", -1),
            "chunk_index": chunk_index,
            "ingested_at": doc.metadata.get(
                "ingested_at",
                datetime.now(timezone.utc).isoformat(),
            ),
        }
        metadatas.append(metadata)

    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    return len(documents)