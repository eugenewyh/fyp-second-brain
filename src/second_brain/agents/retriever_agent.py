import logging

from langchain_core.messages import HumanMessage

from second_brain.agents.hybrid_retriever import hybrid_retrieve
from second_brain.agents.utils import docs_to_state
from second_brain.state import GraphState

logger = logging.getLogger(__name__)


def retriever_node(state: GraphState) -> dict:
    queries = state.get("retrieval_queries") or [state["query"]]
    documents, stats = hybrid_retrieve(queries, main_query=state["query"])

    stats_summary = ", ".join(f"{k}={v}" for k, v in stats.items() if v > 0)
    logger.info(
        "Retriever: %d total chunk(s) from %d queries (%s)",
        len(documents), len(queries), stats_summary or "no results",
    )

    return {
        "retrieved_docs": docs_to_state(documents),
        "retrieval_stats": stats,
        "messages": [
            HumanMessage(content=f"[Retriever] Hybrid search: {len(documents)} result(s) ({stats_summary})"),
        ],
    }