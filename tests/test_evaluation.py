import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evaluation.metrics import analyze_query_result, score_expect, summarize
from evaluation.runner import load_benchmarks


def test_benchmark_count():
    benchmarks = load_benchmarks()
    assert len(benchmarks) == 20
    ids = {b["id"] for b in benchmarks}
    assert len(ids) == 20


def test_benchmark_categories():
    benchmarks = load_benchmarks()
    categories = {b["category"] for b in benchmarks}
    assert categories == {"personal_vault", "hybrid", "research", "edge_gaps"}
    modes = {b["mode"] for b in benchmarks}
    assert modes == {"query", "research"}
    for b in benchmarks:
        assert "expect" in b


def test_analyze_research_metrics():
    metrics = analyze_query_result(
        "HY01", "hybrid", "research", 45.2, True,
        answer="## Executive Summary\nText [1]\n## Identified Gaps\nNo arxiv papers found.",
        retrieval_stats={"personal": 3, "web": 3, "arxiv": 0},
        revision_count=1,
    )
    assert metrics.has_citations
    assert metrics.has_gaps_section
    assert metrics.personal_sources == 3

    plain = analyze_query_result(
        "HY02", "hybrid", "research", 10.0, True,
        answer="## In short\nText [1]\n## What's missing\nNo arxiv papers found.",
        retrieval_stats={"personal": 1, "web": 1, "arxiv": 0},
    )
    assert plain.has_gaps_section


def test_summarize():
    m1 = analyze_query_result("A", "personal_vault", "query", 2.0, True, answer="Answer [1]")
    m2 = analyze_query_result("B", "hybrid", "research", 60.0, False, error="timeout")
    summary = summarize([m1, m2])
    assert summary.total == 2
    assert summary.completed == 1
    assert summary.failed == 1


def test_benchmarks_json_valid():
    path = Path(__file__).parents[1] / "evaluation" / "benchmarks.json"
    data = json.loads(path.read_text())
    assert data["version"] == "2.0"
    assert len(data["queries"]) == 20


def test_score_expect_gap_honesty():
    _, honest, invented = score_expect(
        "The provided notes do not contain any information about Mongolia's capital.",
        {"kind": "gap", "none_of": ["ulaanbaatar"]},
    )
    assert honest is True
    assert invented is False

    _, honest2, invented2 = score_expect(
        "Ulaanbaatar is the capital of Mongolia.",
        {"kind": "gap", "none_of": ["ulaanbaatar"]},
    )
    assert invented2 is True
    assert honest2 is False


def test_score_expect_grounded():
    gold, _, _ = score_expect(
        "DiffusionGemma refines blocks of 256 tokens in parallel.",
        {"kind": "grounded", "any_of": ["256", "parallel"]},
    )
    assert gold is True
