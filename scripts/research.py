#!/usr/bin/env python3
"""Terminal interface for multi-agent autonomous research."""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from second_brain.agents.utils import docs_from_state
from second_brain.graph import run_research
from second_brain.memory.chroma_store import collection_count

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def print_report(result: dict, verbose: bool = False) -> None:
    if verbose:
        print("\n" + "=" * 60)
        print("RESEARCH PLAN")
        print("=" * 60)
        print(result.get("plan", "(none)"))

        queries = result.get("retrieval_queries", [])
        if queries:
            print("\n" + "-" * 60)
            print("SEARCH QUERIES")
            print("-" * 60)
            for q in queries:
                print(f"  • {q}")

        stats = result.get("retrieval_stats", {})
        if stats:
            print("\n" + "-" * 60)
            print("RETRIEVAL BREAKDOWN")
            print("-" * 60)
            for source_type, count in stats.items():
                if count > 0:
                    print(f"  {source_type}: {count}")

        docs = docs_from_state(result.get("retrieved_docs", []))
        print(f"\nRetrieved: {len(docs)} total result(s)")

        if result.get("analysis"):
            print("\n" + "-" * 60)
            print("ANALYSIS (pre-report)")
            print("-" * 60)
            print(result["analysis"][:500] + ("..." if len(result["analysis"]) > 500 else ""))

        revisions = result.get("revision_count", 0)
        if revisions:
            print(f"\nRevisions: {revisions}")

    print("\n" + "=" * 60)
    print("RESEARCH REPORT")
    print("=" * 60)
    print(result.get("report", "(no report generated)"))
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Run multi-agent research on your personal knowledge base",
    )
    parser.add_argument("query", help="Research question")
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show plan, queries, and analysis before final report",
    )
    args = parser.parse_args()

    if collection_count() == 0:
        print(
            "Knowledge base is empty. Ingest documents first:\n"
            "  python scripts/ingest.py --input data/documents",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Research question: {args.query}")
    print("Running multi-agent workflow (planner → retriever → analyst → verifier → synthesizer)...\n")

    result = run_research(args.query)
    print_report(result, verbose=args.verbose)


if __name__ == "__main__":
    main()