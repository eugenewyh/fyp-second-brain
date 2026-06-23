import logging

from langchain_core.messages import HumanMessage, SystemMessage

from second_brain.agents.prompts import ANALYST_REVISION_NOTE, ANALYST_SYSTEM, ANALYST_USER
from second_brain.agents.utils import docs_from_state
from second_brain.memory.llm import get_llm
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

    context = format_context(documents)
    llm = get_llm()

    response = llm.invoke([
        SystemMessage(content=ANALYST_SYSTEM),
        HumanMessage(content=ANALYST_USER.format(
            query=query,
            plan=plan,
            context=context,
            critique_section=critique_section,
        )),
    ])
    analysis = response.content if isinstance(response.content, str) else str(response.content)

    label = "revised" if revision_count > 0 else "initial"
    logger.info("Analyst: %s analysis (%d chars)", label, len(analysis))

    return {
        "analysis": analysis,
        "messages": [HumanMessage(content=f"[Analyst] {label.capitalize()} analysis complete")],
    }