"""FastAPI sidecar — exposes Second Brain operations over HTTP for the Tauri UI."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv(ROOT / ".env")

from second_brain.config import PROJECT_ROOT  # noqa: E402
from second_brain.graph import run_research  # noqa: E402
from second_brain.ingestion.pipeline import ingest_directory  # noqa: E402
from second_brain.memory.chroma_store import collection_count  # noqa: E402
from second_brain.memory.retriever import retrieve  # noqa: E402
from second_brain.rag.chain import ask  # noqa: E402

app = FastAPI(title="Second Brain Sidecar", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ENV_PATH = PROJECT_ROOT / ".env"
ENV_KEYS = [
    "OLLAMA_BASE_URL",
    "EMBEDDING_MODEL",
    "LLM_MODEL",
    "TAVILY_API_KEY",
    "ENABLE_WEB_SEARCH",
    "ENABLE_ARXIV",
    "RETRIEVAL_TOP_K",
    "MAX_REVISIONS",
]


class QueryRequest(BaseModel):
    question: str
    top_k: int = Field(default=5, ge=1, le=20)


class ResearchRequest(BaseModel):
    query: str


class IngestRequest(BaseModel):
    path: str


class SettingsUpdate(BaseModel):
    values: dict[str, str]


class VaultSearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=8, ge=1, le=20)


class VaultRelatedRequest(BaseModel):
    text: str
    top_k: int = Field(default=5, ge=1, le=20)


def _read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key, _, val = line.partition("=")
                values[key.strip()] = val.strip()
    for key in ENV_KEYS:
        values.setdefault(key, os.getenv(key, ""))
    return {key: values.get(key, "") for key in ENV_KEYS}


def _write_env(updates: dict[str, str]) -> None:
    current = _read_env()
    current.update(updates)
    lines = [f"{key}={current[key]}" for key in ENV_KEYS if current.get(key) is not None]
    ENV_PATH.write_text("\n".join(lines) + "\n")
    load_dotenv(ENV_PATH, override=True)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/status")
def status():
    return {
        "collection_count": collection_count(),
        "project_root": str(PROJECT_ROOT),
        "ollama_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    }


@app.post("/api/query")
def query(req: QueryRequest):
    if collection_count() == 0:
        raise HTTPException(400, "Knowledge base is empty. Ingest documents first.")
    response = ask(req.question, top_k=req.top_k)
    return {
        "question": response.question,
        "answer": response.answer,
        "sources": [
            {
                "index": s.index,
                "source": s.source,
                "page": s.page,
                "excerpt": s.excerpt,
            }
            for s in response.sources
        ],
    }


@app.post("/api/research")
def research(req: ResearchRequest):
    if collection_count() == 0:
        raise HTTPException(400, "Knowledge base is empty. Ingest documents first.")
    result = run_research(req.query)
    return {
        "query": result["query"],
        "plan": result.get("plan", ""),
        "retrieval_queries": result.get("retrieval_queries", []),
        "retrieval_stats": result.get("retrieval_stats", {}),
        "retrieval_log": result.get("retrieval_log", []),
        "analysis": result.get("analysis", ""),
        "revision_count": result.get("revision_count", 0),
        "report": result.get("report", ""),
    }


@app.post("/api/ingest")
def ingest(req: IngestRequest):
    target = Path(req.path).expanduser().resolve()
    if not target.is_dir():
        raise HTTPException(400, f"Not a directory: {target}")
    count = ingest_directory(target)
    return {
        "ingested_chunks": count,
        "collection_total": collection_count(),
        "path": str(target),
    }


@app.get("/api/settings")
def get_settings():
    env = _read_env()
    return {
        "values": env,
        "tavily_configured": bool(env.get("TAVILY_API_KEY")),
    }


@app.put("/api/settings")
def update_settings(req: SettingsUpdate):
    allowed = {k: v for k, v in req.values.items() if k in ENV_KEYS}
    _write_env(allowed)
    return {"updated": list(allowed.keys()), "values": _read_env()}


def _format_retrieval_results(docs) -> list[dict]:
    results = []
    for doc in docs:
        meta = doc.metadata
        results.append(
            {
                "source": meta.get("source", "unknown"),
                "excerpt": doc.page_content[:300],
                "distance": meta.get("distance"),
                "page": meta.get("page"),
            }
        )
    return results


@app.post("/api/vault/search")
def vault_search(req: VaultSearchRequest):
    if collection_count() == 0:
        raise HTTPException(400, "Knowledge base is empty. Ingest documents first.")
    docs = retrieve(req.query, top_k=req.top_k)
    return {"query": req.query, "results": _format_retrieval_results(docs)}


@app.post("/api/vault/related")
def vault_related(req: VaultRelatedRequest):
    if collection_count() == 0:
        return {"query": req.text, "results": []}
    docs = retrieve(req.text, top_k=req.top_k)
    return {"query": req.text, "results": _format_retrieval_results(docs)}


def main():
    import uvicorn

    port = int(os.getenv("SIDECAR_PORT", "8765"))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()