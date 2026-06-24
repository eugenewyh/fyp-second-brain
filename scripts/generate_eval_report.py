#!/usr/bin/env python3
"""Generate a markdown evaluation report from benchmark results JSON."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description="Generate markdown report from evaluation results")
    parser.add_argument("results", type=Path, help="Path to evaluation results JSON")
    parser.add_argument("--output", "-o", type=Path, help="Output markdown path")
    args = parser.parse_args()

    data = json.loads(args.results.read_text())
    summary = data["summary"]
    metrics = data.get("metrics", [])

    lines = [
        "# Second Brain — Evaluation Report",
        "",
        f"**Run date:** {data.get('run_at', 'unknown')}",
        f"**Queries completed:** {summary['completed']}/{summary['total']}",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Success rate | {summary['completed']}/{summary['total']} ({summary['completed']/max(summary['total'],1):.0%}) |",
        f"| Failed | {summary['failed']} |",
        f"| Avg latency | {summary['avg_latency_seconds']}s |",
        f"| Citation rate | {summary['citation_rate']:.0%} |",
        f"| Gaps section rate | {summary['gaps_section_rate']:.0%} |",
        "",
        "## By Category",
        "",
        "| Category | Success | Avg Latency |",
        "|----------|---------|-------------|",
    ]

    for cat, stats in summary.get("by_category", {}).items():
        lines.append(f"| {cat} | {stats['success']}/{stats['total']} | {stats['avg_latency']}s |")

    lines.extend(["", "## Failed Queries", ""])
    failed = [m for m in metrics if not m.get("success")]
    if failed:
        for m in failed:
            lines.append(f"- **{m['query_id']}** ({m['category']}): {m.get('error', 'unknown error')}")
    else:
        lines.append("_None_")

    lines.extend(["", "## Latency Distribution", ""])
    latencies = sorted(m["latency_seconds"] for m in metrics if m.get("success"))
    if latencies:
        lines.append(f"- Min: {latencies[0]}s")
        lines.append(f"- Median: {latencies[len(latencies)//2]}s")
        lines.append(f"- Max: {latencies[-1]}s")
        lines.append(f"- Total: {sum(latencies):.0f}s ({sum(latencies)/60:.1f} min)")

    output = args.output or args.results.with_suffix(".md")
    output.write_text("\n".join(lines) + "\n")
    print(f"Report written to {output}")


if __name__ == "__main__":
    main()