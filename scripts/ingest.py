#!/usr/bin/env python3
"""CLI to ingest documents into the Chroma knowledge base."""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from second_brain.ingestion.pipeline import ingest_directory
from second_brain.memory.chroma_store import collection_count, reset_vector_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main():
    parser = argparse.ArgumentParser(description="Ingest documents into Chroma")
    parser.add_argument(
        "--input", "-i",
        type=Path,
        required=True,
        help="Directory containing PDF/txt/md/docx files to ingest",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Wipe the Chroma index first (fixes corrupt HNSW / embedding switches)",
    )
    args = parser.parse_args()

    if not args.input.is_dir():
        print(f"Error: {args.input} is not a directory", file=sys.stderr)
        sys.exit(1)

    if args.reset:
        print("Resetting vector store…")
        reset_vector_store()

    print(f"Ingesting documents from: {args.input}")
    count = ingest_directory(args.input)
    total = collection_count()
    print(f"Done — ingested {count} chunk(s). Collection total: {total}")


if __name__ == "__main__":
    main()
