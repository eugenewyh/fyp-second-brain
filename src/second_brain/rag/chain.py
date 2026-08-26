from dataclasses import dataclass, field

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from second_brain.agent.supervisor import REFUSE_MESSAGE
from second_brain.config import RETRIEVAL_TOP_K
from second_brain.memory.llm import invoke_llm
from second_brain.memory.recall import memory_is_useful, recall_for_query
from second_brain.memory.retriever import retrieve
from second_brain.rag.prompts import (
    CHAT_CONTEXT_BLOCK,
    CHAT_SYSTEM_PROMPT,
    CHAT_USER_WITH_CONTEXT,
    RAG_SYSTEM_PROMPT,
    RAG_USER_TEMPLATE,
    format_context,
)


THIN_MEMORY_ANSWER = REFUSE_MESSAGE


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
    thin_memory: bool = False
    contested_claims: list[dict] = field(default_factory=list)


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

    messages = [
        SystemMessage(content=RAG_SYSTEM_PROMPT),
        HumanMessage(content=RAG_USER_TEMPLATE.format(
            context=context,
            question=question,
        )),
    ]

    response = invoke_llm(messages, role="fast")
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


def _has_ephemeral_context(context: ChatContext | None) -> bool:
    if not context:
        return False
    return bool(
        (context.selected_text and context.selected_text.strip())
        or (context.note_excerpt and context.note_excerpt.strip())
    )


def chat_with_context(
    messages: list[ChatMessage],
    context: ChatContext | None = None,
    top_k: int = RETRIEVAL_TOP_K,
    project_path: str | None = None,
    session_id: str | None = None,
    also_project_paths: list[str] | None = None,
) -> RAGResponse:
    question = _last_user_message(messages)
    if not question:
        return RAGResponse(
            question="",
            answer="Please send a message to start the conversation.",
            sources=[],
        )

    ephemeral = _has_ephemeral_context(context)
    memory = recall_for_query(
        question,
        project_path=project_path,
        session_id=session_id,
        top_k=top_k,
        also_project_paths=also_project_paths,
    )
    on_topic: bool | None = None
    if project_path and not ephemeral:
        try:
            from second_brain.memory.relevance import should_file_research

            ok, _reason = should_file_research(
                question,
                project_path,
                llm_fn=lambda *_a, **_k: None,
            )
            on_topic = ok
        except Exception:
            on_topic = None
    if not memory_is_useful(memory, has_ephemeral=ephemeral, on_topic=on_topic):
        return RAGResponse(
            question=question,
            answer=THIN_MEMORY_ANSWER,
            sources=[],
            thin_memory=True,
        )

    try:
        documents = retrieve(
            question,
            top_k=top_k,
            project_path=project_path,
            also_project_paths=also_project_paths,
        )
    except Exception:
        documents = []
    citations = _build_citations(documents)
    context_text = format_context(documents)
    memory_text = memory.text or "(none)"

    llm_messages: list[SystemMessage | HumanMessage | AIMessage] = [
        SystemMessage(content=build_chat_system_content(context)),
    ]

    prior = messages[:-1] if messages and messages[-1].role == "user" else messages
    llm_messages.extend(_history_messages(prior))

    llm_messages.append(
        HumanMessage(
            content=CHAT_USER_WITH_CONTEXT.format(
                memory=memory_text,
                context=context_text,
                question=question,
            )
        )
    )

    response = invoke_llm(llm_messages, role="fast")
    answer = response.content if isinstance(response.content, str) else str(response.content)
    return RAGResponse(
        question=question,
        answer=answer,
        sources=citations,
        contested_claims=list(memory.contested_claims or []),
    )