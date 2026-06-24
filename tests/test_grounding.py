import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from langchain_core.documents import Document

from second_brain.agents.grounding import check_grounding, extract_citation_indices


def _web_doc(title: str = "Tutorial") -> Document:
    return Document(
        page_content="Web tutorial content",
        metadata={"source": title, "source_path": "https://example.com", "source_type": "web"},
    )


def test_extract_citation_indices():
    assert extract_citation_indices("See [1] and [3] for details.") == {1, 3}


def test_grounding_invalid_citation():
    docs = [_web_doc()]
    ok, issues = check_grounding("According to [2], servlets are fast.", docs)
    assert not ok
    assert any("Invalid citation" in issue for issue in issues)


def test_grounding_academic_claim_without_arxiv():
    docs = [_web_doc("NTU Tutorial")]
    analysis = "The academic paper by Chua et al. [1] explains servlets."
    ok, issues = check_grounding(analysis, docs)
    assert not ok
    assert any("academic" in issue.lower() for issue in issues)


def test_grounding_valid_web_citation():
    docs = [_web_doc("Servlets Tutorial")]
    analysis = "The web tutorial [1] explains how to extend HttpServlet."
    ok, issues = check_grounding(analysis, docs)
    assert ok
    assert issues == []