"""Retrieval scope: local / hybrid / web."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from langchain_core.documents import Document

from second_brain.agents.hybrid_retriever import hybrid_retrieve
from second_brain.scope import (
    filter_queries_for_scope,
    normalize_scope,
    planner_scope_instructions,
)


def test_normalize_scope():
    assert normalize_scope("local") == "local"
    assert normalize_scope("LIBRARY") == "local"
    assert normalize_scope(None) == "hybrid"
    assert normalize_scope("web") == "web"


def test_filter_queries_local():
    lines = [
        "[personal] multi-agent",
        "[web] latest RAG",
        "[arxiv] retrieval",
    ]
    kept = filter_queries_for_scope(lines, "local")
    assert all("personal" in q for q in kept)
    assert len(kept) == 1


def test_filter_queries_web():
    lines = [
        "[personal] vault",
        "[web] news",
        "[arxiv] paper",
    ]
    kept = filter_queries_for_scope(lines, "web")
    assert not any("personal" in q for q in kept)
    assert len(kept) == 2


def test_planner_instructions_local():
    text = planner_scope_instructions("local")
    assert "ONLY with [personal]" in text or "LOCAL" in text


def test_hybrid_retrieve_local_skips_web():
    personal = Document(
        page_content="five agents",
        metadata={"source": "pipeline.md", "source_type": "personal", "chunk_index": 0},
    )
    with (
        patch(
            "second_brain.agents.hybrid_retriever.retrieve",
            return_value=[personal],
        ) as ret,
        patch("second_brain.agents.hybrid_retriever.search_web") as web,
        patch("second_brain.agents.hybrid_retriever.search_arxiv") as arx,
    ):
        docs, stats, log = hybrid_retrieve(
            ["[personal] agents", "[web] agents"],
            main_query="agents",
            retrieval_scope="local",
        )
    assert stats.get("personal", 0) >= 1
    assert stats.get("web", 0) == 0
    assert any("scope disallows" in e or "scope" in e for e in log)
    web.assert_not_called()
    # arxiv not called for web tag under local
    assert ret.called


def test_hybrid_retrieve_web_skips_personal():
    web_doc = Document(
        page_content="from the web",
        metadata={"source": "https://example.com", "source_type": "web", "source_path": "https://example.com"},
    )
    with (
        patch("second_brain.agents.hybrid_retriever.retrieve") as ret,
        patch(
            "second_brain.agents.hybrid_retriever.search_web",
            return_value=[web_doc],
        ),
        patch("second_brain.agents.hybrid_retriever.ENABLE_WEB_SEARCH", True),
        patch(
            "second_brain.agents.hybrid_retriever.is_web_search_available",
            return_value=True,
        ),
        patch("second_brain.agents.hybrid_retriever.search_arxiv", return_value=[]),
    ):
        docs, stats, log = hybrid_retrieve(
            ["[personal] vault", "[web] news"],
            main_query="news",
            retrieval_scope="web",
        )
    assert stats.get("personal", 0) == 0
    assert stats.get("web", 0) == 1
    ret.assert_not_called()
