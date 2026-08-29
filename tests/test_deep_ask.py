"""Deep Ask: source pinning and comprehensive explain-from-memory."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from langchain_core.documents import Document

from second_brain.memory.claims import ORIGIN_DUMP, ClaimCard, claims_for_source
from second_brain.memory.recall import recall_for_query
from second_brain.rag.ask_depth import ask_depth, resolve_pinned_source, source_path_matches
from second_brain.rag.chain import ChatMessage, chat_with_context


def _noop_ingest(*_a, **_k):
    return 0


def test_ask_depth_comprehensive_for_teach_everything():
    assert ask_depth("teach everything about lec10") == "comprehensive"
    assert ask_depth("walk me through all about session beans") == "comprehensive"
    assert ask_depth("what is a session bean?") == "quick"
    assert ask_depth("teach me about session beans") == "quick"


def test_resolve_pinned_source_from_lec10_hint(tmp_path, monkeypatch):
    from second_brain.memory import claims as claims_mod

    monkeypatch.setattr(claims_mod, "ingest_file", _noop_ingest)
    project = tmp_path / "Student notes"
    library = project / "library"
    library.mkdir(parents=True)
    lec_path = library / "Lec10_Session_Beans_Clean.md"
    lec_path.write_text("# Lec10\n\nSession beans are cool.\n", encoding="utf-8")

    card = ClaimCard(
        id="lec10-1",
        claim="Stateful session beans maintain client state across calls.",
        status="settled",
        origin=ORIGIN_DUMP,
        slug="stateful-beans",
        source_path=str(lec_path),
        confidence=0.9,
    )
    claims_mod._write_claim_file(card, project_path=str(project), ingest=False)

    pinned = resolve_pinned_source("teach everything about lec10", str(project))
    assert pinned is not None
    assert pinned.endswith("Lec10_Session_Beans_Clean.md")


def test_resolve_pinned_source_prefers_open_note(tmp_path):
    project = tmp_path / "Topic"
    project.mkdir()
    note = project / "Lec10_Session_Beans_Clean.md"
    note.write_text("# Lec10\n", encoding="utf-8")

    pinned = resolve_pinned_source(
        "teach me everything about this lecture",
        str(project),
        note_path=str(note),
    )
    assert pinned is not None
    assert Path(pinned).name == "Lec10_Session_Beans_Clean.md"


def test_source_path_matches_by_filename():
    assert source_path_matches(
        "/vault/library/Lec10_Session_Beans_Clean.md",
        "library/Lec10_Session_Beans_Clean.md",
    )
    assert source_path_matches("Lec10_Session_Beans_Clean.md", "/vault/Lec10_Session_Beans_Clean.md")
    assert not source_path_matches("/vault/Lec05_Foo.md", "/vault/Lec10_Bar.md")


def test_claims_for_source_returns_all_from_file(tmp_path, monkeypatch):
    from second_brain.memory import claims as claims_mod

    monkeypatch.setattr(claims_mod, "ingest_file", _noop_ingest)
    project = tmp_path / "Proj"
    project.mkdir()
    source = str(project / "Lec10_Session_Beans_Clean.md")

    for i in range(6):
        card = ClaimCard(
            id=f"lec10-{i}",
            claim=f"Claim number {i} about session beans.",
            status="settled",
            origin=ORIGIN_DUMP,
            slug=f"claim-{i}",
            source_path=source,
            confidence=0.8,
        )
        claims_mod._write_claim_file(card, project_path=str(project), ingest=False)

    other = ClaimCard(
        id="lec05-1",
        claim="Unrelated lecture claim.",
        status="settled",
        origin=ORIGIN_DUMP,
        slug="other",
        source_path=str(project / "Lec05_Other.md"),
        confidence=0.8,
    )
    claims_mod._write_claim_file(other, project_path=str(project), ingest=False)

    matched = claims_for_source(str(project), source)
    assert len(matched) == 6
    assert all(c.source_path == source for c in matched)


def test_retrieve_filters_by_pinned_source(monkeypatch):
    from second_brain.memory.retriever import retrieve

    docs = [
        Document(page_content="lec10 chunk", metadata={"source_path": "/vault/Lec10_Session_Beans_Clean.md"}),
        Document(page_content="lec05 chunk", metadata={"source_path": "/vault/Lec05_Other.md"}),
        Document(page_content="lec10 chunk 2", metadata={"source_path": "/vault/Lec10_Session_Beans_Clean.md"}),
    ]

    monkeypatch.setattr(
        "second_brain.memory.retriever.get_collection",
        lambda: type("C", (), {"count": lambda self: 3})(),
    )
    monkeypatch.setattr(
        "second_brain.memory.retriever.get_embeddings",
        lambda: type("E", (), {"embed_query": lambda self, q: [0.1]})(),
    )
    monkeypatch.setattr(
        "second_brain.memory.retriever.get_collection",
        lambda: type("C", (), {"count": lambda self: 3, "query": lambda self, **k: {
            "documents": [[d.page_content for d in docs]],
            "metadatas": [[d.metadata for d in docs]],
            "distances": [[0.1, 0.2, 0.3]],
        }})(),
    )

    out = retrieve(
        "session beans",
        top_k=5,
        source_path_filter="/vault/Lec10_Session_Beans_Clean.md",
    )
    assert len(out) == 2
    assert all("Lec10" in (d.metadata.get("source_path") or "") for d in out)


def test_recall_comprehensive_loads_all_pinned_claims(tmp_path, monkeypatch):
    from second_brain.memory import claims as claims_mod

    monkeypatch.setattr(claims_mod, "ingest_file", _noop_ingest)
    project = tmp_path / "Proj"
    project.mkdir()
    source = str(project / "Lec10_Session_Beans_Clean.md")
    Path(source).write_text("# Lec10\n", encoding="utf-8")

    for i in range(8):
        card = ClaimCard(
            id=f"c{i}",
            claim=f"Pinned claim {i} on session beans.",
            status="settled",
            origin=ORIGIN_DUMP,
            slug=f"c{i}",
            source_path=source,
            confidence=0.85,
        )
        claims_mod._write_claim_file(card, project_path=str(project), ingest=False)

    monkeypatch.setattr(
        "second_brain.memory.recall.retrieve",
        lambda *a, **k: [],
    )

    ctx = recall_for_query(
        "teach everything about lec10",
        project_path=str(project),
        depth="comprehensive",
        pinned_source=source,
    )
    assert ctx.claim_count == 8
    assert "Pinned claim 7" in (ctx.text or "")
    assert "[Pinned source]" in (ctx.text or "")


def test_chat_comprehensive_uses_deep_prompt(tmp_path, monkeypatch):
    from second_brain.memory import claims as claims_mod
    from second_brain.memory.recall import MemoryContext
    from second_brain.rag import chain as chain_mod

    monkeypatch.setattr(claims_mod, "ingest_file", _noop_ingest)
    project = tmp_path / "Proj"
    project.mkdir()
    source = str(project / "Lec10_Session_Beans_Clean.md")
    Path(source).write_text("# Lec10\n", encoding="utf-8")

    card = ClaimCard(
        id="c1",
        claim="Session beans can be stateful or stateless.",
        status="settled",
        origin=ORIGIN_DUMP,
        slug="beans",
        source_path=source,
        confidence=0.9,
    )
    claims_mod._write_claim_file(card, project_path=str(project), ingest=False)

    memory = MemoryContext(
        text="[Project claims]\n- [[beans]] Session beans can be stateful or stateless.",
        claim_count=1,
    )
    monkeypatch.setattr(chain_mod, "recall_for_query", lambda *a, **k: memory)
    monkeypatch.setattr(chain_mod, "retrieve", lambda *a, **k: [])

    captured: dict[str, object] = {}

    def fake_llm(messages, role="main", **_k):
        captured["role"] = role
        captured["prompt"] = "\n".join(getattr(m, "content", "") or "" for m in messages)

        class Dummy:
            content = "Outline\n1. Stateful\n2. Stateless"

        return Dummy()

    monkeypatch.setattr(chain_mod, "invoke_llm", fake_llm)
    resp = chat_with_context(
        [ChatMessage(role="user", content="teach everything about lec10")],
        project_path=str(project),
    )
    assert resp.thin_memory is False
    assert captured["role"] == "main"
    prompt = str(captured["prompt"]).lower()
    assert "outline" in prompt or "structured study" in prompt
