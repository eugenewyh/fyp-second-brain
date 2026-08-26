"""Plan / execute graph split + run registry."""

import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.messages import AIMessage

from second_brain.graph import (
    build_execute_graph,
    build_plan_graph,
    route_after_verifier,
    seed_execute_state,
)
from sidecar.runs import RunRegistry


def test_plan_and_execute_graphs_compile():
    assert build_plan_graph() is not None
    assert build_execute_graph() is not None


def test_seed_execute_state():
    s = seed_execute_state(
        composed_query="q",
        plan="1. Do research",
        retrieval_queries=["[personal] foo", "  ", "[web] bar"],
        retrieval_scope="local",
    )
    assert s["query"] == "q"
    assert s["plan"] == "1. Do research"
    assert s["retrieval_queries"] == ["[personal] foo", "[web] bar"]
    assert s["critique_history"] == []
    assert s["retrieval_scope"] == "local"


def test_run_registry_pending_does_not_block():
    reg = RunRegistry()
    a = reg.create(query="q", composed_query="q", plan="p", retrieval_queries=["x"])
    b = reg.create(query="q2", composed_query="q2", plan="p2", retrieval_queries=["y"])
    assert a.run_id != b.run_id
    assert reg.active_run_id() is None
    rec, err = reg.begin_execute(a.run_id)
    assert err is None
    assert a.run_id in reg.active_run_ids()
    rec2, err2 = reg.begin_execute(b.run_id)
    assert err2 is None
    assert {a.run_id, b.run_id} <= reg.active_run_ids()
    reg.finish(a.run_id)
    assert a.run_id not in reg.active_run_ids()
    assert b.run_id in reg.active_run_ids()
    reg.finish(b.run_id)
    assert reg.active_run_ids() == set()


def test_run_registry_concurrent_auto_cap():
    from sidecar.runs import MAX_CONCURRENT_RUNS

    reg = RunRegistry()
    tokens = []
    for i in range(MAX_CONCURRENT_RUNS):
        token, busy = reg.begin_auto(f"/tmp/topic-{i}")
        assert busy is None
        assert token
        tokens.append(token)
    extra, busy = reg.begin_auto("/tmp/overflow")
    assert extra is None
    assert busy is not None
    # Finishing A does not finish B
    reg.end_auto(tokens[0])
    assert tokens[0] not in reg.active_run_ids()
    assert tokens[1] in reg.active_run_ids()
    token2, busy2 = reg.begin_auto("/tmp/topic-new")
    assert busy2 is None
    assert token2
    assert reg.topic_has_run("/tmp/topic-1") == tokens[1]
    assert reg.topic_has_run("/tmp/missing") is None

    two = RunRegistry()
    a, busy_a = two.begin_auto("/a")
    b, busy_b = two.begin_auto("/b")
    assert busy_a is None and busy_b is None
    assert a and b and a != b


def test_run_registry_regenerate_expires_old():
    reg = RunRegistry()
    a = reg.create(query="q", composed_query="q", plan="p", retrieval_queries=["x"])
    b = reg.create(
        query="q",
        composed_query="q",
        plan="p2",
        retrieval_queries=["y"],
        replace_run_id=a.run_id,
    )
    assert reg.get(a.run_id) is None
    assert reg.get(b.run_id) is not None


def test_plan_graph_mocked_llm():
    def fake_llm(messages, **kwargs):
        return AIMessage(
            content=(
                "RESEARCH_PLAN:\n1. Step one\n\n"
                "SEARCH_QUERIES:\n- [personal] servlet architecture"
            )
        )

    with patch("second_brain.agents.planner.invoke_llm", side_effect=fake_llm):
        g = build_plan_graph()
        out = g.invoke(
            {
                "query": "What are servlets?",
                "messages": [],
                "plan": "",
                "retrieval_queries": [],
                "retrieval_stats": {},
                "retrieval_log": [],
                "retrieved_docs": [],
                "analysis": "",
                "critique": "",
                "critique_approved": False,
                "revision_count": 0,
                "report": "",
                "critique_structured": None,
                "critique_history": [],
                "analysis_history": [],
            }
        )
    assert "Step" in out["plan"] or "servlet" in out["plan"].lower() or out["plan"]
    assert any("personal" in q.lower() for q in out["retrieval_queries"])


def test_route_still_works():
    assert route_after_verifier({"critique_approved": True, "revision_count": 0}) == "synthesizer"
