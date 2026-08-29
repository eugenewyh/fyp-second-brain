"""Unified route_turn pipeline — tier, meta, forced, local model paths."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from second_brain.agent.router.meta import is_meta_intent  # noqa: E402
from second_brain.agent.router.recall import RecallSnapshot  # noqa: E402
from second_brain.agent.router.turn import route_turn  # noqa: E402

FIND_PAPERS = "Find papers on JustGRPO"
VAGUE = "help with my FYP"
NOTES_Q = (
    "According to my notes, what do I care about in diffusion language models "
    "besides raw generation speed?"
)
SYNTHESIS = (
    "Synthesise my stance on home espresso: grind vs dose, milk steaming, "
    "and what I'd buy next. Cite my notes."
)


def _snap(count: int = 0) -> RecallSnapshot:
    return RecallSnapshot(
        topic="dlm",
        matching_claim_count=count,
        claim_previews=["Constrained decoding for diffusion LMs."] if count else [],
    )


@pytest.fixture
def no_recall(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "second_brain.agent.router.turn.recall.recall_snapshot",
        lambda *_a, **_k: _snap(0),
    )


@pytest.fixture
def no_llm(monkeypatch: pytest.MonkeyPatch):
    def boom(*_a, **_k):
        raise AssertionError("clear paths must not call the LLM router")

    monkeypatch.setattr("second_brain.agent.router.turn.llm_router.llm_choose", boom)


def test_meta_hi_what_can_you_do(no_recall, no_llm):
    turn = route_turn("hi what can you do?", project_path="/vault/dlm", clarify_count=0)
    assert turn.kind == "meta"
    assert turn.route_tier == "meta"
    assert "Teach" in turn.text
    assert "Ask" in turn.text
    assert "Research" in turn.text


def test_meta_greeting(no_recall, no_llm):
    assert is_meta_intent("hello")
    turn = route_turn("hello", project_path="/vault/Coffee")
    assert turn.kind == "meta"
    assert turn.job is None


def test_vague_fyp_still_clarifies(no_recall, no_llm):
    turn = route_turn(VAGUE, project_path="/vault/dlm", clarify_count=0)
    assert turn.kind == "clarify"
    assert turn.focus == "clarify"


def test_forced_research_tier(no_recall, no_llm):
    turn = route_turn(FIND_PAPERS, project_path="/vault/dlm", forced_job="research")
    assert turn.kind == "dispatch"
    assert turn.job == "research"
    assert turn.route_tier == "forced"


def test_research_phrasing_rule_tier(no_recall, no_llm):
    turn = route_turn(
        "Research indoor plant care for low-light apartments",
        project_path="/vault/Plants",
    )
    assert turn.kind == "dispatch"
    assert turn.job == "research"
    assert turn.route_tier in {"rule", "local", "forced"}


def test_notes_with_claims_answer(no_llm, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "second_brain.agent.router.turn.recall.recall_snapshot",
        lambda *_a, **_k: _snap(5),
    )
    turn = route_turn(NOTES_Q, project_path="/vault/dlm")
    assert turn.kind == "dispatch"
    assert turn.job == "answer"
    assert turn.route_tier == "rule"


def test_synthesis_research_rule_tier(no_llm, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "second_brain.agent.router.turn.recall.recall_snapshot",
        lambda *_a, **_k: _snap(5),
    )
    turn = route_turn(SYNTHESIS, project_path="/vault/Coffee")
    assert turn.kind == "dispatch"
    assert turn.job == "research"
    assert turn.route_tier == "rule"
