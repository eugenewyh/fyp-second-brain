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
from second_brain.scope import allowed_sources, normalize_scope
from second_brain.tools.arxiv_search import search_arxiv
from second_brain.tools.mcp_client import is_mcp_available, search_mcp
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


def _reformulate_arxiv_query(query: str) -> str:
    return f'all:"{query}" OR multi-agent systems OR retrieval augmented generation'


def _fetch_arxiv(parsed: RetrievalQuery, retrieval_log: list[str]) -> list[Document]:
    docs = search_arxiv(parsed.query)
    log_entry = f"[arxiv] {parsed.query} → {len(docs)} result(s)"

    if not docs:
        reformulated = _reformulate_arxiv_query(parsed.query)
        docs = search_arxiv(reformulated)
        log_entry += f"; retry '{reformulated}' → {len(docs)} result(s)"

    retrieval_log.append(log_entry)
    return docs


def _fetch_for_source(
    parsed: RetrievalQuery,
    retrieval_log: list[str],
    allowed: frozenset[str],
    project_path: str | None = None,
    also_project_paths: list[str] | None = None,
) -> list[Document]:
    if parsed.source not in allowed:
        retrieval_log.append(
            f"[{parsed.source}] {parsed.query} → skipped (scope disallows {parsed.source})"
        )
        return []

    if parsed.source == "web":
        if not ENABLE_WEB_SEARCH:
            retrieval_log.append(f"[web] {parsed.query} → skipped (disabled)")
            return []
        docs = search_web(parsed.query)
        retrieval_log.append(f"[web] {parsed.query} → {len(docs)} result(s)")
        return docs

    if parsed.source == "arxiv":
        if not ENABLE_ARXIV:
            retrieval_log.append(f"[arxiv] {parsed.query} → skipped (disabled)")
            return []
        return _fetch_arxiv(parsed, retrieval_log)

    # personal (optionally scoped to project folder)
    docs = retrieve(
        parsed.query,
        top_k=RETRIEVAL_TOP_K_PER_QUERY,
        project_path=project_path,
        also_project_paths=also_project_paths,
    )
    extra = f"+{len(also_project_paths)} extra" if also_project_paths else ""
    scope_note = f" project={project_path}{extra}" if project_path else extra
    retrieval_log.append(
        f"[personal] {parsed.query} → {len(docs)} result(s){scope_note}"
    )
    return docs


def hybrid_retrieve(
    query_lines: list[str],
    main_query: str,
    retrieval_scope: str | None = "hybrid",
    project_path: str | None = None,
    also_project_paths: list[str] | None = None,
) -> tuple[list[Document], dict[str, int], list[str]]:
    scope = normalize_scope(retrieval_scope)
    allowed = allowed_sources(scope)
    parsed_queries = [parse_retrieval_query(line) for line in query_lines]
    seen: set[str] = set()
    documents: list[Document] = []
    stats = {"personal": 0, "web": 0, "arxiv": 0, "mcp": 0}
    retrieval_log: list[str] = [f"[scope] {scope} (allowed: {', '.join(sorted(allowed))})"]
    if project_path:
        retrieval_log.append(f"[project] personal retrieval limited to {project_path}")
    if also_project_paths:
        retrieval_log.append(
            f"[project] also retrieving from {', '.join(also_project_paths)}"
        )

    for parsed in parsed_queries:
        for doc in _fetch_for_source(
            parsed, retrieval_log, allowed, project_path, also_project_paths
        ):
            key = _doc_key(doc)
            if key in seen:
                continue
            seen.add(key)
            documents.append(doc)
            source_type = doc.metadata.get("source_type", "personal")
            stats[source_type] = stats.get(source_type, 0) + 1

    if scope == "hybrid" and is_mcp_available():
        mcp_docs = search_mcp(main_query)
        retrieval_log.append(f"[mcp:notion] '{main_query}' → {len(mcp_docs)} result(s)")
        for doc in mcp_docs:
            key = _doc_key(doc)
            if key in seen:
                continue
            seen.add(key)
            documents.append(doc)
            stats["mcp"] = stats.get("mcp", 0) + 1

    personal_count = stats.get("personal", 0)
    has_web_query = any(q.source == "web" for q in parsed_queries)
    has_arxiv_query = any(q.source == "arxiv" for q in parsed_queries)

    # Fallbacks only when hybrid (or when web-only and we need external coverage)
    if scope == "hybrid":
        if personal_count < HYBRID_FALLBACK_THRESHOLD and not has_web_query:
            if ENABLE_WEB_SEARCH and is_web_search_available() and "web" in allowed:
                logger.info("Fallback: personal results thin (%d) — trying web", personal_count)
                fallback_docs = search_web(main_query)
                retrieval_log.append(
                    f"[web] fallback '{main_query}' → {len(fallback_docs)} result(s)"
                )
                for doc in fallback_docs:
                    key = _doc_key(doc)
                    if key not in seen:
                        seen.add(key)
                        documents.append(doc)
                        stats["web"] = stats.get("web", 0) + 1

        if personal_count < HYBRID_FALLBACK_THRESHOLD and not has_arxiv_query:
            if ENABLE_ARXIV and "arxiv" in allowed:
                logger.info("Fallback: personal results thin (%d) — trying arXiv", personal_count)
                fallback = RetrievalQuery(source="arxiv", query=main_query)
                for doc in _fetch_arxiv(fallback, retrieval_log):
                    key = _doc_key(doc)
                    if key not in seen:
                        seen.add(key)
                        documents.append(doc)
                        stats["arxiv"] = stats.get("arxiv", 0) + 1

    return documents, stats, retrieval_log
