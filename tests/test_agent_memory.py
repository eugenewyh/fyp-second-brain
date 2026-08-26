"""Tests for learning cards, confidence, recall helpers, citations, goal stop logic."""

from second_brain.agent.goal_loop import _follow_up_query, _should_continue
from second_brain.memory.learning import (
    compute_confidence,
    extract_executive_summary,
    extract_key_findings,
    extract_open_questions,
    write_learning_card,
)
from second_brain.rag.citations import check_report_citations, scrub_invalid_citations


SAMPLE_REPORT = """## Executive Summary
Multi-agent systems improve research quality through specialization.

## Key Findings
- Specialized agents reduce hallucination under critique loops.
- Hybrid retrieval combines personal and web sources.

## Detailed Analysis
Agents work in a graph [1].

## Identified Gaps
- Unclear how memory compounds across sessions?
- Missing evaluation of long-horizon goals
- arXiv returned zero results for this topic
"""


def test_extract_open_questions():
    qs = extract_open_questions(SAMPLE_REPORT)
    assert len(qs) >= 1
    assert any("memory" in q.lower() or "unclear" in q.lower() or "missing" in q.lower() for q in qs)


def test_extract_key_findings():
    findings = extract_key_findings(SAMPLE_REPORT)
    assert len(findings) >= 1
    assert "hallucination" in findings[0].lower() or "specialized" in findings[0].lower()


PLAIN_REPORT = """## In short
Multi-agent systems improve research quality through specialization.

## What we found
- Specialized agents reduce hallucination under critique loops.
- Hybrid retrieval combines personal and web sources.

## The details
Agents work in a graph [1].

## What's missing
- Unclear how memory compounds across sessions?
- Missing evaluation of long-horizon goals
- arXiv returned zero results for this topic
"""


def test_extractors_accept_plain_headings():
    assert "specialization" in extract_executive_summary(PLAIN_REPORT).lower()
    findings = extract_key_findings(PLAIN_REPORT)
    assert len(findings) >= 1
    qs = extract_open_questions(PLAIN_REPORT)
    assert len(qs) >= 1


def test_extract_executive_summary_legacy_heading():
    assert "specialization" in extract_executive_summary(SAMPLE_REPORT).lower()


def test_compute_confidence_thin_vs_strong():
    thin = compute_confidence(
        {
            "retrieval_stats": {"personal": 1},
            "critique_structured": {
                "grounding_passed": False,
                "verdict": "revise",
                "source": "grounding",
                "issues": [{"severity": "blocking"}],
            },
            "revision_count": 2,
            "report": SAMPLE_REPORT,
        }
    )
    strong = compute_confidence(
        {
            "retrieval_stats": {"personal": 4, "web": 3, "arxiv": 2},
            "critique_structured": {
                "grounding_passed": True,
                "verdict": "approved",
                "source": "llm",
                "issues": [],
            },
            "critique_approved": True,
            "revision_count": 0,
            "report": "## Executive Summary\nSolid.\n\n## Key Findings\n- A\n\n## Identified Gaps\n- Minor coverage limit\n",
        }
    )
    assert thin[0] < strong[0]
    assert strong[0] >= 0.6


def test_write_learning_card(tmp_path, monkeypatch):
    from second_brain.memory import learning as learning_mod

    monkeypatch.setattr(learning_mod, "DOCUMENTS_DIR", tmp_path)
    monkeypatch.setattr(learning_mod, "learnings_dir", lambda project_path=None: tmp_path / "learnings")

    state = {
        "query": "What is multi-agent research?",
        "report": SAMPLE_REPORT,
        "retrieval_stats": {"personal": 3, "web": 2},
        "critique": "ok",
        "critique_structured": {
            "grounding_passed": True,
            "verdict": "approved",
            "source": "llm",
            "issues": [],
        },
        "revision_count": 0,
        "critique_approved": True,
    }
    card = write_learning_card(
        state,
        ingest=False,
        report_path=str(tmp_path / "research" / "2026-08-06-multi-agent.md"),
    )
    assert card.learning_path
    path = __import__("pathlib").Path(card.learning_path)
    assert path.is_file()
    text = path.read_text()
    assert "type: learning" in text
    assert "multi-agent" in text.lower() or "Learning:" in text
    assert "## Related" in text
    assert "[[2026-08-06-multi-agent]]" in text


