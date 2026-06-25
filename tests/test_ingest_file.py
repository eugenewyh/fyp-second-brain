import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from second_brain.ingestion.pipeline import ingest_file


def test_ingest_file_returns_zero_for_missing(tmp_path: Path):
    missing = tmp_path / "nope.md"
    assert ingest_file(missing) == 0