"""Topic-scoped memory: fail closed, no sibling leak, watch decay."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from langchain_core.documents import Document

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from second_brain.memory.claims import (
    ORIGIN_DUMP,
    ORIGIN_WATCH,
    ClaimCard,
    expire_watch_claims,
    list_claims,
    upsert_claims_from_learning,
    upsert_sourced_claims,
    SourcedClaim,
    merge_topic_claims,
)
from second_brain.memory.digest_link import digest_and_link
from second_brain.memory.learning import (
    SKIP_NO_TOPIC_DETAIL,
    LearningCard,
    persist_research_memory,
    project_memory_root,
)
from second_brain.memory.retriever import _doc_in_any_project, _doc_in_project

SAMPLE_REPORT = """## Executive Summary
Specialized agents reduce hallucination under critique loops.

## Key Findings
- Specialized agents reduce hallucination under critique loops.
- Hybrid retrieval combines personal and web sources.

## Identified Gaps
- Unclear how memory compounds across sessions?
"""


def _noop_ingest(*_a, **_k):
    return 0


def _learning(text: str) -> LearningCard:
    return LearningCard(
        id="learn1",
        query="watch run",
        summary=text,
        key_findings=[text],
        open_questions=[],
        source_stats={},
        confidence=0.7,
        confidence_reasons=[],
        critique_summary="",
    )


def test_persist_without_project_path_writes_nothing(tmp_path, monkeypatch):
    from second_brain.memory import claims as claims_mod
    from second_brain.memory import learning as learning_mod

    monkeypatch.setattr(claims_mod, "ingest_file", _noop_ingest)
    monkeypatch.setattr(learning_mod, "ingest_file", _noop_ingest)
    meta = persist_research_memory(
        {
            "query": "What is multi-agent research?",
            "report": SAMPLE_REPORT,
            "retrieval_stats": {"web": 2},
            "critique_approved": True,
        },
        project_path=None,
        session_id="sess-1",
        write_report=True,
        ingest=False,
    )
    assert meta["memory_written"] is False
    assert meta["memory_detail"] == SKIP_NO_TOPIC_DETAIL
    assert meta["claim_count"] == 0
    assert meta["contested_claims"] == []
    root = project_memory_root(None)
    assert "documents" not in str(root).lower() or "unbound" in str(root)
    assert not list(tmp_path.rglob("*.md"))
    assert not root.exists()


def test_digest_requires_project_path():
    with pytest.raises(ValueError, match="project_path"):
        digest_and_link(text="A note long enough to remember.", project_path=None, ingest=False)


def test_upsert_without_topic_writes_nothing(tmp_path, monkeypatch):
    from second_brain.memory import claims as claims_mod

    monkeypatch.setattr(claims_mod, "ingest_file", _noop_ingest)
    result = upsert_sourced_claims(
        [SourcedClaim(claim="Diffusion models generate text by denoising.", source_quote="denoising")],
        project_path=None,
        ingest=False,
    )
    assert result.created == []
    assert not list(tmp_path.rglob("*.md"))


def test_unapproved_research_mints_contested_not_settled(tmp_path, monkeypatch):
    from second_brain.memory import claims as claims_mod
    from second_brain.memory import learning as learning_mod

    project = tmp_path / "dlm"
    project.mkdir()
    monkeypatch.setattr(claims_mod, "ingest_file", _noop_ingest)
    monkeypatch.setattr(learning_mod, "ingest_file", _noop_ingest)
    meta = persist_research_memory(
        {
            "query": "How does DiffusionGemma decode?",
            "report": SAMPLE_REPORT,
            "retrieval_stats": {"personal": 2},
            "critique_approved": False,
            "critique_structured": {
                "grounding_passed": False,
                "verdict": "revise",
                "source": "llm",
                "issues": [{"severity": "blocking"}],
            },
        },
        project_path=str(project),
        session_id="sess-2",
        write_report=True,
        ingest=False,
    )
    assert meta["memory_written"] is True
    assert (project / "research").is_dir()
    contested = list_claims(str(project), status="contested")
    settled = list_claims(str(project), status="settled")
    assert contested
    assert settled == []
    assert meta["contested_claims"]


def test_forced_max_revisions_are_contested(tmp_path, monkeypatch):
    from second_brain.memory import claims as claims_mod
    from second_brain.memory import learning as learning_mod

    project = tmp_path / "dlm"
    project.mkdir()
    monkeypatch.setattr(claims_mod, "ingest_file", _noop_ingest)
    monkeypatch.setattr(learning_mod, "ingest_file", _noop_ingest)
    meta = persist_research_memory(
        {
            "query": "How does DiffusionGemma decode?",
            "report": SAMPLE_REPORT,
            "retrieval_stats": {"web": 3},
            "critique_approved": True,
            "critique_structured": {
                "grounding_passed": False,
                "verdict": "approved",
                "source": "forced_max_revisions",
                "issues": [],
            },
        },
        project_path=str(project),
        ingest=False,
    )
    assert meta["memory_written"] is True
    assert list_claims(str(project), status="settled") == []
    assert list_claims(str(project), status="contested")


def test_retriever_does_not_leak_sibling_topic():
    prefix = "/vault/topics/dlm"
    sibling = Document(
        page_content="espresso",
        metadata={"source_path": "/vault/topics/dlm-eval/note.md"},
    )
    own = Document(
        page_content="diffusion",
        metadata={"source_path": "/vault/topics/dlm/note.md"},
    )
    nested = Document(
        page_content="ok",
        metadata={"source_path": "/vault/topics/dlm"},
    )
    assert _doc_in_project(sibling, prefix) is False
    assert _doc_in_project(own, prefix) is True
    assert _doc_in_project(nested, prefix) is True


def test_expired_watch_claim_archived_dump_untouched(tmp_path, monkeypatch):
    from second_brain.memory import claims as claims_mod

    project = tmp_path / "Topic"
    project.mkdir()
    monkeypatch.setattr(claims_mod, "ingest_file", _noop_ingest)
    upsert_sourced_claims(
        [
            SourcedClaim(
                claim="RAG still fabricates citations when the corpus is thin.",
                source_quote="fabricates citations when the corpus is thin",
            )
        ],
        project_path=str(project),
        origin=ORIGIN_DUMP,
        ingest=False,
    )
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
    future = (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat()
    watch = ClaimCard(
        id="watch1",
        claim="Hybrid retrieval should prefer personal notes before the web search layer.",
        status="settled",
        origin=ORIGIN_WATCH,
        expires=yesterday,
        updated=yesterday,
        created=yesterday,
    )
    claims_mod._write_claim_file(watch, project_path=str(project), ingest=False)
    live_watch = ClaimCard(
        id="watch2",
        claim="Watch briefs should stay scoped to this topic folder only.",
        status="settled",
        origin=ORIGIN_WATCH,
        expires=future,
        updated=future,
        created=future,
    )
    claims_mod._write_claim_file(live_watch, project_path=str(project), ingest=False)

    n = expire_watch_claims(str(project), ingest=False)
    assert n == 1
    dumps = [c for c in list_claims(str(project), status="settled") if c.origin == ORIGIN_DUMP]
    assert len(dumps) == 1
    superseded = [c for c in list_claims(str(project), status="superseded") if c.origin == ORIGIN_WATCH]
    assert len(superseded) == 1
    still_live = [c for c in list_claims(str(project), status="settled") if c.origin == ORIGIN_WATCH]
    assert len(still_live) == 1
    assert Path(dumps[0].path).is_file()


def test_contested_watch_against_dump_does_not_expire(tmp_path, monkeypatch):
    from second_brain.memory import claims as claims_mod

    project = tmp_path / "Topic"
    project.mkdir()
    monkeypatch.setattr(claims_mod, "ingest_file", _noop_ingest)
    dump_text = "RAG still fabricates citations when the corpus is thin."
    watch_text = "RAG often fabricates citations if the personal corpus is thin and unverified."
    upsert_sourced_claims(
        [SourcedClaim(claim=dump_text, source_quote="fabricates citations when the corpus is thin")],
        project_path=str(project),
        origin=ORIGIN_DUMP,
        ingest=False,
    )
    upsert_claims_from_learning(
        _learning(watch_text),
        project_path=str(project),
        origin=ORIGIN_WATCH,
        ingest=False,
    )
    contested = list_claims(str(project), status="contested")
    assert contested
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
    card = contested[0]
    card.expires = yesterday
    claims_mod._write_claim_file(card, project_path=str(project), ingest=False)
    n = expire_watch_claims(str(project), ingest=False)
    assert n == 0
    assert list_claims(str(project), status="contested")
    dumps = [c for c in list_claims(str(project), status="settled") if c.origin == ORIGIN_DUMP]
    assert dumps


def test_merge_copies_claims_and_rewrites_supersedes(tmp_path, monkeypatch):
    from second_brain.memory import claims as claims_mod

    monkeypatch.setattr(claims_mod, "ingest_file", _noop_ingest)
    src = tmp_path / "JustGRPO"
    dest = tmp_path / "DLM"
    src.mkdir()
    dest.mkdir()

    old = ClaimCard(
        id="old1",
        claim="JustGRPO needs a verifier loop before it can settle a claim.",
        status="superseded",
        origin=ORIGIN_DUMP,
        slug="justgrpo-verifier",
    )
    claims_mod._write_claim_file(old, project_path=str(src), ingest=False)
    new = ClaimCard(
        id="new1",
        claim="JustGRPO should keep contested siblings visible after a verifier fail.",
        status="settled",
        origin=ORIGIN_DUMP,
        supersedes="old1",
        slug="justgrpo-contested",
    )
    claims_mod._write_claim_file(new, project_path=str(src), ingest=False)
    twin = ClaimCard(
        id="dest1",
        claim="JustGRPO needs a verifier loop before it can settle a claim.",
        status="settled",
        origin=ORIGIN_DUMP,
        slug="already-there",
    )
    claims_mod._write_claim_file(twin, project_path=str(dest), ingest=False)

    result = merge_topic_claims(str(src), str(dest), ingest=False)
    assert result["copied"] == 1
    assert result["skipped"] == 1
    assert result["dest_name"] == "DLM"
    source_left = list_claims(str(src), status=None)
    assert {c.id for c in source_left} == {"old1", "new1"}
    dest_cards = list_claims(str(dest), status=None)
    dest_ids = {c.id for c in dest_cards}
    assert "dest1" in dest_ids
    copied = [c for c in dest_cards if c.id != "dest1"]
    assert len(copied) == 1
    assert copied[0].id == "new1"
    assert copied[0].supersedes == "dest1"


def test_claims_matching_query_includes_contested(tmp_path, monkeypatch):
    from second_brain.memory import claims as claims_mod
    from second_brain.memory.claims import claims_matching_query
    from second_brain.memory.recall import recall_for_query

    monkeypatch.setattr(claims_mod, "ingest_file", _noop_ingest)
    project = tmp_path / "Topic"
    project.mkdir()
    settled = ClaimCard(
        id="s1",
        claim="Burr grinders matter more than machine upgrades for home espresso.",
        status="settled",
        origin=ORIGIN_DUMP,
        slug="burr-grinders",
        confidence=0.9,
    )
    contested = ClaimCard(
        id="c1",
        claim="Machine upgrades matter more than burr grinders for home espresso.",
        status="contested",
        origin=ORIGIN_WATCH,
        slug="machine-upgrades",
        confidence=0.4,
    )
    claims_mod._write_claim_file(settled, project_path=str(project), ingest=False)
    claims_mod._write_claim_file(contested, project_path=str(project), ingest=False)

    matched = claims_matching_query("home espresso grinders vs machine", str(project), limit=5)
    statuses = {c.status for c in matched}
    assert "settled" in statuses
    assert "contested" in statuses
    assert matched[0].status == "settled"

    ctx = recall_for_query("home espresso grinders vs machine", project_path=str(project))
    assert ctx.claim_count >= 2
    assert ctx.contested_claims
    assert "(contested)" in (ctx.text or "")


def test_retrieve_union_includes_second_prefix_default_still_partitioned():
    dlm = "/vault/topics/dlm"
    thesis = "/vault/topics/thesis"
    sibling = Document(
        page_content="espresso",
        metadata={"source_path": "/vault/topics/dlm-eval/note.md"},
    )
    own = Document(
        page_content="diffusion",
        metadata={"source_path": "/vault/topics/dlm/note.md"},
    )
    extra = Document(
        page_content="chapter outline",
        metadata={"source_path": "/vault/topics/thesis/outline.md"},
    )
    assert _doc_in_project(sibling, dlm) is False
    assert _doc_in_project(own, dlm) is True
    assert _doc_in_project(extra, dlm) is False
    assert _doc_in_any_project(own, [dlm]) is True
    assert _doc_in_any_project(extra, [dlm]) is False
    assert _doc_in_any_project(extra, [dlm, thesis]) is True
    assert _doc_in_any_project(sibling, [dlm, thesis]) is False
