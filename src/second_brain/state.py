from typing import Annotated

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class GraphState(TypedDict):
    query: str
    messages: Annotated[list[BaseMessage], add_messages]
    plan: str
    retrieved_docs: list
    analysis: str
    critique: str
    report: str