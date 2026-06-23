from langchain_core.documents import Document

from second_brain.config import RETRIEVAL_TOP_K
from second_brain.memory.chroma_store import get_collection
from second_brain.memory.embeddings import get_embeddings


def retrieve(query: str, top_k: int = RETRIEVAL_TOP_K) -> list[Document]:
    collection = get_collection()
    if collection.count() == 0:
        return []

    embeddings_model = get_embeddings()
    query_embedding = embeddings_model.embed_query(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    documents: list[Document] = []
    for text, metadata, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        doc_metadata = dict(metadata)
        doc_metadata["distance"] = distance
        documents.append(Document(page_content=text, metadata=doc_metadata))

    return documents


def retrieve_multi(queries: list[str], top_k_per_query: int = 3) -> list[Document]:
    seen: set[str] = set()
    results: list[Document] = []

    for query in queries:
        for doc in retrieve(query, top_k=top_k_per_query):
            doc_id = f"{doc.metadata.get('source', '')}_{doc.metadata.get('chunk_index', '')}"
            if doc_id in seen:
                continue
            seen.add(doc_id)
            results.append(doc)

    return results