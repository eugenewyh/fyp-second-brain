import logging

from langchain_core.documents import Document

from second_brain.agents.utils import RetrievalQuery, parse_retrieval_query
from second_brain.config import (
    ENABLE_ARXIV,
    ENABLE_WEB_SEARCH,
    HYBRID_FALLBACK_THRESHOLD,
    RETRIEVAL_TOP_K_PER_QUERY,
)
from second_brain.memory.retriever import retrieve
from second_brain.tools.arxiv_search import search_arxiv
from second_brain.tools.web_search import is_web_search_available, search_web

logger = logging.getLogger(__name__)


def _doc_key(doc: Document) -> str:
    source_type = doc.metadata.get("source_type", "personal")
    if source_type == "personal":
        return (
            f"personal_{doc.metadata.get('source', '')}_"
            f"{doc.metadata.get('chunk_index', '')}"
        )
    return f"{source_type}_{doc.metadata.get('source_path', doc.metadata.get('source', ''))}"


def _fetch_for_source(parsed: RetrievalQuery) -> list[Document]:
    if parsed.source == "web":
        if not ENABLE_WEB_SEARCH:
            logger.info("Web search disabled — skipping: %s", parsed.query)
            return []
        return search_web(parsed.query)

    if parsed.source == "arxiv":
        if not ENABLE_ARXIV:
            logger.info("arXiv search disabled — skipping: %s", parsed.query)
            return []
        return search_arxiv(parsed.query)

    return retrieve(parsed.query, top_k=RETRIEVAL_TOP_K_PER_QUERY)


def hybrid_retrieve(
    query_lines: list[str],
    main_query: str,
) -> tuple[list[Document], dict[str, int]]:
    parsed_queries = [parse_retrieval_query(line) for line in query_lines]
    seen: set[str] = set()
    documents: list[Document] = []
    stats = {"personal": 0, "web": 0, "arxiv": 0}

    for parsed in parsed_queries:
        for doc in _fetch_for_source(parsed):
            key = _doc_key(doc)
            if key in seen:
                continue
            seen.add(key)
            documents.append(doc)
            source_type = doc.metadata.get("source_type", "personal")
            stats[source_type] = stats.get(source_type, 0) + 1

    personal_count = stats.get("personal", 0)
    has_web_query = any(q.source == "web" for q in parsed_queries)
    has_arxiv_query = any(q.source == "arxiv" for q in parsed_queries)

    if personal_count < HYBRID_FALLBACK_THRESHOLD and not has_web_query:
        if ENABLE_WEB_SEARCH and is_web_search_available():
            logger.info("Fallback: personal results thin (%d) — trying web", personal_count)
            for doc in search_web(main_query):
                key = _doc_key(doc)
                if key not in seen:
                    seen.add(key)
                    documents.append(doc)
                    stats["web"] = stats.get("web", 0) + 1

    if personal_count < HYBRID_FALLBACK_THRESHOLD and not has_arxiv_query:
        if ENABLE_ARXIV:
            logger.info("Fallback: personal results thin (%d) — trying arXiv", personal_count)
            for doc in search_arxiv(main_query):
                key = _doc_key(doc)
                if key not in seen:
                    seen.add(key)
                    documents.append(doc)
                    stats["arxiv"] = stats.get("arxiv", 0) + 1

    return documents, stats