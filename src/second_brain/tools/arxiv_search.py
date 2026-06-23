import logging

from langchain_core.documents import Document

from second_brain.config import ARXIV_MAX_RESULTS

logger = logging.getLogger(__name__)


def search_arxiv(query: str, max_results: int = ARXIV_MAX_RESULTS) -> list[Document]:
    try:
        import arxiv
    except ImportError:
        logger.error("arxiv package not installed — skipping arXiv search")
        return []

    documents: list[Document] = []
    try:
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )
        for paper in client.results(search):
            authors = ", ".join(author.name for author in paper.authors)
            content = (
                f"Title: {paper.title}\n"
                f"Authors: {authors}\n"
                f"Published: {paper.published.strftime('%Y-%m-%d')}\n"
                f"Abstract: {paper.summary}"
            )
            documents.append(Document(
                page_content=content,
                metadata={
                    "source": paper.title,
                    "source_path": paper.entry_id,
                    "source_type": "arxiv",
                    "page": -1,
                    "chunk_index": 0,
                    "published": paper.published.isoformat(),
                },
            ))
    except Exception as e:
        logger.error("arXiv search failed for '%s': %s", query, e)
        return []

    logger.info("arXiv search: %d result(s) for '%s'", len(documents), query)
    return documents