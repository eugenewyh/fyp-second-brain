import logging

from langchain_core.messages import HumanMessage, SystemMessage

from second_brain.agents.grounding import check_grounding
from second_brain.agents.prompts import VERIFIER_SYSTEM, VERIFIER_USER
from second_brain.agents.utils import docs_from_state, parse_verifier_output
from second_brain.config import MAX_REVISIONS
from second_brain.memory.llm import get_llm
from second_brain.rag.prompts import format_context
from second_brain.state import GraphState

logger = logging.getLogger(__name__)


def verifier_node(state: GraphState) -> dict:
    query = state["query"]
    analysis = state.get("analysis", "")
    documents = docs_from_state(state.get("retrieved_docs", []))
    revision_count = state.get("revision_count", 0)

    grounded, grounding_issues = check_grounding(analysis, documents)
    if not grounded:
        feedback = "Rule-based grounding check failed:\n" + "\n".join(
            f"- {issue}" for issue in grounding_issues
        )
        logger.info("Verifier: REVISE (grounding) — %d issue(s)", len(grounding_issues))
        return {
            "critique": feedback,
            "critique_approved": False,
            "revision_count": revision_count + 1,
            "messages": [HumanMessage(content="[Verifier] Revision requested (grounding)")],
        }

    context = format_context(documents)
    llm = get_llm(temperature=0.1)

    response = llm.invoke([
        SystemMessage(content=VERIFIER_SYSTEM),
        HumanMessage(content=VERIFIER_USER.format(
            query=query,
            context=context,
            analysis=analysis,
        )),
    ])
    raw = response.content if isinstance(response.content, str) else str(response.content)
    approved, feedback = parse_verifier_output(raw)

    if not approved and revision_count >= MAX_REVISIONS:
        logger.info("Verifier: max revisions reached — forcing approval")
        approved = True
        feedback = (
            f"Max revisions ({MAX_REVISIONS}) reached. Proceeding with best available analysis.\n"
            f"{feedback}"
        )

    logger.info("Verifier: %s", "APPROVED" if approved else f"REVISE (attempt {revision_count + 1})")

    result = {
        "critique": feedback,
        "critique_approved": approved,
        "messages": [HumanMessage(content=f"[Verifier] {'Approved' if approved else 'Revision requested'}")],
    }

    if not approved:
        result["revision_count"] = revision_count + 1

    return result