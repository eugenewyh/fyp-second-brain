import logging
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage

from second_brain.agents.prompts import ANALYST_REVISION_NOTE, ANALYST_SYSTEM, ANALYST_USER
from second_brain.agents.retrieval_notes import build_retrieval_notes
from second_brain.agents.utils import docs_from_state
from second_brain.memory.llm import invoke_llm
from second_brain.rag.prompts import format_context
from second_brain.state import GraphState

logger = logging.getLogger(__name__)


def analyst_node(state: GraphState) -> dict:
    query = state["query"]
    plan = state.get("plan", "")
    critique = state.get("critique", "")
    revision_count = state.get("revision_count", 0)
    documents = docs_from_state(state.get("retrieved_docs", []))

    critique_section = ""
    if critique and revision_count > 0:
        critique_section = ANALYST_REVISION_NOTE.format(critique=critique)

    retrieval_note = build_retrieval_notes(
        state.get("retrieval_stats", {}),
        state.get("retrieval_log", []),
    )
    context = format_context(documents)

    response = invoke_llm([
        SystemMessage(content=ANALYST_SYSTEM),
        HumanMessage(content=ANALYST_USER.format(
            query=query,
            plan=plan,
            context=context,
            retrieval_note=retrieval_note,
            critique_section=critique_section,
        )),
    ], role="fast")
    analysis = response.content if isinstance(response.content, str) else str(response.content)

    label = "revised" if revision_count > 0 else "initial"
    logger.info("Analyst: %s analysis (%d chars)", label, len(analysis))

    history_delta = [
        {
            "revision_index": revision_count,
            "analysis_excerpt": analysis[:500],
            "analysis_char_count": len(analysis),
            "ts": datetime.now(timezone.utc).isoformat(),
        }
    ]

    return {
        "analysis": analysis,
        "analysis_history": history_delta,
        "messages": [HumanMessage(content=f"[Analyst] {label.capitalize()} analysis complete")],
    }
