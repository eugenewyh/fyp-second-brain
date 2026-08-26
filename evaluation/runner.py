import json
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from second_brain.config import ENABLE_SELF_CRITIQUE  # noqa: E402
from second_brain.graph import run_research  # noqa: E402
from second_brain.rag.chain import ask  # noqa: E402

from evaluation.metrics import QueryMetrics, analyze_query_result, summarize  # noqa: E402

BENCHMARKS_PATH = Path(__file__).parent / "benchmarks.json"
RESULTS_DIR = Path(__file__).parent / "results"


def load_benchmarks() -> list[dict]:
    data = json.loads(BENCHMARKS_PATH.read_text())
    return data["queries"]


def run_single(benchmark: dict) -> tuple[dict, QueryMetrics]:
    query_id = benchmark["id"]
    category = benchmark["category"]
    mode = benchmark["mode"]
    query = benchmark["query"]

    start = time.perf_counter()
    try:
        if mode == "query":
            response = ask(query)
            latency = time.perf_counter() - start
            result = {
                "answer": response.answer,
                "sources": [asdict(s) for s in response.sources],
            }
            metrics = analyze_query_result(
                query_id, category, mode, latency, True,
                answer=response.answer,
                sources=result["sources"],
                expect=benchmark.get("expect"),
            )
        else:
            state = run_research(query)
            latency = time.perf_counter() - start
            result = {
                "plan": state.get("plan", ""),
                "retrieval_queries": state.get("retrieval_queries", []),
                "retrieval_stats": state.get("retrieval_stats", {}),
                "retrieval_log": state.get("retrieval_log", []),
                "analysis": state.get("analysis", ""),
                "revision_count": state.get("revision_count", 0),
                "report": state.get("report", ""),
            }
            metrics = analyze_query_result(
                query_id, category, mode, latency, True,
                answer=result["report"],
                retrieval_stats=result["retrieval_stats"],
                revision_count=result["revision_count"],
                expect=benchmark.get("expect"),
            )
        return result, metrics
    except Exception as e:
        latency = time.perf_counter() - start
        metrics = analyze_query_result(
            query_id, category, mode, latency, False, error=str(e),
        )
        return {"error": str(e)}, metrics


def run_evaluation(
    benchmarks: list[dict],
    output_path: Path,
    resume_from: dict | None = None,
    *,
    sleep_seconds: float = 0.0,
) -> dict:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    completed_ids: set[str] = set()
    results: list[dict] = []
    metrics_list: list[QueryMetrics] = []

    if resume_from:
        results = resume_from.get("results", [])
        metrics_list = [
            QueryMetrics(**m) for m in resume_from.get("metrics", [])
        ]
        completed_ids = {r["id"] for r in results}

    ran_any = False
    for benchmark in benchmarks:
        if benchmark["id"] in completed_ids:
            continue

        if sleep_seconds > 0 and ran_any:
            time.sleep(sleep_seconds)

        print(f"  [{benchmark['id']}] {benchmark['mode']}: {benchmark['query'][:60]}…")
        result, metrics = run_single(benchmark)
        ran_any = True
        entry = {
            "id": benchmark["id"],
            "category": benchmark["category"],
            "mode": benchmark["mode"],
            "query": benchmark["query"],
            "metrics": asdict(metrics),
            "result": result,
        }
        results.append(entry)
        metrics_list.append(metrics)

        partial = _build_report(benchmarks, results, metrics_list)
        output_path.write_text(json.dumps(partial, indent=2))

    return _build_report(benchmarks, results, metrics_list)


def _build_report(benchmarks: list[dict], results: list[dict], metrics_list: list[QueryMetrics]) -> dict:
    summary = summarize(metrics_list)
    return {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_count": len(benchmarks),
        "completed_count": len(results),
        "enable_self_critique": ENABLE_SELF_CRITIQUE,
        "summary": asdict(summary),
        "metrics": [asdict(m) for m in metrics_list],
        "results": results,
    }