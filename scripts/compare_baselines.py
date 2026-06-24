#!/usr/bin/env python3
"""Merge evaluation results with baseline scores and produce comparison summary."""

import argparse
import csv
import json
import sys
from pathlib import Path
from statistics import mean

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_baselines(path: Path) -> list[dict]:
    with path.open() as f:
        return list(csv.DictReader(f))


def main():
    parser = argparse.ArgumentParser(description="Compare Second Brain vs baseline scores")
    parser.add_argument("results", type=Path, help="Evaluation results JSON")
    parser.add_argument("baselines", type=Path, help="Scored baseline CSV (from baseline_template.csv)")
    parser.add_argument("--output", "-o", type=Path, help="Output comparison JSON")
    args = parser.parse_args()

    results = json.loads(args.results.read_text())
    baselines = load_baselines(args.baselines)

    system_by_id = {}
    for entry in results.get("results", []):
        text = entry.get("result", {}).get("report") or entry.get("result", {}).get("answer", "")
        system_by_id[entry["id"]] = text

    comparison = {"models": {}, "per_query": []}

    for row in baselines:
        qid = row["query_id"]
        model = row["baseline_model"]
        if not model or not row.get("score_overall"):
            continue

        scores = {
            "accuracy": float(row.get("score_accuracy") or 0),
            "citations": float(row.get("score_citations") or 0),
            "completeness": float(row.get("score_completeness") or 0),
            "gaps": float(row.get("score_gaps") or 0),
            "overall": float(row.get("score_overall") or 0),
        }
        comparison["per_query"].append({"query_id": qid, "model": model, "scores": scores})

        bucket = comparison["models"].setdefault(model, {"scores": []})
        bucket["scores"].append(scores["overall"])

    for model, data in comparison["models"].items():
        data["avg_overall"] = round(mean(data["scores"]), 2) if data["scores"] else 0
        data["count"] = len(data["scores"])

    comparison["system"] = {
        "citation_rate": results.get("summary", {}).get("citation_rate", 0),
        "success_rate": results["summary"]["completed"] / max(results["summary"]["total"], 1),
        "avg_latency": results.get("summary", {}).get("avg_latency_seconds", 0),
    }

    output = args.output or args.results.parent / f"{args.results.stem}_comparison.json"
    output.write_text(json.dumps(comparison, indent=2))
    print(f"Comparison written to {output}")
    for model, data in comparison["models"].items():
        print(f"  {model}: avg overall = {data['avg_overall']} (n={data['count']})")


if __name__ == "__main__":
    main()