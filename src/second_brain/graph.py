import logging
from typing import Literal

from langgraph.graph import END, START, StateGraph

from second_brain.agents import (
    analyst_node,
    planner_node,
    retriever_node,
    synthesizer_node,
    verifier_node,
)
from second_brain.config import MAX_REVISIONS
from second_brain.state import GraphState

logger = logging.getLogger(__name__)


def route_after_verifier(state: GraphState) -> Literal["analyst", "synthesizer"]:
    if state.get("critique_approved"):
        return "synthesizer"
    if state.get("revision_count", 0) >= MAX_REVISIONS:
        return "synthesizer"
    return "analyst"


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("planner", planner_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("verifier", verifier_node)
    graph.add_node("synthesizer", synthesizer_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "retriever")
    graph.add_edge("retriever", "analyst")
    graph.add_edge("analyst", "verifier")
    graph.add_conditional_edges("verifier", route_after_verifier, {
        "analyst": "analyst",
        "synthesizer": "synthesizer",
    })
    graph.add_edge("synthesizer", END)

    return graph.compile()


def run_research(query: str) -> GraphState:
    graph = build_graph()
    initial_state: GraphState = {
        "query": query,
        "messages": [],
        "plan": "",
        "retrieval_queries": [],
        "retrieved_docs": [],
        "analysis": "",
        "critique": "",
        "critique_approved": False,
        "revision_count": 0,
        "report": "",
    }
    logger.info("Starting research workflow for: %s", query)
    return graph.invoke(initial_state)