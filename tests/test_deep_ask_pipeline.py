"""Section summaries, rerank, study cache, and map-reduce for Deep Ask."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from langchain_core.documents import Document

from second_brain.ingestion.sections import (
    build_section_index,
    ensure_section_summaries,
    format_section_outline,
    load_section_index,
    parse_markdown_sections,
)
from second_brain.memory.rerank import rerank_documents
from second_brain.rag.study_cache import get_cached_study_guide, save_study_guide


def test_parse_markdown_sections_splits_headings():
    text = """# Lec10 Session Beans

Intro paragraph about enterprise beans.

## Stateful vs Stateless

Stateful beans keep client state on the server.

## Lifecycle

Create, passivate, activate, remove.
"""
    sections = parse_markdown_sections(text)
    titles = [s.title for s in sections]
    assert "Stateful vs Stateless" in titles
    assert "Lifecycle" in titles
    assert any("client state" in s.summary.lower() for s in sections)


def test_ensure_section_summaries_writes_cache(tmp_path):
    project = tmp_path / "Student notes"
    project.mkdir()
    (project / "memory").mkdir()
    md = project / "Lec10_Session_Beans_Clean.md"
    md.write_text(
        "## Session beans\n\nSession beans encapsulate business logic.\n\n## Lifecycle\n\nBeans are created by the container.\n",
        encoding="utf-8",
    )

    index = ensure_section_summaries(md, project_path=str(project))
    assert index is not None
    assert len(index.sections) >= 2

    cached = load_section_index(str(md.resolve()), project_path=str(project))
    assert cached is not None
    assert cached.content_hash == index.content_hash

    outline = format_section_outline(cached)
    assert "Session beans" in outline
    assert "Lifecycle" in outline


def test_rerank_prefers_token_overlap():
    docs = [
        Document(
            page_content="unrelated espresso grind settings",
            metadata={"source_path": "/a.md", "distance": 0.1},
        ),
        Document(
            page_content="session beans are stateful enterprise components",
            metadata={"source_path": "/lec10.md", "distance": 0.3},
        ),
    ]
    ranked = rerank_documents("session beans stateful", docs, top_k=1)
    assert len(ranked) == 1
    assert "session beans" in ranked[0].page_content.lower()


def test_study_guide_cache_roundtrip(tmp_path):
    project = tmp_path / "Topic"
    project.mkdir()
    (project / "memory").mkdir()
    source = project / "Lec10_Session_Beans_Clean.md"
    source.write_text("## One\n\nBody text.\n", encoding="utf-8")
    resolved = str(source.resolve())

    ensure_section_summaries(source, project_path=str(project))
    answer = "Outline\n1. Session beans\n\nStateful beans keep state."
    save_study_guide(
        "teach everything about lec10",
        resolved,
        answer,
        project_path=str(project),
    )

    cached = get_cached_study_guide(
        "teach everything about lec10",
        resolved,
        project_path=str(project),
    )
    assert cached == answer

    source.write_text("## One\n\nChanged body.\n", encoding="utf-8")
    ensure_section_summaries(source, project_path=str(project))
    assert get_cached_study_guide(
        "teach everything about lec10",
        resolved,
        project_path=str(project),
    ) is None


def test_needs_map_reduce_when_many_sections():
    from second_brain.ingestion.sections import SectionIndex, SectionSummary
    from second_brain.memory.recall import MemoryContext
    from second_brain.rag.map_reduce import needs_map_reduce

    index = SectionIndex(
        source_path="/vault/Lec10.md",
        content_hash="abc",
        sections=[
            SectionSummary(title=f"S{i}", summary="text", order=i)
            for i in range(1, 7)
        ],
    )
    memory = MemoryContext(text="x" * 100, claim_count=3)
    assert needs_map_reduce(memory, index, comprehensive=True) is True
    assert needs_map_reduce(memory, index, comprehensive=False) is False


def test_chat_uses_study_cache(tmp_path, monkeypatch):
    from second_brain.memory import claims as claims_mod
    from second_brain.memory.claims import ORIGIN_DUMP, ClaimCard
    from second_brain.memory.recall import MemoryContext
    from second_brain.rag import chain as chain_mod
    from second_brain.rag.chain import ChatMessage, chat_with_context

    monkeypatch.setattr(claims_mod, "ingest_file", lambda *_a, **_k: 0)
    project = tmp_path / "Proj"
    project.mkdir()
    (project / "memory").mkdir()
    source = project / "Lec10_Session_Beans_Clean.md"
    source.write_text("## Beans\n\nSession beans.\n", encoding="utf-8")
    resolved = str(source.resolve())

    card = ClaimCard(
        id="c1",
        claim="Session beans encapsulate business logic.",
        status="settled",
        origin=ORIGIN_DUMP,
        slug="beans",
        source_path=resolved,
        confidence=0.9,
    )
    claims_mod._write_claim_file(card, project_path=str(project), ingest=False)
    ensure_section_summaries(source, project_path=str(project))

    save_study_guide(
        "teach everything about lec10",
        resolved,
        "Cached study guide outline.",
        project_path=str(project),
    )

    monkeypatch.setattr(
        chain_mod,
        "recall_for_query",
        lambda *a, **k: MemoryContext(text="claims", claim_count=1),
    )

    def boom(*_a, **_k):
        raise AssertionError("cache hit must skip LLM")

    monkeypatch.setattr(chain_mod, "invoke_llm", boom)
    monkeypatch.setattr(chain_mod, "retrieve", boom)

    resp = chat_with_context(
        [ChatMessage(role="user", content="teach everything about lec10")],
        project_path=str(project),
    )
    assert "Cached study guide" in resp.answer
