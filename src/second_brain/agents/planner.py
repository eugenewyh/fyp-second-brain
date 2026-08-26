import logging

from langchain_core.messages import HumanMessage, SystemMessage

from second_brain.agents.prompts import PLANNER_SYSTEM, PLANNER_USER
from second_brain.agents.utils import parse_planner_output
from second_brain.memory.llm import invoke_llm
from second_brain.scope import (
    filter_queries_for_scope,
    normalize_scope,
    planner_scope_instructions,
)
from second_brain.state import GraphState

logger = logging.getLogger(__name__)


def planner_node(state: GraphState) -> dict:
    query = state["query"]
    scope = normalize_scope(state.get("retrieval_scope"))
    scope_note = planner_scope_instructions(scope)
    memory_context = (state.get("memory_context") or "").strip()

    user_prompt = PLANNER_USER.format(query=query)
    if memory_context:
        user_prompt = (
            f"{user_prompt}\n\n"
            "---\n"
            "MEMORY (prior agent learnings & vault — build on this; do not redo needlessly):\n"
            f"{memory_context[:3500]}\n"
            "---\n"
            "Prefer queries that deepen open questions and connect to prior findings."
        )

    response = invoke_llm(
        [
            SystemMessage(content=f"{PLANNER_SYSTEM}\n\n{scope_note}"),
            HumanMessage(content=user_prompt),
        ],
        role="main",
    )
    raw = response.content if isinstance(response.content, str) else str(response.content)

    plan, retrieval_queries = parse_planner_output(raw)
    if not retrieval_queries:
        if scope == "web":
            retrieval_queries = [f"[web] {query}", f"[arxiv] {query}"]
        else:
            retrieval_queries = [f"[personal] {query}"]

    retrieval_queries = filter_queries_for_scope(retrieval_queries, scope)
    if not retrieval_queries:
        if scope == "web":
            retrieval_queries = [f"[web] {query}"]
        else:
            retrieval_queries = [f"[personal] {query}"]

    logger.info(
        "Planner: scope=%s, memory_chars=%d, %d steps, %d search queries",
        scope,
        len(memory_context),
        plan.count("\n") + 1,
        len(retrieval_queries),
    )

    return {
        "plan": plan,
        "retrieval_queries": retrieval_queries,
        "retrieval_scope": scope,
        "messages": [HumanMessage(content=f"[Planner] {plan}")],
    }
