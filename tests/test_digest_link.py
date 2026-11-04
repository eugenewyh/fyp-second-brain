"""Tests for Remember-path digest: sourced claims, revise, idempotency."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from second_brain.memory.claims import SourcedClaim, list_claims
from second_brain.memory.digest_link import (
    content_hash,
    digest_and_link,
    digest_many,
    is_memory_trace_path,
    quote_in_source,
)
from second_brain.memory.learning import project_memory_path


NOTE = (
    "Retrieval-augmented generation still fabricates citations when the corpus is thin. "
    "Long-context models can beat RAG on short document sets. "
    "Students should verify every citation against the original PDF."
)

NOTE_B = (
    "Sourdough starter needs regular feeding with flour and water. "
    "A warm kitchen speeds fermentation but can overproof the dough. "
    "Bakers score the loaf so steam escapes in a controlled pattern."
)


def _noop_ingest(*_a, **_k):
    return 0


@pytest.fixture
def project(tmp_path, monkeypatch):
    from second_brain.memory import digest_link as dl
    from second_brain.memory import claims as claims_mod
    from second_brain.memory import learning as learning_mod

    monkeypatch.setattr(dl, "ingest_file", _noop_ingest)
    monkeypatch.setattr(claims_mod, "ingest_file", _noop_ingest)
    monkeypatch.setattr(learning_mod, "ingest_file", _noop_ingest)
    monkeypatch.setattr(learning_mod, "_optional_llm_polish_sections", lambda body: body)
    return tmp_path / "RAG-Grounding"


def test_quote_in_source_requires_span():
    assert quote_in_source("still fabricates citations", NOTE)
    assert not quote_in_source("quantum supremacy is guaranteed", NOTE)


def test_refuses_memory_trace_paths():
    assert is_memory_trace_path("/vault/proj/memory/claims/foo.md")
    assert is_memory_trace_path("/vault/proj/research/report.md")
    assert not is_memory_trace_path("/vault/proj/inbox/note.md")


def test_extract_drops_unverifiable_quotes(monkeypatch):
    from second_brain.memory import digest_link as dl

    class Dummy:
        content = (
            '[{"claim": "Invented belief", "source_quote": "not in the document"},'
            ' {"claim": "RAG still fabricates citations on thin corpora.",'
            '  "source_quote": "Retrieval-augmented generation still fabricates citations when the corpus is thin."}]'
        )

    monkeypatch.setattr("second_brain.memory.llm.invoke_llm", lambda *a, **k: Dummy())
    sourced = dl.extract_sourced_claims(NOTE)
    assert all(quote_in_source(s.source_quote, NOTE) for s in sourced)
    assert len(sourced) <= 7
    assert any("fabricates" in s.claim.lower() for s in sourced)


def test_extract_caps_at_seven(monkeypatch):
    from second_brain.memory import digest_link as dl

    quote = "Students should verify every citation against the original PDF."
    payload = [
        {"claim": f"Distinct claim {i} about verifying citations in student workflows.", "source_quote": quote}
        for i in range(20)
    ]

    class Dummy:
        content = __import__("json").dumps(payload)

    monkeypatch.setattr("second_brain.memory.llm.invoke_llm", lambda *a, **k: Dummy())
    sourced = dl.extract_sourced_claims(NOTE)
    assert len(sourced) == 7


def test_digest_creates_sourced_claim_and_linked_section(project, monkeypatch):
    from second_brain.memory import digest_link as dl

    quote = "Retrieval-augmented generation still fabricates citations when the corpus is thin."
    monkeypatch.setattr(
        dl,
        "extract_sourced_claims",
        lambda *a, **k: [SourcedClaim(claim="RAG still fabricates citations on thin corpora.", source_quote=quote)],
    )
    result = digest_and_link(text=NOTE, title="RAG note", project_path=str(project), ingest=False)
    assert result.claims_created == 1
    assert result.claims_revised == 0
    saved = Path(result.saved_path)
    assert saved.is_file()
    body = saved.read_text(encoding="utf-8")
    assert "## Linked" in body
    claims = list_claims(str(project), status="active")
    assert len(claims) == 1
    assert claims[0].source_quote
    assert project_memory_path(str(project)).is_file()
    assert not (project / "memory" / "learnings").exists()
    assert not (project / "research").exists()


def test_prefer_revise_over_create(project, monkeypatch):
    from second_brain.memory import digest_link as dl

    quote = "Retrieval-augmented generation still fabricates citations when the corpus is thin."
    monkeypatch.setattr(
        dl,
        "extract_sourced_claims",
        lambda *a, **k: [
            SourcedClaim(
                claim="RAG still fabricates citations on thin corpora.",
                source_quote=quote,
            )
        ],
    )
    digest_and_link(text=NOTE, title="first", project_path=str(project), ingest=False)

    monkeypatch.setattr(
        dl,
        "extract_sourced_claims",
        lambda *a, **k: [
            SourcedClaim(
                claim="RAG still fabricates citations when the personal corpus is thin.",
                source_quote=quote,
            )
        ],
    )
    # Different hash so it is not the idempotent path
    other = NOTE + " Extra sentence about verifying PDFs."
    result = digest_and_link(text=other, title="second", project_path=str(project), ingest=False)
    assert result.claims_revised >= 1
    active = list_claims(str(project), status="active")
    assert len(active) == 1
    assert active[0].supersedes


def test_idempotent_same_hash_reuses_inbox(project, monkeypatch):
    from second_brain.memory import digest_link as dl

    quote = "Long-context models can beat RAG on short document sets."
    calls = {"n": 0}

    def _extract(*a, **k):
        calls["n"] += 1
        return [
            SourcedClaim(
                claim="Long-context models can beat RAG on short sets.",
                source_quote=quote,
            )
        ]

    monkeypatch.setattr(dl, "extract_sourced_claims", _extract)
    first = digest_and_link(text=NOTE, title="RAG note", project_path=str(project), ingest=False)
    second = digest_and_link(text=NOTE, title="RAG note again", project_path=str(project), ingest=False)
    assert first.content_hash == second.content_hash == content_hash(NOTE)
    assert second.idempotent is True
    assert Path(first.saved_path) == Path(second.saved_path)
    assert calls["n"] == 1
    assert second.summary == "Already remembered this dump"
    inbox = list((project / "inbox").glob("*.md"))
    assert len(inbox) == 1
    # Identical restatement should not mint extra claim files
    all_claims = list_claims(str(project), status=None)
    active = list_claims(str(project), status="active")
    assert len(active) == 1
    assert len(all_claims) == 1


def test_digest_many_one_extract_two_files(project, monkeypatch):
    from second_brain.memory import digest_link as dl

    calls = {"n": 0}

    def _extract(text, **k):
        calls["n"] += 1
        out = []
        if "fabricates" in text:
            out.append(
                SourcedClaim(
                    claim="RAG still fabricates citations on thin corpora.",
                    source_quote="Retrieval-augmented generation still fabricates citations when the corpus is thin.",
                )
            )
        if "Sourdough" in text or "sourdough" in text.lower():
            out.append(
                SourcedClaim(
                    claim="Sourdough starter needs regular feeding.",
                    source_quote="Sourdough starter needs regular feeding with flour and water.",
                )
            )
        return out

    monkeypatch.setattr(dl, "extract_sourced_claims", _extract)

    inbox = project / "inbox"
    inbox.mkdir(parents=True)
    p1 = inbox / "rag.md"
    p2 = inbox / "bread.md"
    p1.write_text(NOTE, encoding="utf-8")
    p2.write_text(NOTE_B, encoding="utf-8")

    result = digest_many(
        paths=[str(p1), str(p2)],
        title="Recipes",
        project_path=str(project),
        ingest=False,
    )
    assert calls["n"] == 1
    assert result["claims_created"] >= 1
    assert "results" in result
    assert len(result["results"]) == 2
    assert Path(result["results"][0]["saved_path"]).is_file()
    assert Path(result["results"][1]["saved_path"]).is_file()
    assert project_memory_path(str(project)).is_file()
