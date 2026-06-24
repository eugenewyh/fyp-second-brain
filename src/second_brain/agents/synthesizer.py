import logging

from langchain_core.messages import HumanMessage, SystemMessage

from second_brain.agents.prompts import FORCED_SYNTHESIS_NOTE, SYNTHESIZER_SYSTEM, SYNTHESIZER_USER
from second_brain.agents.retrieval_notes import build_retrieval_notes
from second_brain.agents.utils import docs_from_state
from second_brain.config import MAX_REVISIONS
from second_brain.memory.llm import get_llm
from second_brain.rag.citations import format_bibliography, strip_sources_section
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
    llm = get_llm()

    response = llm.invoke([
        SystemMessage(content=SYNTHESIZER_SYSTEM),
        HumanMessage(content=SYNTHESIZER_USER.format(
            query=query,
            plan=plan,
            analysis=analysis,
            context=context,
            retrieval_note=retrieval_note,
            critique_note=critique_note,
        )),
    ])
    report_body = response.content if isinstance(response.content, str) else str(response.content)
    report_body = strip_sources_section(report_body)
    bibliography = format_bibliography(documents)
    report = f"{report_body}\n\n## Sources\n\n{bibliography}"

    logger.info("Synthesizer: report generated (%d chars)", len(report))

    return {
        "report": report,
        "messages": [HumanMessage(content="[Synthesizer] Final report complete")],
    }