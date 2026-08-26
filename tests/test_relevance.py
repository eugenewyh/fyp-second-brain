"""Off-topic lookups must not be filed into topic memory."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from second_brain.memory.relevance import SKIP_FILE_DETAIL, should_file_research

DLM_IDEA = """# Idea

Track diffusion language models: text models that refine groups of tokens in parallel
instead of generating one token at a time.

Focus on DiffusionGemma, Nemotron-Labs-Diffusion, constrained decoding, few-step sampling.
"""
ESPRESSO = "What is the best espresso machine for a small kitchen?"
IN_TOPIC = "What is DiffusionGemma and how does constrained decoding work?"


def _topic(tmp_path: Path) -> Path:
    project = tmp_path / "dlm"
    project.mkdir()
    (project / "IDEA.md").write_text(DLM_IDEA, encoding="utf-8")
    (project / "README.md").write_text("# dlm\n\nProject notes and sources.\n", encoding="utf-8")
    return project


def test_espresso_is_not_filed(tmp_path):
    project = _topic(tmp_path)
    ok, reason = should_file_research(ESPRESSO, str(project), llm_fn=lambda *_a: None)
    assert ok is False
    assert "off-topic" in reason


def test_in_topic_query_is_filed(tmp_path):
    project = _topic(tmp_path)
    ok, reason = should_file_research(IN_TOPIC, str(project), llm_fn=lambda *_a: False)
    assert ok is True
    assert "overlap" in reason or "topic" in reason


def test_empty_topic_still_files(tmp_path):
    project = tmp_path / "blank"
    project.mkdir()
    ok, reason = should_file_research(ESPRESSO, str(project), llm_fn=lambda *_a: False)
    assert ok is True
    assert "identity" in reason


def test_watch_origin_always_files(tmp_path):
    project = _topic(tmp_path)
    ok, _reason = should_file_research(
        ESPRESSO, str(project), origin="watch", llm_fn=lambda *_a: False
    )
    assert ok is True


def test_llm_can_keep_new_on_topic_paper(tmp_path):
    project = _topic(tmp_path)
    ok, reason = should_file_research(
        "Find papers on LLaDA",
        str(project),
        llm_fn=lambda *_a: True,
    )
    assert ok is True
    assert reason == "on-topic"


def test_persist_skips_off_topic_report(tmp_path, monkeypatch):
    from second_brain.memory import learning as learning_mod
    from second_brain.memory.learning import persist_research_memory

    project = _topic(tmp_path)
    monkeypatch.setattr(learning_mod, "DOCUMENTS_DIR", tmp_path)
    monkeypatch.setattr(
        "second_brain.memory.relevance._llm_on_topic",
        lambda *_a, **_k: None,
    )
    meta = persist_research_memory(
        {
            "query": ESPRESSO,
            "report": "## In short\nBuy a Breville Bambino Plus.\n",
            "retrieval_stats": {"web": 4},
        },
        project_path=str(project),
        session_id="sess-1",
        write_report=True,
        ingest=False,
    )
    assert meta["memory_written"] is False
    assert meta["memory_detail"] == SKIP_FILE_DETAIL
    assert meta["claim_count"] == 0
    assert not list((project / "research").glob("*.md"))
    assert not (project / "memory" / "project.md").exists()
