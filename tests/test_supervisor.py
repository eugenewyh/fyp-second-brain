"""Supervisor + tool policy: file dumps, refuse espresso, research only when allowed."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from second_brain.agent.policy import (
    apply_policy,
    fallback_job,
    force_file,
    has_search_intent,
    research_allowed,
)
from second_brain.agent.supervisor import (
    REFUSE_MESSAGE,
    RecallSnapshot,
    decide_act,
)

SGLANG_DUMP = (
    "I now think schema-constrained decoding for diffusion LMs shipped in SGLang last week. "
    "I still don’t trust tok/s without GPU and batch size named. "
    "Parallel decode that breaks JSON is still a fail for me."
)
ESPRESSO = "What is the best espresso machine for a small kitchen?"
IN_TOPIC = "What do I care about with DLMs?"
FIND_PAPERS = "Find papers on JustGRPO"


def _snap(count: int = 0, previews: list[str] | None = None) -> RecallSnapshot:
    return RecallSnapshot(
        topic="dlm",
        matching_claim_count=count,
        claim_previews=previews or [],
    )


@pytest.fixture
def no_recall(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "second_brain.agent.supervisor.recall_snapshot",
        lambda *_a, **_k: _snap(0),
    )


@pytest.fixture
def matching_recall(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "second_brain.agent.supervisor.recall_snapshot",
        lambda *_a, **_k: _snap(5, ["Constrained decoding for diffusion LMs."]),
    )


def test_search_intent_includes_curly_apostrophe():
    assert has_search_intent("what's new on DiffusionGemma")
    assert has_search_intent("what’s new on DiffusionGemma")
    assert has_search_intent("Find papers on JustGRPO")
    assert not has_search_intent(ESPRESSO)


def test_notes_intent_blocks_research():
    from second_brain.agent.policy import has_notes_intent

    q = "According to my notes, what do I care about in diffusion language models besides raw generation speed?"
    assert has_notes_intent(q)
    assert research_allowed(q, matching_claim_count=0) is False
    assert apply_policy("research", text=q, matching_claim_count=0) == "refuse"
    assert apply_policy("research", text=q, matching_claim_count=4) == "answer"


def test_synthesis_cite_notes_is_research_policy():
    from second_brain.agent.policy import has_notes_intent, has_synthesis_intent

    q = (
        "Synthesise my stance on home espresso: grind vs dose, milk steaming, "
        "and what I'd buy next. Cite my notes."
    )
    assert has_synthesis_intent(q)
    assert has_notes_intent(q)
    assert research_allowed(q, matching_claim_count=4) is True
    assert apply_policy("answer", text=q, matching_claim_count=4) == "research"
    assert fallback_job(text=q, matching_claim_count=4) == "research"


def test_research_denied_without_search_or_matches():
    assert research_allowed(ESPRESSO, matching_claim_count=0) is False
    assert apply_policy("research", text=ESPRESSO, matching_claim_count=0) == "refuse"


def test_research_allowed_with_search_intent_and_zero_matches():
    assert research_allowed(FIND_PAPERS, matching_claim_count=0) is True
    assert apply_policy("refuse", text=FIND_PAPERS, matching_claim_count=0) == "research"


def test_research_allowed_with_research_intent_and_zero_matches():
    from second_brain.agent.policy import has_research_intent

    text = "Research indoor plant care for beginners"
    assert has_research_intent(text)
    assert research_allowed(text, matching_claim_count=0) is True
    assert apply_policy("refuse", text=text, matching_claim_count=0) == "research"


def test_forced_research_on_empty_topic():
    assert apply_policy(
        "research",
        text=ESPRESSO,
        matching_claim_count=0,
        forced=True,
    ) == "research"


def test_research_allowed_with_matches_and_deepen():
    text = "Go deeper on constrained decoding"
    assert research_allowed(text, matching_claim_count=3) is True
    assert apply_policy("research", text=text, matching_claim_count=3) == "research"
    assert apply_policy("research", text=text, matching_claim_count=0) == "refuse"


def test_attachments_always_file():
    assert force_file(text=ESPRESSO, has_attachments=True) is True
    assert apply_policy("research", text=ESPRESSO, matching_claim_count=0, has_attachments=True) == "file"
    assert apply_policy("answer", text="What is this?", matching_claim_count=0, has_attachments=True) == "file"


def test_answer_with_zero_matches_refuses():
    assert apply_policy("answer", text=ESPRESSO, matching_claim_count=0) == "refuse"
    assert apply_policy("answer", text=IN_TOPIC, matching_claim_count=4) == "answer"


def test_file_on_question_without_attachments_coerced():
    assert apply_policy("file", text=ESPRESSO, matching_claim_count=0) == "refuse"
    assert apply_policy("file", text=IN_TOPIC, matching_claim_count=3) == "answer"


def test_sglang_dump_files_even_when_claims_exist(matching_recall, monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("belief dumps must skip the LLM")

    monkeypatch.setattr("second_brain.agent.supervisor._llm_choose", boom)
    decision = decide_act(SGLANG_DUMP, project_path="/vault/dlm", choose_fn=lambda *_a: "research")
    assert decision.job == "file"
    assert decision.matching_claim_count == 5


def test_espresso_policy_denies_greedy_research(no_recall):
    decision = decide_act(ESPRESSO, project_path="/vault/dlm", choose_fn=lambda *_a: "research")
    assert decision.job == "refuse"
    assert decision.refuse_message == REFUSE_MESSAGE
    assert "teach" in (decision.refuse_message or "").lower()
    assert "notes" in (decision.refuse_message or "").lower()


def test_in_topic_question_answers_from_notes(matching_recall):
    decision = decide_act(IN_TOPIC, project_path="/vault/dlm", choose_fn=lambda *_a: "answer")
    assert decision.job == "answer"
    assert decision.refuse_message is None


def test_find_papers_is_research(no_recall, monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("search intent must skip the LLM")

    monkeypatch.setattr("second_brain.agent.supervisor._llm_choose", boom)
    decision = decide_act(FIND_PAPERS, project_path="/vault/dlm", choose_fn=lambda *_a: "refuse")
    assert decision.job == "research"


def test_synthesis_over_notes_skips_llm(matching_recall, monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("synthesis+claims must skip the LLM")

    monkeypatch.setattr("second_brain.agent.supervisor._llm_choose", boom)
    q = (
        "Synthesise my stance on home espresso: grind vs dose, milk steaming, "
        "and what I'd buy next. Cite my notes."
    )
    decision = decide_act(q, project_path="/vault/Coffee")
    assert decision.job == "research"
    assert decision.reason == "synthesis over notes"


def test_plant_research_via_router(no_recall):
    decision = decide_act(
        "Research indoor plant care for low-light apartments — watering and soil",
        project_path="/vault/Plants",
    )
    assert decision.job == "research"


def test_ambiguous_falls_back_to_llm(matching_recall, monkeypatch):
    calls = {"n": 0}

    def fake_choose(message, snapshot):
        calls["n"] += 1
        return "answer", "ambiguous"

    monkeypatch.setattr("second_brain.agent.job_router.route_job", lambda *_a, **_k: (None, "", 0.0))
    monkeypatch.setattr("second_brain.agent.supervisor._llm_choose", fake_choose)
    decision = decide_act("What about the checkpoint?", project_path="/vault/dlm")
    assert calls["n"] == 1
    assert decision.job == "answer"


def test_forced_job_skips_llm(matching_recall, monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("forced job must skip the LLM")

    monkeypatch.setattr("second_brain.agent.supervisor._llm_choose", boom)
    decision = decide_act(
        "According to my notes, what matters?",
        project_path="/vault/dlm",
        forced_job="research",
    )
    assert decision.job == "research"
    assert decision.reason == "forced"


def test_attachments_file_via_supervisor(no_recall, monkeypatch):
    monkeypatch.setattr(
        "second_brain.agent.supervisor._llm_choose",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("attachments skip the LLM")),
    )
    decision = decide_act("What is this?", has_attachments=True, choose_fn=lambda *_a: "research")
    assert decision.job == "file"


def test_fallback_files_multi_sentence_dump():
    assert fallback_job(text=SGLANG_DUMP, matching_claim_count=0) == "file"
    assert fallback_job(text=ESPRESSO, matching_claim_count=0) == "refuse"
    assert fallback_job(text=IN_TOPIC, matching_claim_count=3) == "answer"


def test_act_http_attachments_and_espresso(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("sidecar.server.start_scheduler", lambda **_kwargs: None)
    monkeypatch.setattr(
        "second_brain.agent.supervisor.recall_snapshot",
        lambda *_a, **_k: _snap(0),
    )
    monkeypatch.setattr(
        "second_brain.agent.supervisor._llm_choose",
        lambda *_a, **_k: ("research", "greedy"),
    )
    from fastapi.testclient import TestClient
    from sidecar.server import app

    with TestClient(app) as client:
        attached = client.post(
            "/api/act",
            json={"message": "What is this?", "has_attachments": True},
        )
        assert attached.status_code == 200
        assert attached.json()["job"] == "file"

        espresso = client.post("/api/act", json={"message": ESPRESSO, "project_path": "/vault/dlm"})
        assert espresso.status_code == 200
        body = espresso.json()
        assert body["job"] == "refuse"
        assert body["refuse_message"]
        assert "don't have notes" in body["refuse_message"].lower() or "teach" in body["refuse_message"].lower()
