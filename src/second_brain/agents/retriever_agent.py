import logging

from langchain_core.messages import HumanMessage

from second_brain.agents.utils import docs_to_state
from second_brain.config import RETRIEVAL_TOP_K_PER_QUERY
from second_brain.memory.retriever import retrieve_multi
from second_brain.state import GraphState

logger = logging.getLogger(__name__)


def retriever_node(state: GraphState) -> dict:
    queries = state.get("retrieval_queries") or [state["query"]]
    documents = retrieve_multi(queries, top_k_per_query=RETRIEVAL_TOP_K_PER_QUERY)

    logger.info("Retriever: %d unique chunk(s) from %d queries", len(documents), len(queries))

    return {
        "retrieved_docs": docs_to_state(documents),
        "messages": [HumanMessage(content=f"[Retriever] Found {len(documents)} relevant chunk(s)")],
    }