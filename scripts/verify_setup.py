#!/usr/bin/env python3
"""Smoke test: Ollama, Chroma, ingestion, and LangGraph scaffold."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from langchain_core.messages import HumanMessage

from second_brain.config import EMBEDDING_MODEL, OLLAMA_BASE_URL
from second_brain.graph import build_graph
from second_brain.ingestion.pipeline import ingest_file
from second_brain.memory.chroma_store import collection_count
from second_brain.memory.embeddings import get_embeddings


def check(label: str, ok: bool, detail: str = ""):
    status = "PASS" if ok else "FAIL"
    msg = f"  [{status}] {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return ok


def main() -> int:
    print("Second Brain — Phase 0 Setup Verification\n")
    results = []

    # 1. Ollama connectivity + embedding model
    try:
        embeddings = get_embeddings()
        vector = embeddings.embed_query("test connectivity")
        results.append(check(
            "Ollama embeddings",
            len(vector) > 0,
            f"{EMBEDDING_MODEL} @ {OLLAMA_BASE_URL} → dim={len(vector)}",
        ))
    except Exception as e:
        results.append(check("Ollama embeddings", False, str(e)))

    # 2. Chroma persistence
    try:
        before = collection_count()
        results.append(check("Chroma store", True, f"collection count={before}"))
    except Exception as e:
        results.append(check("Chroma store", False, str(e)))

    # 3. Ingest a test file
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(
                "Second Brain is a graph-based multi-agent system for "
                "autonomous research and lifelong personal knowledge management."
            )
            test_path = Path(f.name)

        count = ingest_file(test_path)
        after = collection_count()
        test_path.unlink()
        results.append(check(
            "Document ingestion",
            count > 0 and after > before,
            f"ingested {count} chunk(s), total={after}",
        ))
    except Exception as e:
        results.append(check("Document ingestion", False, str(e)))

    # 4. LangGraph scaffold
    try:
        graph = build_graph()
        result = graph.invoke({
            "query": "test query",
            "messages": [HumanMessage(content="hello")],
            "plan": "",
            "retrieval_queries": [],
            "retrieved_docs": [],
            "analysis": "",
            "critique": "",
            "critique_approved": False,
            "revision_count": 0,
            "report": "",
        })
        results.append(check(
            "LangGraph scaffold",
            result.get("query") == "test query",
            "passthrough node executed",
        ))
    except Exception as e:
        results.append(check("LangGraph scaffold", False, str(e)))

    print()
    passed = sum(results)
    total = len(results)
    print(f"Result: {passed}/{total} checks passed")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())