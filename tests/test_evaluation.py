import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evaluation.metrics import analyze_query_result, summarize
from evaluation.runner import load_benchmarks


def test_benchmark_count():
    benchmarks = load_benchmarks()
    assert len(benchmarks) == 52
    ids = {b["id"] for b in benchmarks}
    assert len(ids) == 52


def test_benchmark_categories():
    benchmarks = load_benchmarks()
    categories = {b["category"] for b in benchmarks}
    assert "personal_java" in categories
    assert "hybrid" in categories
    assert "edge_gaps" in categories


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


def test_summarize():
    m1 = analyze_query_result("A", "personal_java", "query", 2.0, True, answer="Answer [1]")
    m2 = analyze_query_result("B", "hybrid", "research", 60.0, False, error="timeout")
    summary = summarize([m1, m2])
    assert summary.total == 2
    assert summary.completed == 1
    assert summary.failed == 1


def test_benchmarks_json_valid():
    path = Path(__file__).parents[1] / "evaluation" / "benchmarks.json"
    data = json.loads(path.read_text())
    assert data["version"] == "1.0"
    assert len(data["queries"]) == 52