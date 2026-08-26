"""RAG helpers. Import chain/prompts from submodules to avoid graph import cycles."""

from typing import Any

__all__ = ["RAGResponse", "ask"]


def __getattr__(name: str) -> Any:
    if name in {"RAGResponse", "ask"}:
        from second_brain.rag.chain import RAGResponse, ask

        return RAGResponse if name == "RAGResponse" else ask
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
