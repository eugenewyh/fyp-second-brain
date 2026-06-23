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


def format_context(documents: list) -> str:
    if not documents:
        return "No relevant documents found."

    parts = []
    for i, doc in enumerate(documents, start=1):
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", -1)
        page_label = f", page {page + 1}" if page >= 0 else ""
        parts.append(
            f"[{i}] Source: {source}{page_label}\n{doc.page_content.strip()}"
        )
    return "\n\n".join(parts)