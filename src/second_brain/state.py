from typing import Annotated

import operator
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class GraphState(TypedDict):
    query: str
    messages: Annotated[list[BaseMessage], add_messages]
    plan: str
    retrieval_queries: list[str]
    retrieval_stats: dict[str, int]
    retrieval_log: list[str]
    retrieved_docs: list[dict]
    analysis: str
    critique: str
    critique_approved: bool
    revision_count: int
    report: str
    # Structured critique (latest) + append-only histories
    critique_structured: dict | None
    critique_history: Annotated[list[dict], operator.add]
    analysis_history: Annotated[list[dict], operator.add]
    # local | hybrid | web — where agents may search
    retrieval_scope: str
    # Optional vault project folder path — scopes personal retrieval
    project_path: str | None
    # Extra topic folders for this turn only (explicit cross-topic retrieve)
    also_project_paths: list[str]
    # Chat/session id — scopes agent memory write/recall
    session_id: str | None
    # Auto-recalled prior learnings / research for planner
    memory_context: str
    memory_recalled_count: int
    # Quality signals
    confidence: float
    confidence_reasons: list[str]
    open_questions: list[str]
    learning_path: str | None
    report_path: str | None
    citation_issues: list[str]
