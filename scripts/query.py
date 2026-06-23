#!/usr/bin/env python3
"""Terminal interface for querying the personal knowledge base."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from second_brain.memory.chroma_store import collection_count
from second_brain.rag.chain import RAGResponse, ask


def print_response(response: RAGResponse) -> None:
    print("\n" + "=" * 60)
    print("ANSWER")
    print("=" * 60)
    print(response.answer)

    if response.sources:
        print("\n" + "-" * 60)
        print("SOURCES")
        print("-" * 60)
        for src in response.sources:
            page = f", page {src.page}" if src.page else ""
            print(f"  [{src.index}] {src.source}{page}")
            print(f"      {src.excerpt}...")
    print()


def interactive_loop(top_k: int) -> None:
    count = collection_count()
    print(f"Second Brain — Personal Knowledge Query")
    print(f"Knowledge base: {count} chunk(s) indexed")
    print("Type your question (or 'quit' to exit)\n")

    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not question:
            continue
        if question.lower() in {"quit", "exit", "q"}:
            print("Goodbye.")
            break

        print("\nSearching and generating answer...")
        response = ask(question, top_k=top_k)
        print_response(response)


def main():
    parser = argparse.ArgumentParser(description="Query your personal knowledge base")
    parser.add_argument("question", nargs="?", help="Question to ask (omit for interactive mode)")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Number of chunks to retrieve")
    args = parser.parse_args()

    if collection_count() == 0:
        print(
            "Knowledge base is empty. Ingest documents first:\n"
            "  python scripts/ingest.py --input data/documents",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.question:
        response = ask(args.question, top_k=args.top_k)
        print_response(response)
    else:
        interactive_loop(top_k=args.top_k)


if __name__ == "__main__":
    main()