def test_learning_card_personal_source_wikilinks(tmp_path, monkeypatch):
    from second_brain.memory import learning as learning_mod

    monkeypatch.setattr(learning_mod, "DOCUMENTS_DIR", tmp_path)
    monkeypatch.setattr(learning_mod, "learnings_dir", lambda project_path=None: tmp_path / "learnings")

    state = {
        "query": "Link my notes",
        "report": SAMPLE_REPORT,
        "retrieval_stats": {"personal": 2},
        "retrieved_docs": [
            {
                "page_content": "note body",
                "metadata": {
                    "source": "rag-and-hallucinations.md",
                    "source_path": "/vault/Second-Brain-Lab/rag-and-hallucinations.md",
                    "source_type": "personal",
                },
            },
            {
                "page_content": "web",
                "metadata": {"source": "https://example.com", "source_type": "web"},
            },
        ],
        "critique_approved": True,
        "revision_count": 0,
    }
    card = write_learning_card(state, ingest=False)
    text = __import__("pathlib").Path(card.learning_path).read_text()
    assert "[[rag-and-hallucinations]]" in text
    assert "example.com" not in text
    report = "Claim [1] and bad [9].\n\n## Sources\n\n[1] x\n"
    r = check_report_citations(report, document_count=2)
    assert not r.ok
    assert 9 in r.invalid_indices
    scrubbed = scrub_invalid_citations(report, 2)
    assert "[9]" not in scrubbed
    assert "[1]" in scrubbed


def test_citation_check_missing_when_docs():
    report = "Long enough body without any citations " + ("word " * 50)
    r = check_report_citations(report, document_count=3)
    assert not r.ok


def test_goal_should_continue():
    cont, reason = _should_continue(
        pass_index=1,
        max_passes=2,
        confidence=0.4,
        min_confidence=0.65,
        open_questions=["What about X?"],
    )
    assert cont is True
    stop, reason2 = _should_continue(
        pass_index=2,
        max_passes=2,
        confidence=0.4,
        min_confidence=0.65,
        open_questions=["What about X?"],
    )
    assert stop is False
    assert reason2 == "max_passes_reached"


def test_follow_up_query():
    q = _follow_up_query("Understand agents", ["Gap A?"], "Prior text about agents")
    assert "Understand agents" in q
    assert "Gap A?" in q


def test_session_scoped_learning_and_project_rollup(tmp_path, monkeypatch):
    from second_brain.memory import learning as learning_mod
    from second_brain.memory.learning import persist_research_memory, read_project_memory_tail

    project = tmp_path / "MyProject"
    project.mkdir()
    monkeypatch.setattr(learning_mod, "DOCUMENTS_DIR", tmp_path)

    state = {
        "query": "Session memory hierarchy",
        "report": SAMPLE_REPORT,
        "retrieval_stats": {"personal": 3},
        "critique": "ok",
        "critique_approved": True,
        "revision_count": 0,
        "critique_structured": {
            "grounding_passed": True,
            "verdict": "approved",
            "source": "llm",
            "issues": [],
        },
    }
    session_id = "abc-123-session"
    meta = persist_research_memory(
        state,
        project_path=str(project),
        session_id=session_id,
        write_report=True,
        ingest=False,
    )
    assert meta["memory_written"] is True
    assert meta["session_id"] == "abc-123-session"
    assert "Updated chat memory" in (meta.get("memory_detail") or "")

    learning = __import__("pathlib").Path(meta["learning_path"])
    assert "memory/agents/abc-123-session/learnings" in str(learning).replace("\\", "/")
    assert learning.is_file()
    assert "session_id:" in learning.read_text()

    agent_mem = project / "memory" / "agents" / "abc-123-session" / "memory.md"
    assert agent_mem.is_file()
    assert "Session memory hierarchy" in agent_mem.read_text()

    project_mem = project / "memory" / "project.md"
    assert project_mem.is_file()
    project_text = project_mem.read_text()
    assert "## Settled claims" in project_text
    assert "## Open questions" in project_text
    assert meta.get("claim_count", 0) >= 1
    peek = read_project_memory_tail(str(project), max_lines=8)
    assert "[[" in peek or "Specialized" in peek or "hallucination" in peek.lower()

    log = project / "memory" / "project-log.md"
    assert log.is_file()


def test_recall_prefers_session_files(tmp_path, monkeypatch):
    from second_brain.memory import learning as learning_mod
    from second_brain.memory.learning import (
        agent_memory_path,
        project_memory_path,
        update_agent_session_memory,
        promote_to_project_memory,
        LearningCard,
    )
    from second_brain.memory.recall import recall_for_query

    project = tmp_path / "Proj"
    project.mkdir()
    monkeypatch.setattr(learning_mod, "DOCUMENTS_DIR", tmp_path)

    card = LearningCard(
        id="x",
        query="Prefer session memory",
        summary="Chat-specific understanding about widgets",
        key_findings=["Widgets matter for multi-agent memory systems"],
        confidence=0.8,
    )
    update_agent_session_memory(card, project_path=str(project), session_id="sess99", ingest=False)
    promote_to_project_memory(card, project_path=str(project), session_id="sess99", ingest=False)

    def fake_retrieve(*_a, **_k):
        return []

    monkeypatch.setattr("second_brain.memory.recall.retrieve", fake_retrieve)
    ctx = recall_for_query(
        "widgets",
        project_path=str(project),
        session_id="sess99",
    )
    assert ctx.recalled_count >= 1
    assert "Chat memory" in ctx.text or "widgets" in ctx.text.lower()
    assert any("memory.md" in s for s in ctx.sources)
    assert agent_memory_path(str(project), "sess99").is_file()
    assert project_memory_path(str(project)).is_file()


