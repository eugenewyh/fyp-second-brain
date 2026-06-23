import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from second_brain.graph import run_research
from second_brain.memory.chroma_store import collection_count


@pytest.fixture
def requires_indexed_docs():
    if collection_count() == 0:
        pytest.skip("No documents indexed — run ingest first")


@pytest.mark.slow
def test_run_research_end_to_end(requires_indexed_docs):
    result = run_research("What are servlets in Java?")
    assert result["plan"]
    assert result["retrieval_queries"]
    assert result["retrieved_docs"]
    assert result["analysis"]
    assert result["report"]
    assert len(result["report"]) > 100