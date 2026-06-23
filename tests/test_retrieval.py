import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from second_brain.memory.chroma_store import collection_count
from second_brain.memory.retriever import retrieve
from second_brain.rag.chain import ask
from second_brain.rag.prompts import format_context


@pytest.fixture
def requires_indexed_docs():
    if collection_count() == 0:
        pytest.skip("No documents indexed — run ingest first")


def test_format_context_empty():
    assert format_context([]) == "No relevant documents found."


def test_format_context_numbered(requires_indexed_docs):
    docs = retrieve("Java programming", top_k=2)
    context = format_context(docs)
    assert "[1]" in context
    assert "Source:" in context


def test_retrieve_returns_documents(requires_indexed_docs):
    docs = retrieve("object oriented programming", top_k=3)
    assert len(docs) > 0
    assert docs[0].page_content
    assert "source" in docs[0].metadata


def test_ask_returns_citations(requires_indexed_docs):
    response = ask("What is a class in Java?", top_k=3)
    assert response.question == "What is a class in Java?"
    assert response.answer
    assert len(response.sources) > 0
    assert response.sources[0].source