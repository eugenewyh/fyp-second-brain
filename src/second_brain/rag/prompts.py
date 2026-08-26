RAG_SYSTEM_PROMPT = """You are a helpful assistant with access to the user's personal documents.
Answer the question using ONLY the provided context, in short plain sentences a non-expert can follow.
If a technical term is unavoidable, define it in the same sentence.
If the context does not contain enough information, say so clearly.

Rules:
- Cite sources inline using [1], [2], etc. matching the source numbers in the context.
- Be concise and accurate. Do not invent facts not supported by the context.
- Never mention RAG, retrieval, embeddings, or hybrid search.
- If multiple sources support a point, cite all relevant ones."""

RAG_USER_TEMPLATE = """Context from personal documents:

{context}

Question: {question}

Answer with inline citations:"""

CHAT_SYSTEM_PROMPT = """You are a personal assistant for the user's notes.
Answer from their notes and the excerpts from their documents, in short plain sentences a non-expert can follow.
If a technical term is unavoidable, define it in the same sentence.
Say "your notes" — never mention claims, project beliefs, RAG, retrieval, embeddings, or hybrid search.
If the notes do not support an answer, say so clearly — do not invent facts.

Rules:
- Prefer what the notes already settle, and how sources connect, over isolated snippets.
- If the memory marks something as contested, say the disagreement in plain language (for example: "your notes disagree…") while still preferring the settled notes for the main answer.
- Cite sources inline using [1], [2], etc. matching the source numbers in the context.
- Be concise and accurate. Do not invent facts not supported by the context.
- Maintain conversational continuity with prior turns in this thread."""

CHAT_CONTEXT_BLOCK = """Open note: {note_path}
{selected_block}
{excerpt_block}"""

CHAT_USER_WITH_CONTEXT = """From the user's notes:
{memory}

Excerpts from your documents:

{context}

User message: {question}

Answer with inline citations. Explain how sources connect when relevant, in plain language."""


_SOURCE_LABELS = {
    "personal": "Personal",
    "web": "Web",
    "arxiv": "arXiv",
    "mcp": "Notion",
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
        url_label = f"\nURL: {url}" if url and source_type in {"web", "arxiv", "mcp"} else ""
        parts.append(
            f"[{i}] {type_label}: {source}{page_label}{url_label}\n{doc.page_content.strip()}"
        )
    return "\n\n".join(parts)