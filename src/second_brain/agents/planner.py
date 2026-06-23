import logging

from langchain_core.messages import HumanMessage, SystemMessage

from second_brain.agents.prompts import PLANNER_SYSTEM, PLANNER_USER
from second_brain.agents.utils import parse_planner_output
from second_brain.memory.llm import get_llm
from second_brain.state import GraphState

logger = logging.getLogger(__name__)


def planner_node(state: GraphState) -> dict:
    query = state["query"]
    llm = get_llm()

    response = llm.invoke([
        SystemMessage(content=PLANNER_SYSTEM),
        HumanMessage(content=PLANNER_USER.format(query=query)),
    ])
    raw = response.content if isinstance(response.content, str) else str(response.content)

    plan, retrieval_queries = parse_planner_output(raw)
    if not retrieval_queries:
        retrieval_queries = [query]

    logger.info("Planner: %d steps, %d search queries", plan.count("\n") + 1, len(retrieval_queries))

    return {
        "plan": plan,
        "retrieval_queries": retrieval_queries,
        "messages": [HumanMessage(content=f"[Planner] {plan}")],
    }