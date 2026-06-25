RAG_SYSTEM_PROMPT = """You are a helpful research assistant with access to the user's personal documents.
Answer the question using ONLY the provided context. If the context does not contain enough information, say so clearly.

Rules:
- Cite sources inline using [1], [2], etc. matching the source numbers in the context.
- Be concise and accurate. Do not invent facts not supported by the context.
- If multiple sources support a claim, cite all relevant ones."""

RAG_USER_TEMPLATE = """Context from personal documents:

{context}

Question: {question}

Answer with inline citations:"""

CHAT_SYSTEM_PROMPT = """You are a contextual research assistant helping the user explore their personal knowledge base.
Answer using the retrieved document context and any open-note context provided. If context is insufficient, say so clearly.

Rules:
- Cite sources inline using [1], [2], etc. matching the source numbers in the context.
- Be concise and accurate. Do not invent facts not supported by the context.
- Maintain conversational continuity with prior turns in this thread."""

CHAT_CONTEXT_BLOCK = """Open note: {note_path}
{selected_block}
{excerpt_block}"""

CHAT_USER_WITH_CONTEXT = """Retrieved context from personal documents:

{context}

User message: {message}

Answer with inline citations:"""


_SOURCE_LABELS = {
    "personal": "Personal",
    "web": "Web",
    "arxiv": "arXiv",
}


def format_context(documents: list) -> str:
    if not documents:
        return "No relevant documents found."

    parts = []
    for i, doc in enumerate(documents, start=1):
        source = doc.metadata.get("source", "unknown")
        source_type = doc.metadata.get("source_type", "personal")
        type_label = _SOURCE_LABELS.get(source_type, "Source")
        page = doc.metadata.get("page", -1)
        page_label = f", page {page + 1}" if page >= 0 else ""
        url = doc.metadata.get("source_path", "")
        url_label = f"\nURL: {url}" if url and source_type in {"web", "arxiv"} else ""
        parts.append(
            f"[{i}] {type_label}: {source}{page_label}{url_label}\n{doc.page_content.strip()}"
        )
    return "\n\n".join(parts)