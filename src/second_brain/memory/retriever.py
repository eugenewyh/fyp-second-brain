from pathlib import Path

from langchain_core.documents import Document

from second_brain.config import RETRIEVAL_TOP_K
from second_brain.memory.chroma_store import get_collection
from second_brain.memory.embeddings import get_embeddings


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


def retrieve(
    query: str,
    top_k: int = RETRIEVAL_TOP_K,
    project_path: str | None = None,
    also_project_paths: list[str] | None = None,
) -> list[Document]:
    collection = get_collection()
    if collection.count() == 0:
        return []

    embeddings_model = get_embeddings()
    query_embedding = embeddings_model.embed_query(query)

    prefixes = _prefix_list(project_path, also_project_paths)
    # Over-fetch when filtering by project so we still return ~top_k in-scope hits
    fetch_k = min(collection.count(), top_k * 4 * max(1, len(prefixes)) if prefixes else top_k)

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=fetch_k,
            include=["documents", "metadatas", "distances"],
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

    documents: list[Document] = []
    for text, metadata, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        doc_metadata = dict(metadata)
        doc_metadata["distance"] = distance
        doc_metadata.setdefault("source_type", "personal")
        doc = Document(page_content=text, metadata=doc_metadata)
        if prefixes and not _doc_in_any_project(doc, prefixes):
            continue
        documents.append(doc)
        if len(documents) >= top_k:
            break

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