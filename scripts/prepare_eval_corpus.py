#!/usr/bin/env python3
"""Reset Chroma and ingest the automated-eval Plants corpus."""

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS_PATH = PROJECT_ROOT / "evaluation" / "benchmarks.json"
DEFAULT_CORPUS = PROJECT_ROOT / "evaluation" / "demo" / "Plants"


def corpus_path() -> Path:
    if BENCHMARKS_PATH.is_file():
        data = json.loads(BENCHMARKS_PATH.read_text())
        raw = (data.get("corpus_ingest_path") or "").strip()
        if raw:
            p = Path(raw)
            if not p.is_absolute():
                p = PROJECT_ROOT / p
            if p.is_dir():
                return p
    return DEFAULT_CORPUS


def main() -> None:
    corpus = corpus_path()
    if not corpus.is_dir():
        print(f"Error: eval corpus not found at {corpus}", file=sys.stderr)
        sys.exit(1)

    print(f"Resetting vector store and ingesting eval corpus:\n  {corpus}")
    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "ingest.py"), "--reset", "-i", str(corpus)],
        cwd=PROJECT_ROOT,
        check=True,
    )


if __name__ == "__main__":
    main()
