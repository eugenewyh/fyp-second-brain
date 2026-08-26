"""Tests: dump claims are protected from watch overwrite."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from second_brain.memory.claims import (
    ORIGIN_DUMP,
    ORIGIN_WATCH,
    SourcedClaim,
    list_claims,
    upsert_claims_from_learning,
    upsert_sourced_claims,
)
from second_brain.memory.learning import LearningCard


def _noop_ingest(*_a, **_k):
    return 0


@pytest.fixture
def project(tmp_path, monkeypatch):
    from second_brain.memory import claims as claims_mod
    from second_brain.memory import learning as learning_mod

    monkeypatch.setattr(claims_mod, "ingest_file", _noop_ingest)
    monkeypatch.setattr(learning_mod, "ingest_file", _noop_ingest)
    return tmp_path / "Topic"


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


def test_dump_and_watch_same_text_dump_wins(project: Path):
    text = "RAG still fabricates citations when the corpus is thin."
    upsert_sourced_claims(
        [SourcedClaim(claim=text, source_quote="fabricates citations when the corpus is thin")],
        project_path=str(project),
        origin=ORIGIN_DUMP,
        ingest=False,
    )
    upsert_claims_from_learning(
        _learning(text),
        project_path=str(project),
        origin=ORIGIN_WATCH,
        ingest=False,
    )
    settled = list_claims(str(project), status="settled")
    dumps = [c for c in settled if c.origin == ORIGIN_DUMP]
    assert len(dumps) == 1
    assert dumps[0].claim.startswith("RAG still fabricates")
    contested = list_claims(str(project), status="contested")
    # identical watch restatement does not mint a contested sibling
    assert contested == []


def test_watch_contests_similar_dump_does_not_supersede(project: Path):
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
    dumps = [c for c in list_claims(str(project), status="settled") if c.origin == ORIGIN_DUMP]
    assert len(dumps) == 1
    assert dumps[0].status in {"settled", "active"}
    contested = list_claims(str(project), status="contested")
    assert len(contested) == 1
    assert contested[0].origin == ORIGIN_WATCH


def test_watch_may_revise_watch_claim(project: Path):
    first = "Hybrid retrieval should prefer personal notes before the web."
    second = "Hybrid retrieval should prefer personal notes before web search."
    upsert_claims_from_learning(
        _learning(first),
        project_path=str(project),
        origin=ORIGIN_WATCH,
        ingest=False,
    )
    upsert_claims_from_learning(
        _learning(second),
        project_path=str(project),
        origin=ORIGIN_WATCH,
        ingest=False,
    )
    settled = list_claims(str(project), status="settled")
    superseded = list_claims(str(project), status="superseded")
    assert any(c.origin == ORIGIN_WATCH for c in settled)
    assert superseded


def test_claim_note_uses_plain_body(project: Path):
    upsert_sourced_claims(
        [SourcedClaim(claim="Diffusion models generate text by denoising.", source_quote="denoising")],
        project_path=str(project),
        origin=ORIGIN_DUMP,
        ingest=False,
    )
    cards = list_claims(str(project), status=None)
    assert cards
    text = Path(cards[0].path).read_text(encoding="utf-8")
    assert "# What we know" in text
    assert "How sure: from your notes" in text
    assert "_Confidence:" not in text
    assert "# Claim:" not in text
