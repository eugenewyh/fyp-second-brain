from pathlib import Path

from langchain_core.documents import Document

from second_brain.config import (
    DEEP_ASK_RERANK,
    HYBRID_RRF_K,
    RETRIEVAL_HYBRID,
    RETRIEVAL_TOP_K,
)
from second_brain.memory.bm25_index import documents_for_ids, search_bm25
from second_brain.memory.chroma_store import get_collection
from second_brain.memory.embeddings import get_embeddings
from second_brain.memory.rerank import rerank_documents


def _normalize_path_prefix(project_path: str | None) -> str | None:
    if not project_path or not str(project_path).strip():
        return None
    try:
        return str(Path(project_path).expanduser().resolve())
    except Exception:
        return str(project_path).strip().rstrip("/")


def _doc_in_project(doc: Document, project_prefix: str) -> bool:
    meta = doc.metadata or {}
    prefix = str(Path(project_prefix)).rstrip("/\\")
    for key in ("source_path", "source"):
        raw = meta.get(key)
        if not raw:
            continue
        try:
            path = str(Path(str(raw)).expanduser().resolve())
        except Exception:
            path = str(raw)
        path = path.rstrip("/\\")
        if path == prefix:
            return True
        if path.startswith(prefix + "/") or path.startswith(prefix + "\\"):
            return True
    return False


def _prefix_list(
    project_path: str | None,
    also_project_paths: list[str] | None = None,
) -> list[str]:
    out: list[str] = []
    for raw in [project_path, *(also_project_paths or [])]:
        prefix = _normalize_path_prefix(raw)
        if prefix and prefix not in out:
            out.append(prefix)
    return out


def _doc_in_any_project(doc: Document, prefixes: list[str]) -> bool:
    return any(_doc_in_project(doc, p) for p in prefixes)


def _doc_id_from_metadata(metadata: dict) -> str:
    source_hash = metadata.get("source_hash", "")
    chunk_index = metadata.get("chunk_index", 0)
    source = metadata.get("source", "unknown")
    if source_hash:
        return f"{source_hash}_{chunk_index}"
    return f"{source}_{chunk_index}"


def _rrf_merge(rank_lists: list[list[str]], *, k: int) -> list[str]:
    scores: dict[str, float] = {}
    for ranked in rank_lists:
        for rank, doc_id in enumerate(ranked):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.keys(), key=lambda d: scores[d], reverse=True)


def _vector_candidates(
    query: str,
    fetch_k: int,
) -> tuple[list[str], dict[str, Document]]:
    collection = get_collection()
    embeddings_model = get_embeddings()
    query_embedding = embeddings_model.embed_query(query)

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=fetch_k,
            include=["documents", "metadatas", "distances", "ids"],
        )
    except Exception as e:
        from second_brain.memory.chroma_store import is_hnsw_corruption_error

        if is_hnsw_corruption_error(e):
            raise RuntimeError(
                "Knowledge index is corrupted (Chroma HNSW). "
                "Reset and re-ingest: Ingest panel → Reset index, or "
                "POST /api/ingest with reset=true, or "
                "python scripts/ingest.py --input data/documents --reset"
            ) from e
        raise

    ranked_ids: list[str] = []
    by_id: dict[str, Document] = {}
    for doc_id, text, metadata, distance in zip(
        results["ids"][0],
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        doc_metadata = dict(metadata)
        doc_metadata["distance"] = distance
        doc_metadata.setdefault("source_type", "personal")
        doc = Document(page_content=text, metadata=doc_metadata)
        canonical_id = doc_id or _doc_id_from_metadata(doc_metadata)
        ranked_ids.append(canonical_id)
        by_id[canonical_id] = doc
    return ranked_ids, by_id


def _filter_documents(
    doc_ids: list[str],
    by_id: dict[str, Document],
    *,
    prefixes: list[str],
    source_path_filter: str | None,
    limit: int,
) -> list[Document]:
    if source_path_filter:
        from second_brain.rag.ask_depth import source_path_matches

    documents: list[Document] = []
    for doc_id in doc_ids:
        doc = by_id.get(doc_id)
        if doc is None:
            continue
        if prefixes and not _doc_in_any_project(doc, prefixes):
            continue
        if source_path_filter:
            meta = doc.metadata or {}
            sp = meta.get("source_path") or meta.get("source") or ""
            if not source_path_matches(str(sp), source_path_filter):
                continue
        documents.append(doc)
        if len(documents) >= limit:
            break
    return documents


def retrieve(
    query: str,
    top_k: int = RETRIEVAL_TOP_K,
    project_path: str | None = None,
    also_project_paths: list[str] | None = None,
    source_path_filter: str | None = None,
) -> list[Document]:
    collection = get_collection()
    if collection.count() == 0:
        return []

    prefixes = _prefix_list(project_path, also_project_paths)
    scope_multiplier = max(1, len(prefixes))
    if source_path_filter:
        scope_multiplier *= 4
    base_fetch = top_k * 4 if RETRIEVAL_HYBRID else top_k
    if prefixes or source_path_filter:
        fetch_k = min(collection.count(), base_fetch * scope_multiplier)
    else:
        fetch_k = min(collection.count(), base_fetch)

    vector_ids, vector_by_id = _vector_candidates(query, fetch_k)

    if RETRIEVAL_HYBRID:
        bm25_hits = search_bm25(query, fetch_k)
        bm25_ids = [doc_id for doc_id, _ in bm25_hits]
        bm25_by_id = documents_for_ids(bm25_ids)
        for doc_id, doc in bm25_by_id.items():
            vector_by_id.setdefault(doc_id, doc)
        merged_ids = _rrf_merge([vector_ids, bm25_ids], k=HYBRID_RRF_K)
    else:
        merged_ids = vector_ids

    documents = _filter_documents(
        merged_ids,
        vector_by_id,
        prefixes=prefixes,
        source_path_filter=source_path_filter,
        limit=top_k * 4,
    )

    if DEEP_ASK_RERANK and len(documents) > top_k:
        documents = rerank_documents(query, documents, top_k=top_k)
    elif len(documents) > top_k:
        documents = documents[:top_k]

    return documents


def retrieve_multi(
    queries: list[str],
    top_k_per_query: int = 3,
    project_path: str | None = None,
    also_project_paths: list[str] | None = None,
) -> list[Document]:
    seen: set[str] = set()
    results: list[Document] = []

    for query in queries:
        for doc in retrieve(
            query,
            top_k=top_k_per_query,
            project_path=project_path,
            also_project_paths=also_project_paths,
        ):
            doc_id = f"{doc.metadata.get('source', '')}_{doc.metadata.get('chunk_index', '')}"
            if doc_id in seen:
                continue
            seen.add(doc_id)
            results.append(doc)

    return results
