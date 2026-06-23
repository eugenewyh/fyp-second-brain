from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage, SystemMessage

from second_brain.config import RETRIEVAL_TOP_K
from second_brain.memory.llm import get_llm
from second_brain.memory.retriever import retrieve
from second_brain.rag.prompts import RAG_SYSTEM_PROMPT, RAG_USER_TEMPLATE, format_context


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