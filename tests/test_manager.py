"""Manager: dispatch-first, at most two asks, dumps skip the interview."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from second_brain.agent.manager import (  # noqa: E402
    MAX_CLARIFY,
    is_vague,
    suggest_topic,
    take_turn,
)
from second_brain.agent.supervisor import RecallSnapshot  # noqa: E402

FIND_PAPERS = "Find papers on JustGRPO"
VAGUE = "help with my FYP"
DUMP = (
    "I now think schema-constrained decoding for diffusion LMs shipped in SGLang last week. "
    "I still don’t trust tok/s without GPU and batch size named. "
    "Parallel decode that breaks JSON is still a fail for me."
)
ESPRESSO = "What is the best espresso machine for a small kitchen?"


def _snap(count: int = 0) -> RecallSnapshot:
    return RecallSnapshot(
        topic="dlm",
        matching_claim_count=count,
        claim_previews=["Constrained decoding for diffusion LMs."] if count else [],
    )


@pytest.fixture
def no_recall(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "second_brain.agent.supervisor.recall_snapshot",
        lambda *_a, **_k: _snap(0),
    )


@pytest.fixture
def no_llm(monkeypatch: pytest.MonkeyPatch):
    def boom(*_a, **_k):
        raise AssertionError("clear Manager paths must not call the supervisor LLM")

    monkeypatch.setattr("second_brain.agent.supervisor._llm_choose", boom)


def test_find_papers_is_not_vague():
    assert is_vague(FIND_PAPERS) is False
    assert is_vague(VAGUE) is True


def test_suggest_topic_from_clear_lookup():
    assert suggest_topic(FIND_PAPERS) == "JustGRPO"
    assert suggest_topic("help with my FYP") == "FYP"
    assert suggest_topic("") == "Research"


def test_clear_lookup_dispatches_with_zero_asks(no_recall, no_llm):
    turn = take_turn(FIND_PAPERS, project_path="/vault/dlm", clarify_count=0)
    assert turn.kind == "dispatch"
    assert turn.job == "research"
    assert turn.instruction == FIND_PAPERS
    assert turn.create_topic == ""


def test_dispatch_without_project_proposes_topic(no_recall, no_llm):
    turn = take_turn(FIND_PAPERS, project_path=None, clarify_count=0)
    assert turn.kind == "dispatch"
    assert turn.job == "research"
    assert turn.create_topic == "JustGRPO"
    assert "JustGRPO" in turn.text


def test_vague_goal_asks_once(no_recall, no_llm):
    turn = take_turn(VAGUE, project_path="/vault/dlm", clarify_count=0)
    assert turn.kind == "ask"
    assert turn.focus == "clarify"
    assert turn.job is None


def test_second_vague_ask_then_force_dispatch(no_recall, no_llm):
    first = take_turn(VAGUE, clarify_count=0)
    assert first.kind == "ask"
    second = take_turn("not sure yet", clarify_count=1)
    assert second.kind == "ask"
    assert second.focus == "confirm"
    forced = take_turn("not sure yet", clarify_count=MAX_CLARIFY)
    assert forced.kind == "dispatch"


def test_skip_phrase_dispatches(no_recall, no_llm):
    turn = take_turn(
        "just look it up",
        clarify_count=1,
        history=[{"role": "user", "content": VAGUE}],
    )
    assert turn.kind == "dispatch"
    assert turn.instruction == VAGUE


NOTES_Q = (
    "According to my notes, what do I care about in diffusion language models "
    "besides raw generation speed?"
)
PRIOR_LOOKUP = [
    {"role": "user", "content": FIND_PAPERS},
    {"role": "assistant", "content": "I'll look this up."},
]


def test_followup_notes_question_is_not_poisoned_by_prior_lookup(no_recall, no_llm):
    turn = take_turn(
        NOTES_Q,
        project_path="/vault/dlm",
        clarify_count=0,
        history=PRIOR_LOOKUP,
    )
    assert turn.kind == "dispatch"
    assert turn.job == "refuse"
    assert turn.instruction == NOTES_Q
    assert FIND_PAPERS not in (turn.instruction or "")


def test_followup_notes_question_answers_when_claims_match(no_llm, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "second_brain.agent.supervisor.recall_snapshot",
        lambda *_a, **_k: _snap(5),
    )
    turn = take_turn(
        NOTES_Q,
        project_path="/vault/dlm",
        clarify_count=1,
        history=PRIOR_LOOKUP,
    )
    assert turn.kind == "dispatch"
    assert turn.job == "answer"
    assert turn.instruction == NOTES_Q
    assert turn.retrieval_scope == "local"


SYNTHESIS = (
    "Synthesise my stance on home espresso: grind vs dose, milk steaming, "
    "and what I'd buy next. Cite my notes."
)


def test_synthesis_cite_notes_is_research(no_llm, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "second_brain.agent.supervisor.recall_snapshot",
        lambda *_a, **_k: _snap(5),
    )
    turn = take_turn(SYNTHESIS, project_path="/vault/Coffee", clarify_count=0)
    assert turn.kind == "dispatch"
    assert turn.job == "research"
    assert turn.retrieval_scope == "hybrid"
    assert "look this up" in turn.text.lower()
    assert turn.also_topics == []


def test_forced_job_research_overrides_notes_ask(no_llm, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "second_brain.agent.supervisor.recall_snapshot",
        lambda *_a, **_k: _snap(5),
    )
    turn = take_turn(
        NOTES_Q,
        project_path="/vault/dlm",
        clarify_count=0,
        forced_job="research",
    )
    assert turn.kind == "dispatch"
    assert turn.job == "research"
    assert turn.reason == "forced"


def test_forced_job_watch_dispatches(no_recall, no_llm):
    turn = take_turn(
        "diffusion language models",
        project_path="/vault/dlm",
        clarify_count=0,
        forced_job="watch",
    )
    assert turn.kind == "dispatch"
    assert turn.job == "watch"
    assert turn.reason == "forced watch"


def test_forced_job_still_clamped_by_policy(no_recall, no_llm):
    """Force research off-topic with zero claims → refuse."""
    turn = take_turn(
        ESPRESSO,
        project_path="/vault/dlm",
        clarify_count=0,
        forced_job="research",
    )
    assert turn.kind == "dispatch"
    assert turn.job == "refuse"


def test_dump_skips_interview(no_recall, no_llm):
    turn = take_turn(DUMP, project_path="/vault/dlm", clarify_count=0)
    assert turn.kind == "dispatch"
    assert turn.job == "file"


def test_attachments_skip_interview(no_recall, no_llm):
    turn = take_turn("What is this?", has_attachments=True, clarify_count=0)
    assert turn.kind == "dispatch"
    assert turn.job == "file"


def test_watch_intent_dispatches_watch(no_recall, no_llm):
    turn = take_turn("Watch for new papers on JustGRPO", clarify_count=0)
    assert turn.kind == "dispatch"
    assert turn.job == "watch"


def test_off_topic_still_refused(no_recall, no_llm):
    turn = take_turn(ESPRESSO, project_path="/vault/dlm", clarify_count=0)
    assert turn.kind == "dispatch"
    assert turn.job == "refuse"
    assert turn.refuse_message


def test_manager_http_clear_query(no_recall, no_llm, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("sidecar.server.start_scheduler", lambda **_kwargs: None)
    from fastapi.testclient import TestClient
    from sidecar.server import app

    with TestClient(app) as client:
        res = client.post(
            "/api/manager/turn",
            json={"message": FIND_PAPERS, "project_path": "/vault/dlm", "clarify_count": 0},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["kind"] == "dispatch"
        assert body["job"] == "research"


TOPICS = [
    {"name": "FYP", "path": "/vault/FYP"},
    {"name": "JustGRPO", "path": "/vault/JustGRPO"},
    {"name": "DLM", "path": "/vault/DLM"},
    {"name": "thesis", "path": "/vault/thesis"},
]


def test_this_is_part_of_fyp_dispatches_retarget(no_recall, no_llm):
    turn = take_turn(
        "this is part of FYP",
        project_path="/vault/JustGRPO",
        topics=TOPICS,
    )
    assert turn.kind == "dispatch"
    assert turn.job == "retarget"
    assert turn.retarget_topic == "FYP"
    assert is_vague("this is part of FYP") is False or turn.job == "retarget"


def test_combine_topics_dispatches_merge(no_recall, no_llm):
    turn = take_turn("combine JustGRPO into DLM", project_path="/vault/JustGRPO", topics=TOPICS)
    assert turn.kind == "dispatch"
    assert turn.job == "merge"
    assert turn.merge_source == "JustGRPO"
    assert turn.merge_dest == "DLM"


def test_subject_change_dispatches_split(no_recall, no_llm):
    turn = take_turn(
        "forget JustGRPO, let's do thesis structure",
        project_path="/vault/JustGRPO",
        topics=TOPICS,
    )
    assert turn.kind == "dispatch"
    assert turn.job == "split"
    assert turn.new_topic
    assert turn.create_topic == turn.new_topic


def test_also_check_notes_keeps_question_and_union(no_recall, no_llm):
    turn = take_turn(
        "Find papers on GRPO, also check my thesis notes",
        project_path="/vault/JustGRPO",
        topics=TOPICS,
    )
    assert turn.kind == "dispatch"
    assert turn.job == "research"
    assert "thesis" in turn.also_topics
    assert "/vault/thesis" in turn.also_project_paths
    assert "also check" not in (turn.instruction or "").lower()
    assert "GRPO" in (turn.instruction or "")


def test_empty_channel_still_dispatches_research(no_recall, no_llm):
    turn = take_turn(
        FIND_PAPERS,
        project_path="/vault/dlm",
        clarify_count=0,
        workspace_empty=True,
    )
    assert turn.kind == "dispatch"
    assert turn.job == "research"


def test_vague_asks_even_when_channel_empty(no_recall, no_llm):
    turn = take_turn(
        VAGUE,
        project_path="/vault/dlm",
        clarify_count=0,
        workspace_empty=True,
    )
    assert turn.kind == "ask"
    assert turn.reason == "underspecified"


def test_dump_files_without_staffing(no_recall, no_llm):
    turn = take_turn(
        DUMP,
        project_path="/vault/dlm",
        clarify_count=0,
        workspace_empty=True,
    )
    assert turn.job == "file"


def test_ready_channel_runs_research_in_thread(no_recall, no_llm):
    turn = take_turn(
        FIND_PAPERS,
        project_path="/vault/dlm",
        clarify_count=0,
        workspace_empty=False,
    )
    assert turn.kind == "dispatch"
    assert turn.job == "research"


def test_agent_param_ignored(no_recall, no_llm):
    turn = take_turn(
        FIND_PAPERS,
        project_path="/vault/dlm",
        agent="research",
    )
    assert turn.kind == "dispatch"
    assert turn.job == "research"


def test_non_empty_vague_dispatches_or_asks(no_recall, no_llm):
    turn = take_turn(
        VAGUE,
        project_path="/vault/dlm",
        clarify_count=0,
        workspace_empty=False,
    )
    assert turn.kind in {"ask", "dispatch"}
    assert turn.reason != "onboard"
