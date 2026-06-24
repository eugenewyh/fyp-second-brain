import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from langchain_core.documents import Document

from second_brain.rag.citations import format_bibliography, strip_sources_section


def test_format_bibliography_compact():
    docs = [
        Document(page_content="slide text", metadata={"source": "Lec03.pdf", "source_type": "personal", "page": 11}),
        Document(
            page_content="web text",
            metadata={"source": "Tutorial", "source_path": "https://example.com/servlets", "source_type": "web"},
        ),
    ]
    bib = format_bibliography(docs)
    assert "[1] Personal — Lec03.pdf, p.12" in bib
    assert "[2] Web — Tutorial (https://example.com/servlets)" in bib
    assert "slide text" not in bib


def test_strip_sources_section():
    report = "## Executive Summary\nSummary here.\n\n## Sources\n\n[1] Long dump..."
    stripped = strip_sources_section(report)
    assert "## Sources" not in stripped
    assert "Summary here" in stripped