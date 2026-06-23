import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from second_brain.ingestion.loaders import load_file
from second_brain.ingestion.pipeline import split_documents


def test_load_text_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Hello, Second Brain.")
        path = Path(f.name)

    filename = path.name
    docs = load_file(path)
    path.unlink()

    assert len(docs) == 1
    assert "Second Brain" in docs[0].page_content
    assert docs[0].metadata["source"] == filename


def test_split_documents_adds_metadata():
    from langchain_core.documents import Document

    docs = [Document(page_content="A" * 2000, metadata={"source": "test.txt", "source_path": "/tmp/test.txt"})]
    chunks = split_documents(docs)

    assert len(chunks) >= 2
    assert "chunk_index" in chunks[0].metadata
    assert "ingested_at" in chunks[0].metadata