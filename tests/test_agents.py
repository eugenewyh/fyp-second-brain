import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from second_brain.agents.utils import parse_planner_output, parse_verifier_output
from second_brain.graph import build_graph, route_after_verifier


def test_parse_planner_output():
    text = """RESEARCH_PLAN:
1. Review OOP concepts
2. Find inheritance examples

SEARCH_QUERIES:
- Java inheritance
- object oriented programming
- extends keyword"""
    plan, queries = parse_planner_output(text)
    assert "OOP" in plan
    assert len(queries) == 3
    assert "Java inheritance" in queries


def test_parse_planner_fallback():
    plan, queries = parse_planner_output("Just some unstructured text")
    assert plan == "Just some unstructured text"
    assert queries == []


def test_parse_verifier_approved():
    text = "VERDICT: APPROVED\nFEEDBACK: Analysis is well grounded."
    approved, feedback = parse_verifier_output(text)
    assert approved is True
    assert "well grounded" in feedback


def test_parse_verifier_revise():
    text = "VERDICT: REVISE\nFEEDBACK: Claim [3] is not supported by sources."
    approved, feedback = parse_verifier_output(text)
    assert approved is False
    assert "Claim [3]" in feedback


def test_graph_compiles():
    graph = build_graph()
    assert graph is not None


def test_route_after_verifier_approved():
    assert route_after_verifier({"critique_approved": True, "revision_count": 0}) == "synthesizer"


def test_route_after_verifier_revise():
    assert route_after_verifier({"critique_approved": False, "revision_count": 0}) == "analyst"


def test_route_after_verifier_max_revisions():
    assert route_after_verifier({"critique_approved": False, "revision_count": 2}) == "synthesizer"