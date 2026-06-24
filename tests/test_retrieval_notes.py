import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from second_brain.agents.retrieval_notes import build_retrieval_notes


def test_retrieval_note_when_arxiv_empty():
    note = build_retrieval_notes(
        {"personal": 3, "web": 3, "arxiv": 0},
        ["[arxiv] servlets → 0 result(s); retry '...' → 0 result(s)"],
    )
    assert "arXiv returned no relevant papers" in note


def test_no_note_when_arxiv_has_results():
    note = build_retrieval_notes(
        {"personal": 2, "arxiv": 1},
        ["[arxiv] machine learning → 1 result(s)"],
    )
    assert note == ""