"""Harness allow-list: live env clamps scope, budget, and memory writes."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from second_brain.agent.harness import (
    HarnessError,
    live_max_passes,
    resolve_run_spec,
    run_harness,
    run_harness_stream,
)


def test_web_off_forces_local_scope(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENABLE_WEB_SEARCH", "false")
    monkeypatch.setenv("AUTO_MEMORY", "true")
    spec = resolve_run_spec(
        kind="goal",
        instruction="Look up papers on RAG",
        retrieval_scope="hybrid",
    )
    assert spec.retrieval_scope == "local"
    assert spec.tools.web is False
    assert spec.persist_memory is True


def test_memory_off_disables_persist(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENABLE_WEB_SEARCH", "true")
    monkeypatch.setenv("AUTO_MEMORY", "false")
    spec = resolve_run_spec(kind="goal", instruction="Deepen the last report")
    assert spec.persist_memory is False
    assert spec.tools.write_memory is False
    # Explicit True still clamped by allow-list
    spec2 = resolve_run_spec(
        kind="watch",
        instruction="Morning brief",
        persist_memory=True,
    )
    assert spec2.persist_memory is False


def test_watch_budget_defaults_to_one(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("WATCH_MAX_PASSES", raising=False)
    monkeypatch.delenv("MAX_GOAL_PASSES", raising=False)
    monkeypatch.setenv("ENABLE_WEB_SEARCH", "true")
    watch = resolve_run_spec(kind="watch", instruction="Track citation metrics")
    goal = resolve_run_spec(kind="goal", instruction="Explain citation metrics")
    assert watch.max_passes == 1
    assert watch.claim_origin == "watch"
    assert goal.max_passes == 2
    assert goal.claim_origin == "research"
    assert live_max_passes("watch") == 1
    assert live_max_passes("goal") == 2


def test_request_override_wins_for_passes(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("WATCH_MAX_PASSES", "1")
    monkeypatch.setenv("MAX_GOAL_PASSES", "2")
    spec = resolve_run_spec(kind="watch", instruction="Track X", max_passes=3)
    assert spec.max_passes == 3
    capped = resolve_run_spec(kind="goal", instruction="Y", max_passes=9)
    assert capped.max_passes == 4


def test_run_harness_stream_forwards_clamped_kwargs(monkeypatch: pytest.MonkeyPatch):
    captured: dict = {}

    def fake_stream(goal, **kwargs):
        captured["goal"] = goal
        captured.update(kwargs)
        yield ("complete", {"query": goal, "ok": True})

    monkeypatch.setattr("second_brain.agent.goal_loop.run_goal_stream", fake_stream)
    monkeypatch.setenv("ENABLE_WEB_SEARCH", "false")
    monkeypatch.setenv("AUTO_MEMORY", "false")
    spec = resolve_run_spec(
        kind="goal",
        instruction="Find papers",
        retrieval_scope="web",
        session_id="s1",
        project_path="/tmp/t",
    )
    events = list(run_harness_stream(spec))
    assert captured["goal"] == "Find papers"
    assert captured["retrieval_scope"] == "local"
    assert captured["persist_memory"] is False
    assert captured["claim_origin"] == "research"
    assert captured["session_id"] == "s1"
    assert events[-1][0] == "complete"


def test_run_harness_raises_without_complete(monkeypatch: pytest.MonkeyPatch):
    def fake_stream(goal, **kwargs):
        yield ("error", {"message": "cancelled"})
        return
        yield  # pragma: no cover

    monkeypatch.setattr("second_brain.agent.goal_loop.run_goal_stream", fake_stream)
    spec = resolve_run_spec(kind="goal", instruction="x")
    with pytest.raises(HarnessError, match="cancelled"):
        run_harness(spec)
