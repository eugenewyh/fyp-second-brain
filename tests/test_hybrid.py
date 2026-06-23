import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from langchain_core.documents import Document

from second_brain.agents.hybrid_retriever import hybrid_retrieve
from second_brain.agents.utils import parse_retrieval_query
from second_brain.memory.chroma_store import collection_count


def test_parse_retrieval_query_bracket():
    rq = parse_retrieval_query("[web] servlet security best practices")
    assert rq.source == "web"
    assert "servlet" in rq.query


def test_parse_retrieval_query_colon():
    rq = parse_retrieval_query("arxiv: java servlet performance")
    assert rq.source == "arxiv"
    assert "servlet" in rq.query


def test_parse_retrieval_query_default_personal():
    rq = parse_retrieval_query("Java inheritance")
    assert rq.source == "personal"
    assert rq.query == "Java inheritance"


def test_parse_retrieval_query_extracts_quoted_text():
    rq = parse_retrieval_query('[arxiv] query for research: "web framework patterns"')
    assert rq.source == "arxiv"
    assert rq.query == "web framework patterns"


def test_hybrid_retrieve_personal_only():
    if collection_count() == 0:
        pytest.skip("No documents indexed")

    docs, stats = hybrid_retrieve(["[personal] Java servlet"], main_query="Java servlet")
    assert stats.get("personal", 0) > 0
    assert all(d.metadata.get("source_type") == "personal" for d in docs)


@patch("second_brain.agents.hybrid_retriever.search_web")
@patch("second_brain.agents.hybrid_retriever.is_web_search_available", return_value=True)
def test_hybrid_retrieve_web_tag(mock_available, mock_web):
    mock_web.return_value = [
        Document(
            page_content="Web content about servlets",
            metadata={"source": "Example", "source_path": "https://example.com", "source_type": "web"},
        ),
    ]
    docs, stats = hybrid_retrieve(["[web] servlet tutorial"], main_query="servlets")
    assert stats.get("web", 0) == 1
    assert docs[0].metadata["source_type"] == "web"


@pytest.mark.network
def test_arxiv_search_live():
    from second_brain.tools.arxiv_search import search_arxiv

    docs = search_arxiv("machine learning", max_results=1)
    assert len(docs) == 1
    assert docs[0].metadata["source_type"] == "arxiv"
    assert "Abstract" in docs[0].page_content