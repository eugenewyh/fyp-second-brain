import logging

from langgraph.graph import END, START, StateGraph

from second_brain.state import GraphState

logger = logging.getLogger(__name__)


def passthrough(state: GraphState) -> GraphState:
    logger.info("Graph passthrough — query: %s", state.get("query", ""))
    return state


def build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("passthrough", passthrough)
    graph.add_edge(START, "passthrough")
    graph.add_edge("passthrough", END)
    return graph.compile()