import sys
from pathlib import Path

import pytest
from langchain_core.documents import Document

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from second_brain.memory import bm25_index as bm25_mod
from second_brain.memory.bm25_index import reset_bm25_index, search_bm25, update_bm25_index
from second_brain.memory.retriever import _rrf_merge, retrieve


@pytest.fixture
def isolated_bm25(tmp_path, monkeypatch):
    monkeypatch.setattr(bm25_mod, "CHROMA_PATH", tmp_path)
    monkeypatch.setattr(bm25_mod, "BM25_PATH", tmp_path / "bm25_corpus.pkl")
    monkeypatch.setattr(bm25_mod, "_state", None)
    reset_bm25_index()
    yield tmp_path
    monkeypatch.setattr(bm25_mod, "_state", None)
    reset_bm25_index()


def test_bm25_search_ranks_keyword(isolated_bm25):
    docs = [
        Document(
            page_content="General programming concepts and class design.",
            metadata={"source_hash": "aaa", "chunk_index": 0, "source": "a.md"},
        ),
        Document(
            page_content="The xyzzyplugh pattern ensures one instance only.",
            metadata={"source_hash": "bbb", "chunk_index": 0, "source": "b.md"},
        ),
    ]
    update_bm25_index(docs)

    hits = search_bm25("xyzzyplugh pattern", top_k=2)

    assert hits
    assert hits[0][0] == "bbb_0"
    assert hits[0][1] > hits[1][1]


def test_rrf_merge_boosts_shared_hits():
    merged = _rrf_merge([["doc_a", "doc_b"], ["doc_b", "doc_a"]], k=60)

    assert merged[0] in {"doc_a", "doc_b"}
    assert set(merged[:2]) == {"doc_a", "doc_b"}


def test_hybrid_retrieve_prefers_bm25_keyword(monkeypatch, isolated_bm25):
    keyword_doc = Document(
        page_content="The xyzzyplugh pattern limits instantiation.",
        metadata={
            "source_hash": "keyword",
            "chunk_index": 0,
            "source": "patterns.md",
            "source_path": "/vault/patterns.md",
        },
    )
    filler_doc = Document(
        page_content="Object oriented design principles overview.",
        metadata={
            "source_hash": "filler",
            "chunk_index": 0,
            "source": "oop.md",
            "source_path": "/vault/oop.md",
        },
    )
    update_bm25_index([keyword_doc, filler_doc])

    def fake_vector_candidates(query: str, fetch_k: int):
        return ["filler_0"], {"filler_0": filler_doc}

    class FakeCollection:
        def count(self):
            return 2

    monkeypatch.setattr(
        "second_brain.memory.retriever._vector_candidates",
        fake_vector_candidates,
    )
    monkeypatch.setattr(
        "second_brain.memory.retriever.get_collection",
        lambda: FakeCollection(),
    )
    monkeypatch.setenv("RETRIEVAL_HYBRID", "true")

    from second_brain import config

    monkeypatch.setattr(config, "RETRIEVAL_HYBRID", True)

    results = retrieve("xyzzyplugh pattern", top_k=1)

    assert len(results) == 1
    assert results[0].metadata["source_hash"] == "keyword"