def test_claim_upsert_and_supersede(tmp_path, monkeypatch):
    from second_brain.memory import learning as learning_mod
    from second_brain.memory.claims import (
        list_claims,
        upsert_claims_from_learning,
    )
    from second_brain.memory.learning import LearningCard

    project = tmp_path / "ClaimProj"
    project.mkdir()
    monkeypatch.setattr(learning_mod, "DOCUMENTS_DIR", tmp_path)

    card1 = LearningCard(
        id="c1",
        query="Agent memory",
        summary="Specialized agents reduce hallucination under critique loops.",
        key_findings=["Specialized agents reduce hallucination under critique loops."],
        confidence=0.7,
        session_id="s1",
    )
    created = upsert_claims_from_learning(
        card1, project_path=str(project), session_id="s1", ingest=False
    )
    assert len(created) >= 1
    active = list_claims(str(project), status="active")
    assert len(active) >= 1
    first_id = active[0].id

    card2 = LearningCard(
        id="c2",
        query="Agent memory refine",
        summary="Specialized agents reduce hallucination when critique loops are used.",
        key_findings=["Specialized agents reduce hallucination when critique loops are used."],
        confidence=0.85,
        session_id="s1",
    )
    revised = upsert_claims_from_learning(
        card2, project_path=str(project), session_id="s1", ingest=False
    )
    assert any(c.supersedes == first_id for c in revised)
    superseded = list_claims(str(project), status="superseded")
    assert any(c.id == first_id for c in superseded)
    active2 = list_claims(str(project), status="active")
    assert all(c.id != first_id for c in active2)
    text = __import__("pathlib").Path(revised[0].path).read_text()
    assert "Revises [[" in text


def test_consolidate_project_sections(tmp_path, monkeypatch):
    from second_brain.memory import learning as learning_mod
    from second_brain.memory.claims import upsert_claims_from_learning
    from second_brain.memory.learning import LearningCard, consolidate_project_memory

    project = tmp_path / "ConsolProj"
    project.mkdir()
    monkeypatch.setattr(learning_mod, "DOCUMENTS_DIR", tmp_path)

    card = LearningCard(
        id="z",
        query="Consolidate me",
        summary="Hybrid retrieval combines personal and web sources.",
        key_findings=["Hybrid retrieval combines personal and web sources."],
        open_questions=["How does memory compound across sessions?"],
        confidence=0.9,
        session_id="chat42",
    )
    upsert_claims_from_learning(card, project_path=str(project), session_id="chat42", ingest=False)
    path = consolidate_project_memory(
        card, project_path=str(project), session_id="chat42", ingest=False
    )
    text = path.read_text()
    assert "## Settled claims" in text
    assert "## Open questions" in text
    assert "## Recent revisions" in text
    assert "## Active chats" in text
    assert "chat42" in text
    assert "memory compound" in text.lower() or "How does memory" in text


def test_recall_includes_claims_before_vault(tmp_path, monkeypatch):
    from second_brain.memory import learning as learning_mod
    from second_brain.memory.claims import upsert_claims_from_learning
    from second_brain.memory.learning import LearningCard, update_agent_session_memory
    from second_brain.memory.recall import recall_for_query

    project = tmp_path / "RecallClaims"
    project.mkdir()
    monkeypatch.setattr(learning_mod, "DOCUMENTS_DIR", tmp_path)

    card = LearningCard(
        id="r1",
        query="Claims recall",
        summary="Citation accuracy improves with grounding checks.",
        key_findings=["Citation accuracy improves with grounding checks in multi-agent research."],
        confidence=0.8,
        session_id="sessA",
    )
    upsert_claims_from_learning(card, project_path=str(project), session_id="sessA", ingest=False)
    update_agent_session_memory(
        card, project_path=str(project), session_id="sessA", claim_slugs=["x"], ingest=False
    )

    monkeypatch.setattr("second_brain.memory.recall.retrieve", lambda *_a, **_k: [])
    ctx = recall_for_query(
        "citation grounding accuracy",
        project_path=str(project),
        session_id="sessA",
    )
    assert "Project claims" in ctx.text or "citation" in ctx.text.lower()
    assert "Chat memory" in ctx.text
