#!/usr/bin/env python3
"""Run the vault-grounded benchmark evaluation suite."""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from second_brain.memory.chroma_store import collection_count  # noqa: E402
from evaluation.runner import BENCHMARKS_PATH, RESULTS_DIR, load_benchmarks, run_evaluation  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Run Second Brain benchmark evaluation")
    parser.add_argument(
        "--category",
        "-c",
        help="Filter by category (personal_vault, hybrid, research, edge_gaps)",
    )
    parser.add_argument("--mode", "-m", choices=["query", "research"], help="Filter by mode")
    parser.add_argument("--limit", "-l", type=int, help="Limit number of queries")
    parser.add_argument("--ids", help="Comma-separated query IDs (e.g. PV01,EG01)")
    parser.add_argument("--resume", type=Path, help="Resume from a previous results JSON file")
    parser.add_argument("--output", "-o", type=Path, help="Output JSON path")
    parser.add_argument("--dry-run", action="store_true", help="List queries without running")
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="Seconds to sleep between queries (rate-limit pacing for Groq)",
    )
    parser.add_argument(
        "--ablation-off",
        action="store_true",
        help="Force ENABLE_SELF_CRITIQUE=false for this process (self-critique ablation)",
    )
    args = parser.parse_args()

    if args.ablation_off:
        import os

        os.environ["ENABLE_SELF_CRITIQUE"] = "false"
        # Re-bind config module used by verifier / runner metadata
        import second_brain.config as cfg
        import second_brain.agents.verifier as verifier_mod
        import evaluation.runner as runner_mod

        cfg.ENABLE_SELF_CRITIQUE = False
        verifier_mod.ENABLE_SELF_CRITIQUE = False
        runner_mod.ENABLE_SELF_CRITIQUE = False
        print("Ablation mode: ENABLE_SELF_CRITIQUE=false\n")

    if collection_count() == 0:
        print("Error: Knowledge base is empty. Ingest documents first.", file=sys.stderr)
        sys.exit(1)

    benchmarks = load_benchmarks()
    if not benchmarks:
        print("Error: evaluation/benchmarks.json has no queries.", file=sys.stderr)
        sys.exit(1)

    if args.category:
        benchmarks = [b for b in benchmarks if b["category"] == args.category]
    if args.mode:
        benchmarks = [b for b in benchmarks if b["mode"] == args.mode]
    if args.ids:
        ids = {i.strip() for i in args.ids.split(",")}
        benchmarks = [b for b in benchmarks if b["id"] in ids]
    if args.limit:
        benchmarks = benchmarks[: args.limit]

    print(f"Benchmark evaluation: {len(benchmarks)} queries")
    print(f"Knowledge base: {collection_count()} chunks\n")

    if args.dry_run:
        for b in benchmarks:
            print(f"  {b['id']} [{b['category']}/{b['mode']}] {b['query']}")
        return

    resume_data = None
    if args.resume:
        resume_data = json.loads(args.resume.read_text())
        print(f"Resuming from {args.resume} ({resume_data.get('completed_count', 0)} completed)\n")

    output = args.output or RESULTS_DIR / f"run_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report = run_evaluation(
        benchmarks,
        output,
        resume_from=resume_data,
        sleep_seconds=args.sleep,
    )

    summary = report["summary"]
    print(f"\n{'=' * 50}")
    print(f"Evaluation complete → {output}")
    print(f"  Completed: {summary['completed']}/{summary['total']}")
    print(f"  Failed:    {summary['failed']}")
    print(f"  Avg latency: {summary['avg_latency_seconds']}s")
    print(f"  Citation rate: {summary['citation_rate']:.0%}")
    if summary.get("gold_hit_rate") is not None:
        print(f"  Gold-hit rate: {summary['gold_hit_rate']:.0%}")
    if summary.get("honest_gap_rate") is not None:
        print(f"  Honest-gap rate: {summary['honest_gap_rate']:.0%}")
    print(f"  Invented-fact rate: {summary.get('invented_rate', 0):.0%}")
    if summary.get("by_category"):
        print("  By category:")
        for cat, stats in summary["by_category"].items():
            print(f"    {cat}: {stats['success']}/{stats['total']} (avg {stats['avg_latency']}s)")


if __name__ == "__main__":
    main()