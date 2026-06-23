import logging

from langchain_core.documents import Document

from second_brain.config import TAVILY_API_KEY, WEB_SEARCH_MAX_RESULTS

logger = logging.getLogger(__name__)


def is_web_search_available() -> bool:
    return bool(TAVILY_API_KEY)


def search_web(query: str, max_results: int = WEB_SEARCH_MAX_RESULTS) -> list[Document]:
    if not TAVILY_API_KEY:
        logger.warning("TAVILY_API_KEY not set — skipping web search for: %s", query)
        return []

    try:
        from tavily import TavilyClient
    except ImportError:
        logger.error("tavily-python not installed — skipping web search")
        return []

    client = TavilyClient(api_key=TAVILY_API_KEY)
    response = client.search(query=query, max_results=max_results)

    documents: list[Document] = []
    for result in response.get("results", []):
        title = result.get("title", "Web result")
        content = result.get("content", "")
        url = result.get("url", "")

        documents.append(Document(
            page_content=f"Title: {title}\nURL: {url}\n{content}",
            metadata={
                "source": title,
                "source_path": url,
                "source_type": "web",
                "page": -1,
                "chunk_index": 0,
            },
        ))

    logger.info("Web search: %d result(s) for '%s'", len(documents), query)
    return documents