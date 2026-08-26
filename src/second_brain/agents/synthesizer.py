import logging

from langchain_core.messages import HumanMessage, SystemMessage

from second_brain.agents.prompts import FORCED_SYNTHESIS_NOTE, SYNTHESIZER_SYSTEM, SYNTHESIZER_USER
from second_brain.agents.retrieval_notes import build_retrieval_notes
from second_brain.agents.utils import docs_from_state
from second_brain.config import MAX_REVISIONS
from second_brain.memory.learning import compute_confidence, extract_open_questions
from second_brain.memory.llm import invoke_llm
from second_brain.rag.citations import (
    check_report_citations,
    format_bibliography,
    scrub_invalid_citations,
    strip_sources_section,
)
from second_brain.rag.prompts import format_context
from second_brain.state import GraphState

logger = logging.getLogger(__name__)


def synthesizer_node(state: GraphState) -> dict:
    query = state["query"]
    plan = state.get("plan", "")
    analysis = state.get("analysis", "")
    documents = docs_from_state(state.get("retrieved_docs", []))
    revision_count = state.get("revision_count", 0)
    was_forced = revision_count >= MAX_REVISIONS

    critique_note = FORCED_SYNTHESIS_NOTE if was_forced else ""
    retrieval_note = build_retrieval_notes(
        state.get("retrieval_stats", {}),
        state.get("retrieval_log", []),
    )
    context = format_context(documents)

    response = invoke_llm([
        SystemMessage(content=SYNTHESIZER_SYSTEM),
        HumanMessage(content=SYNTHESIZER_USER.format(
            query=query,
            plan=plan,
            analysis=analysis,
            context=context,
            retrieval_note=retrieval_note,
            critique_note=critique_note,
        )),
    ], role="main")
    report_body = response.content if isinstance(response.content, str) else str(response.content)
    report_body = strip_sources_section(report_body)
    bibliography = format_bibliography(documents)
    report = f"{report_body}\n\n## Sources\n\n{bibliography}"

    # Citation hardening: scrub invalid indices; record issues for confidence
    cite_check = check_report_citations(report, len(documents))
    if cite_check.invalid_indices:
        report = scrub_invalid_citations(report, len(documents))
        # Re-append clean bibliography after scrub
        body = strip_sources_section(report)
        report = f"{body}\n\n## Sources\n\n{bibliography}"

    conf_state = {**state, "report": report}
    confidence, confidence_reasons = compute_confidence(conf_state)
    if cite_check.issues:
        confidence = max(0.05, round(confidence - 0.08, 2))
        confidence_reasons = list(confidence_reasons) + cite_check.issues[:2]

    open_questions = extract_open_questions(report)

    logger.info(
        "Synthesizer: report generated (%d chars, confidence=%.2f, cite_ok=%s)",
        len(report),
        confidence,
        cite_check.ok,
    )

    return {
        "report": report,
        "confidence": confidence,
        "confidence_reasons": confidence_reasons,
        "open_questions": open_questions,
        "citation_issues": cite_check.issues,
        "messages": [HumanMessage(content="[Synthesizer] Final report complete")],
    }