from dataclasses import dataclass, field

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from second_brain.config import RETRIEVAL_TOP_K
from second_brain.memory.llm import get_llm
from second_brain.memory.retriever import retrieve
from second_brain.rag.prompts import (
    CHAT_CONTEXT_BLOCK,
    CHAT_SYSTEM_PROMPT,
    CHAT_USER_WITH_CONTEXT,
    RAG_SYSTEM_PROMPT,
    RAG_USER_TEMPLATE,
    format_context,
)


@dataclass
class SourceCitation:
    index: int
    source: str
    page: int | None
    excerpt: str
    distance: float | None = None


@dataclass
class RAGResponse:
    question: str
    answer: str
    sources: list[SourceCitation] = field(default_factory=list)


def _build_citations(documents) -> list[SourceCitation]:
    citations = []
    for i, doc in enumerate(documents, start=1):
        page = doc.metadata.get("page", -1)
        citations.append(SourceCitation(
            index=i,
            source=doc.metadata.get("source", "unknown"),
            page=page + 1 if page >= 0 else None,
            excerpt=doc.page_content[:200].strip(),
            distance=doc.metadata.get("distance"),
        ))
    return citations


def ask(question: str, top_k: int = RETRIEVAL_TOP_K) -> RAGResponse:
    documents = retrieve(question, top_k=top_k)
    citations = _build_citations(documents)

    if not documents:
        return RAGResponse(
            question=question,
            answer=(
                "I could not find any relevant documents in your personal knowledge base. "
                "Try ingesting documents first with: python scripts/ingest.py --input data/documents"
            ),
            sources=[],
        )

    context = format_context(documents)
    llm = get_llm()

    messages = [
        SystemMessage(content=RAG_SYSTEM_PROMPT),
        HumanMessage(content=RAG_USER_TEMPLATE.format(
            context=context,
            question=question,
        )),
    ]

    response = llm.invoke(messages)
    answer = response.content if isinstance(response.content, str) else str(response.content)

    return RAGResponse(question=question, answer=answer, sources=citations)


@dataclass
class ChatContext:
    note_path: str | None = None
    selected_text: str | None = None
    note_excerpt: str | None = None


@dataclass
class ChatMessage:
    role: str
    content: str


MAX_CHAT_HISTORY_TURNS = 10


def _last_user_message(messages: list[ChatMessage]) -> str | None:
    for msg in reversed(messages):
        if msg.role == "user" and msg.content.strip():
            return msg.content.strip()
    return None


def build_chat_system_content(context: ChatContext | None) -> str:
    if not context or not any([context.note_path, context.selected_text, context.note_excerpt]):
        return CHAT_SYSTEM_PROMPT

    selected_block = ""
    if context.selected_text and context.selected_text.strip():
        selected_block = f"Selected text:\n{context.selected_text.strip()}\n"

    excerpt_block = ""
    if context.note_excerpt and context.note_excerpt.strip():
        excerpt = context.note_excerpt.strip()
        if len(excerpt) > 2000:
            excerpt = excerpt[:2000] + "…"
        excerpt_block = f"Note excerpt:\n{excerpt}\n"

    note_path = context.note_path or "none"
    context_block = CHAT_CONTEXT_BLOCK.format(
        note_path=note_path,
        selected_block=selected_block,
        excerpt_block=excerpt_block,
    ).strip()
    return f"{CHAT_SYSTEM_PROMPT}\n\n{context_block}"


def _history_messages(messages: list[ChatMessage]) -> list[HumanMessage | AIMessage]:
    history: list[HumanMessage | AIMessage] = []
    trimmed = messages[-MAX_CHAT_HISTORY_TURNS:]
    for msg in trimmed:
        if msg.role == "user":
            history.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            history.append(AIMessage(content=msg.content))
    return history


def chat_with_context(
    messages: list[ChatMessage],
    context: ChatContext | None = None,
    top_k: int = RETRIEVAL_TOP_K,
) -> RAGResponse:
    question = _last_user_message(messages)
    if not question:
        return RAGResponse(
            question="",
            answer="Please send a message to start the conversation.",
            sources=[],
        )

    documents = retrieve(question, top_k=top_k)
    citations = _build_citations(documents)
    context_text = format_context(documents)

    llm = get_llm()
    llm_messages: list[SystemMessage | HumanMessage | AIMessage] = [
        SystemMessage(content=build_chat_system_content(context)),
    ]

    prior = messages[:-1] if messages and messages[-1].role == "user" else messages
    llm_messages.extend(_history_messages(prior))

    llm_messages.append(
        HumanMessage(
            content=CHAT_USER_WITH_CONTEXT.format(
                context=context_text,
                message=question,
            )
        )
    )

    response = llm.invoke(llm_messages)
    answer = response.content if isinstance(response.content, str) else str(response.content)
    return RAGResponse(question=question, answer=answer, sources=citations)