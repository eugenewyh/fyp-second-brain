"""FastAPI sidecar — exposes Second Brain operations over HTTP for the Tauri UI."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

load_dotenv(ROOT / ".env")

from second_brain.agent.daily_review import (  # noqa: E402
    plan_daily_review,
    plan_to_dict,
    review_status_payload,
)
from second_brain.agent.harness import (  # noqa: E402
    live_allow_list,
    live_max_passes,
    live_min_confidence,
    resolve_run_spec,
    run_harness_stream,
)
from second_brain.config import (  # noqa: E402
    AGENT_MODE_DEFAULT,
    DAILY_REVIEW_CATCH_UP,
    DAILY_REVIEW_HOUR,
    DAILY_REVIEW_MAX_GOALS,
    ENABLE_SELF_CRITIQUE,
    PLAN_REVIEW_DEFAULT,
    PROJECT_ROOT,
)
from second_brain.memory.digest import get_digest, list_digests  # noqa: E402
from second_brain.memory.digest_link import digest_and_link  # noqa: E402
from second_brain.graph import (  # noqa: E402
    run_plan,
    run_research,
    stream_execute,
    stream_research,
)
from second_brain.ingestion.pipeline import ingest_directory, ingest_file  # noqa: E402
from second_brain.memory.chroma_store import collection_count, reset_vector_store  # noqa: E402
from second_brain.memory.embeddings import probe_embeddings  # noqa: E402
from second_brain.memory.retriever import retrieve  # noqa: E402
from second_brain.rag.chain import ChatContext, ChatMessage, ask, chat_with_context  # noqa: E402
from second_brain.tools.mcp_client import mcp_status  # noqa: E402

from sidecar.runs import MAX_CONCURRENT_RUNS, RUNS  # noqa: E402
from sidecar.scheduler import start_scheduler  # noqa: E402

app = FastAPI(title="Second Brain Sidecar", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _reserve_auto(project_path: str | None = None) -> str:
    token, busy = RUNS.begin_auto(project_path)
    if busy:
        raise HTTPException(
            409,
            f"Too many research graphs in flight (max {MAX_CONCURRENT_RUNS}, active={busy})",
        )
    return token


@app.on_event("startup")
def _start_daily_review_scheduler():
    start_scheduler(acquire_lock=RUNS.try_begin_auto, release_lock=RUNS.end_auto)

ENV_PATH = PROJECT_ROOT / ".env"
ENV_KEYS = [
    "LLM_PROVIDER",
    "GROQ_API_KEY",
    "LLM_API_KEY",
    "LLM_BASE_URL",
    "LLM_MAX_TOKENS",
    "GROQ_MAX_TOKENS",
    "OLLAMA_BASE_URL",
    "EMBEDDING_PROVIDER",
    "EMBEDDING_MODEL",
    "EMBEDDING_API_KEY",
    "EMBEDDING_BASE_URL",
    "LLM_MODEL",
    "LLM_FAST_MODEL",
    "GROQ_FALLBACK_MODEL",
    "LLM_FALLBACK_MODEL",
    "OPENAI_API_KEY",
    "XAI_API_KEY",
    "OPENROUTER_API_KEY",
    "CUSTOM_API_KEY",
    "CUSTOM_BASE_URL",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "SESSION_TITLE_MODEL",
    "GEMINI_LITE_MODEL",
    "TAVILY_API_KEY",
    "ENABLE_WEB_SEARCH",
    "ENABLE_ARXIV",
    "ENABLE_MCP",
    "NOTION_API_KEY",
    "RETRIEVAL_TOP_K",
    "MAX_REVISIONS",
    "AUTO_MEMORY",
    "AUTO_RECALL",
    "MAX_GOAL_PASSES",
    "WATCH_MAX_PASSES",
    "MIN_GOAL_CONFIDENCE",
    "AGENT_MODE_DEFAULT",
    "PLAN_REVIEW_DEFAULT",
    "DAILY_REVIEW_ENABLED",
    "DAILY_REVIEW_HOUR",
    "DAILY_REVIEW_MAX_GOALS",
    "DAILY_REVIEW_CATCH_UP",
    "ENABLE_SELF_CRITIQUE",
    "CLOUD_WATCH_URL",
    "CLOUD_WATCH_TOKEN",
    "CLOUD_WATCH_USER_TOKEN",
]

# Kept in .env for the sidecar; never shown or writable via Settings UI.
_HIDDEN_ENV_KEYS = frozenset(
    {
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "SESSION_TITLE_MODEL",
        "GEMINI_LITE_MODEL",
        # Cloud Watch: URL is operator/build config; session token is set by sign-in.
        "CLOUD_WATCH_URL",
        "CLOUD_WATCH_TOKEN",
        "CLOUD_WATCH_USER_TOKEN",
    }
)


class QueryRequest(BaseModel):
    question: str
    top_k: int = Field(default=5, ge=1, le=20)


class ChatMessageRequest(BaseModel):
    role: str
    content: str


class ChatContextRequest(BaseModel):
    note_path: str | None = None
    selected_text: str | None = None
    note_excerpt: str | None = None


class ChatRequest(BaseModel):
    messages: list[ChatMessageRequest]
    context: ChatContextRequest | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    project_path: str | None = None
    session_id: str | None = None
    also_project_paths: list[str] = Field(default_factory=list)


class WatchRunRequest(BaseModel):
    project_path: str
    watch_id: str | None = None
    session_id: str | None = None
    force: bool = False
    max_passes: int | None = Field(default=None, ge=1, le=4)


class WatchSteerRequest(BaseModel):
    project_path: str
    watch_id: str | None = None
    note: str


class WatchUpdateRequest(BaseModel):
    project_path: str
    watch_id: str | None = None
    name: str | None = None
    focus: str | None = None
    include: str | None = None
    exclude: str | None = None
    trusted_sources: str | None = None
    enabled: bool | None = None


class WatchCreateRequest(BaseModel):
    project_path: str
    name: str | None = None
    focus: str | None = None
    include: str | None = None
    enabled: bool | None = None


class WatchMoveRequest(BaseModel):
    project_path: str
    dest_project_path: str
    watch_id: str | None = None


class WatchDeleteRequest(BaseModel):
    project_path: str
    watch_id: str | None = None


class WatchPromoteRequest(BaseModel):
    project_path: str
    name: str | None = None


class CloudWatchSyncRequest(BaseModel):
    project_path: str
    watch_id: str | None = None


class CloudWatchAuthRequest(BaseModel):
    email: str
    password: str


class CloudWatchLlmRequest(BaseModel):
    llm_provider: str = "groq"
    llm_api_key: str = ""
    llm_model: str = ""


class ActRequest(BaseModel):
    """Supervisor: pick file / answer / research / refuse."""

    message: str = ""
    project_path: str | None = None
    session_id: str | None = None
    has_attachments: bool = False


class ManagerHistoryItem(BaseModel):
    role: str = "user"
    content: str = ""


class TopicRefBody(BaseModel):
    name: str
    path: str = ""


class ManagerTurnRequest(BaseModel):
    """Router: ask, onboard, or dispatch. Does not run the skill."""

    message: str = ""
    project_path: str | None = None
    session_id: str | None = None
    has_attachments: bool = False
    clarify_count: int = 0
    history: list[ManagerHistoryItem] = Field(default_factory=list)
    topics: list[TopicRefBody] = Field(default_factory=list)
    workspace_empty: bool | None = None
    agent: str | None = None
    # Shift+Tab / plus menu: answer | research | file — policy still clamps
    forced_job: str | None = None


class DigestRequest(BaseModel):
    """Remember-path: write sourced claims."""

    text: str | None = None
    title: str | None = None
    path: str | None = None
    paths: list[str] | None = None
    project_path: str | None = None
    session_id: str | None = None


class SessionTitleRequest(BaseModel):
    """Auto-rename a chat from the first user message (Gemini Flash-Lite)."""

    message: str = Field(..., min_length=1, max_length=4000)


class ResearchRequest(BaseModel):
    query: str
    """Optional prior research context for multi-turn continuity."""
    prior_context: str | None = None
    """local | hybrid | web — where agents may search."""
    retrieval_scope: str = "hybrid"
    """Optional vault project folder — scopes personal retrieval."""
    project_path: str | None = None
    """Desktop chat/session id — scopes agent memory."""
    session_id: str | None = None
    also_project_paths: list[str] = Field(default_factory=list)


class GoalRequest(BaseModel):
    """Autonomous multi-pass goal (plan review skipped)."""

    goal: str
    retrieval_scope: str = "hybrid"
    project_path: str | None = None
    session_id: str | None = None
    max_passes: int | None = Field(default=None, ge=1, le=4)
    min_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    also_project_paths: list[str] = Field(default_factory=list)


class ResearchPlanRequest(BaseModel):
    query: str
    prior_context: str | None = None
    replace_run_id: str | None = None
    retrieval_scope: str = "hybrid"
    project_path: str | None = None
    session_id: str | None = None
    also_project_paths: list[str] = Field(default_factory=list)


class ResearchExecuteRequest(BaseModel):
    run_id: str
    query: str
    plan: str
    retrieval_queries: list[str]
    retrieval_scope: str | None = None
    project_path: str | None = None
    session_id: str | None = None
    also_project_paths: list[str] = Field(default_factory=list)


class MemoryMergeRequest(BaseModel):
    source_project_path: str
    dest_project_path: str
    ingest: bool = True


class IngestRequest(BaseModel):
    path: str
    reset: bool = False


class IngestFileRequest(BaseModel):
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


# Numeric settings: never persist blank (breaks int() on restart / confuses UI)
_ENV_INT_DEFAULTS = {
    "GROQ_MAX_TOKENS": "4096",
    "LLM_MAX_TOKENS": "4096",
    "RETRIEVAL_TOP_K": "5",
    "MAX_REVISIONS": "2",
    "MAX_GOAL_PASSES": "2",
    "WATCH_MAX_PASSES": "1",
}


def _write_env(updates: dict[str, str]) -> None:
    current = _read_env()
    current.update(updates)
    for key, default in _ENV_INT_DEFAULTS.items():
        if key in current and not str(current.get(key, "")).strip():
            current[key] = default
    lines = [f"{key}={current[key]}" for key in ENV_KEYS if current.get(key) is not None]
    ENV_PATH.write_text("\n".join(lines) + "\n")
    load_dotenv(ENV_PATH, override=True)
    # Refresh process env for live LLM provider switches without full restart
    for key, val in current.items():
        if val is not None:
            os.environ[key] = str(val)


@app.get("/health")
def health():
    return {"status": "ok", "watches_api": 3, "act_api": 1}


@app.get("/api/mcp/status")
def mcp_status_endpoint():
    return mcp_status()


@app.get("/api/status")
def status():
    emb = probe_embeddings()
    return {
        "collection_count": collection_count(),
        "project_root": str(PROJECT_ROOT),
        "ollama_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "llm_provider": os.getenv("LLM_PROVIDER", "groq"),
        "llm_model": os.getenv("LLM_MODEL", ""),
        "llm_fast_model": os.getenv("LLM_FAST_MODEL", ""),
        "embeddings_provider": emb.get("embeddings_provider"),
        "embeddings_model": emb.get("embeddings_model"),
        "embeddings_ok": emb.get("embeddings_ok", False),
        "embeddings_error": emb.get("embeddings_error", ""),
        "embedding_dims": emb.get("embedding_dims"),
        "reindex_required": emb.get("reindex_required", False),
        "fingerprint": emb.get("fingerprint"),
    }


def _require_embeddings_ready():
    """Fail before planner/Ask spends tokens when memory search is broken."""
    emb = probe_embeddings()
    if not emb.get("embeddings_ok"):
        raise HTTPException(
            503,
            emb.get("embeddings_error")
            or "Embeddings unavailable. Check Settings → Embedding provider "
            "(default is bundled fastembed; Ollama is optional).",
        )
    if emb.get("reindex_required"):
        raise HTTPException(
            409,
            emb.get("embeddings_error")
            or "Vault was indexed with a different embedding model. "
            "Re-ingest documents from the Knowledge / Ingest panel.",
        )


@app.post("/api/act")
def act(req: ActRequest):
    """Recall, then pick a job. Does not run the skill."""
    from second_brain.agent.supervisor import decide_act

    return decide_act(
        req.message,
        project_path=req.project_path,
        has_attachments=req.has_attachments,
    ).to_dict()


@app.post("/api/manager/turn")
def manager_turn(req: ManagerTurnRequest):
    """Grok-short router: ask only if vague, else dispatch. Does not run the skill."""
    from second_brain.agent.manager import take_turn

    return take_turn(
        req.message,
        project_path=req.project_path,
        has_attachments=req.has_attachments,
        clarify_count=req.clarify_count,
        history=[{"role": h.role, "content": h.content} for h in req.history],
        topics=[t.model_dump() for t in req.topics],
        workspace_empty=req.workspace_empty,
        agent=req.agent,
        forced_job=req.forced_job,
    ).to_dict()


@app.post("/api/session-title")
def session_title(req: SessionTitleRequest):
    """Generate a short chat title via Gemini Flash-Lite (optional GEMINI_API_KEY)."""
    from second_brain.memory.session_title import (
        generate_session_title,
        gemini_title_configured,
        session_title_model,
    )

    if not gemini_title_configured():
        return {
            "title": None,
            "configured": False,
            "model": session_title_model(),
        }
    title = generate_session_title(req.message)
    return {
        "title": title,
        "configured": True,
        "model": session_title_model(),
    }


@app.post("/api/chat")
def chat(req: ChatRequest):
    if collection_count() == 0:
        raise HTTPException(400, "Knowledge base is empty. Ingest documents first.")
    _require_embeddings_ready()
    messages = [ChatMessage(role=m.role, content=m.content) for m in req.messages]
    ctx = None
    if req.context:
        ctx = ChatContext(
            note_path=req.context.note_path,
            selected_text=req.context.selected_text,
            note_excerpt=req.context.note_excerpt,
        )
    response = chat_with_context(
        messages,
        context=ctx,
        top_k=req.top_k,
        project_path=req.project_path,
        session_id=req.session_id,
        also_project_paths=req.also_project_paths or None,
    )
    return {
        "question": response.question,
        "answer": response.answer,
        "thin_memory": response.thin_memory,
        "contested_claims": response.contested_claims or [],
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


@app.post("/api/memory/merge")
def memory_merge(req: MemoryMergeRequest):
    """Copy claims from one topic folder into another. Source is left in place."""
    from second_brain.memory.claims import merge_topic_claims
    from second_brain.memory.learning import has_topic_path

    if not has_topic_path(req.source_project_path) or not has_topic_path(req.dest_project_path):
        raise HTTPException(400, "source_project_path and dest_project_path are required")
    try:
        return merge_topic_claims(
            req.source_project_path,
            req.dest_project_path,
            ingest=req.ingest,
        )
    except Exception as e:
        raise HTTPException(502, f"Merge failed: {e}") from e


@app.post("/api/query")
def query(req: QueryRequest):
    if collection_count() == 0:
        raise HTTPException(400, "Knowledge base is empty. Ingest documents first.")
    _require_embeddings_ready()
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


def _compose_query(query: str, prior_context: str | None) -> str:
    if not prior_context or not prior_context.strip():
        return query
    return (
        f"{query}\n\n"
        "---\n"
        "Prior research context (continue and deepen; do not repeat unnecessarily):\n"
        f"{prior_context.strip()[:4000]}"
    )


def _research_payload(result: dict) -> dict:
    """Research result for desktop — includes critique, confidence, memory paths.

    Note: retrieved_docs intentionally omitted (large; not for localStorage).
    """
    return {
        "query": result.get("query", ""),
        "plan": result.get("plan", ""),
        "retrieval_queries": result.get("retrieval_queries", []),
        "retrieval_stats": result.get("retrieval_stats", {}),
        "retrieval_log": result.get("retrieval_log", []),
        "analysis": result.get("analysis", ""),
        "revision_count": result.get("revision_count", 0),
        "report": result.get("report", ""),
        "critique": result.get("critique", ""),
        "critique_approved": bool(result.get("critique_approved", False)),
        "critique_structured": result.get("critique_structured"),
        "critique_history": result.get("critique_history") or [],
        "analysis_history": result.get("analysis_history") or [],
        "retrieval_scope": result.get("retrieval_scope") or "hybrid",
        "confidence": result.get("confidence"),
        "confidence_reasons": result.get("confidence_reasons") or [],
        "open_questions": result.get("open_questions") or [],
        "learning_path": result.get("learning_path"),
        "report_path": result.get("report_path") or result.get("saved_path"),
        "citation_issues": result.get("citation_issues") or [],
        "memory_recalled_count": result.get("memory_recalled_count"),
        "memory_written": result.get("memory_written") is not False,
        "memory_detail": result.get("memory_detail"),
        "claim_count": result.get("claim_count"),
        "claim_slugs": result.get("claim_slugs") or [],
        "claims_revised": result.get("claims_revised"),
        "contested_claims": result.get("contested_claims") or [],
        "goal": result.get("goal"),
        "goal_status": result.get("goal_status"),
        "goal_stop_reason": result.get("goal_stop_reason"),
        "passes": result.get("passes") or [],
        "pass_count": result.get("pass_count"),
        "brief_path": result.get("brief_path"),
        "slow_day": result.get("slow_day"),
    }


def _friendly_research_error(exc: BaseException) -> str:
    text = str(exc)
    lower = text.lower()
    if "rate_limit" in lower or "rate limit" in lower or "429" in lower or "tokens per minute" in lower:
        return (
            "AI rate limit reached (tokens/minute). "
            "Wait 30–60s and retry, use Library-only scope, or switch provider in Settings "
            "(OpenRouter, DeepSeek, xAI, etc.). Multi-agent research uses several model calls."
        )
    if "api key" in lower or "groq_api_key" in lower or "llm_api_key" in lower:
        return "API key missing or invalid. Open Settings and add your key (BYOK)."
    if "connection" in lower or "refused" in lower:
        return "Could not reach the AI service. Check the connection, then retry."
    return text


def _require_kb_if_local(scope: str) -> None:
    """Web-only runs may proceed with an empty vault."""
    s = (scope or "hybrid").lower()
    if s == "web":
        return
    if collection_count() == 0:
        raise HTTPException(400, "Knowledge base is empty. Ingest documents first.")
    _require_embeddings_ready()


@app.post("/api/research")
def research(req: ResearchRequest):
    _require_kb_if_local(req.retrieval_scope)
    try:
        result = run_research(
            req.query,
            retrieval_scope=req.retrieval_scope,
            project_path=req.project_path,
            prior_context=req.prior_context,
            session_id=req.session_id,
            also_project_paths=req.also_project_paths or None,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=_friendly_research_error(e)) from e
    return _research_payload(result)


def _sse_from_stream(stream_iter, *, display_query: str):
    """Shared SSE formatting for auto stream, execute, and goal streams."""
    try:
        for kind, payload in stream_iter:
            if kind == "complete":
                body = _research_payload(payload if isinstance(payload, dict) else {})
                # Prefer original user goal/query for display when present
                if not body.get("goal"):
                    body["query"] = display_query
                yield f"data: {json.dumps({'type': 'result', 'result': body})}\n\n"
            elif kind == "error":
                msg = (
                    payload.get("message", str(payload))
                    if isinstance(payload, dict)
                    else str(payload)
                )
                yield f"data: {json.dumps({'type': 'error', 'message': _friendly_research_error(Exception(msg))})}\n\n"
            elif kind in {
                "stage",
                "agent_status",
                "plan",
                "artifact",
                "critique",
                "memory",
                "goal_pass",
                "goal_status",
                "watch_brief",
            }:
                body = {"type": kind}
                if isinstance(payload, dict):
                    body.update(payload)
                yield f"data: {json.dumps(body)}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': _friendly_research_error(e)})}\n\n"


@app.post("/api/research/plan")
def research_plan(req: ResearchPlanRequest):
    """Plan-only: run planner, store pending run for HITL approval."""
    scope = req.retrieval_scope or "hybrid"
    _require_kb_if_local(scope)
    composed = _compose_query(req.query, req.prior_context)
    try:
        result = run_plan(
            composed,
            retrieval_scope=scope,
            project_path=req.project_path,
            prior_context=None,  # already folded into composed when needed
            session_id=req.session_id,
            also_project_paths=req.also_project_paths or None,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=_friendly_research_error(e)) from e

    plan = (result.get("plan") or "").strip()
    queries = [q.strip() for q in (result.get("retrieval_queries") or []) if q.strip()]
    if not plan:
        raise HTTPException(502, "Planner returned an empty plan")
    if not queries:
        if scope == "web":
            queries = [f"[web] {req.query[:120]}"]
        else:
            queries = [f"[personal] {req.query[:120]}"]

    rec = RUNS.create(
        query=req.query,
        composed_query=composed,
        plan=plan,
        retrieval_queries=queries,
        replace_run_id=req.replace_run_id,
        retrieval_scope=scope,
        project_path=req.project_path,
        session_id=req.session_id,
    )
    return {
        "run_id": rec.run_id,
        "query": rec.query,
        "composed_query": rec.composed_query,
        "plan": rec.plan,
        "retrieval_queries": rec.retrieval_queries,
        "status": rec.status,
        "expires_at": time_iso(rec.expires_at),
        "retrieval_scope": rec.retrieval_scope,
    }


def time_iso(ts: float) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


@app.post("/api/research/execute")
def research_execute(req: ResearchExecuteRequest):
    """Execute approved plan as SSE (retriever → … → synthesizer)."""
    plan = req.plan.strip()
    queries = [q.strip() for q in req.retrieval_queries if q.strip()]
    if not plan:
        raise HTTPException(400, "plan must be non-empty")
    if not queries:
        raise HTTPException(400, "retrieval_queries must be non-empty")

    rec, err = RUNS.begin_execute(req.run_id)
    if err == "not_found":
        raise HTTPException(404, "Unknown run_id — regenerate plan")
    if err == "expired":
        raise HTTPException(410, "Plan expired — regenerate")
    if err == "bad_status":
        raise HTTPException(409, f"Run not pending approval (status={rec.status if rec else '?'})")
    if err == "busy":
        raise HTTPException(
            409,
            f"Too many research graphs in flight (max {MAX_CONCURRENT_RUNS}, active={RUNS.active_run_id()})",
        )
    assert rec is not None

    # Persist user edits onto the record for debug
    rec.plan = plan
    rec.retrieval_queries = queries
    scope = req.retrieval_scope or rec.retrieval_scope or "hybrid"
    rec.retrieval_scope = scope
    project_path = req.project_path if req.project_path is not None else rec.project_path
    rec.project_path = project_path
    session_id = req.session_id if req.session_id is not None else rec.session_id
    rec.session_id = session_id
    _require_kb_if_local(scope)

    def event_gen():
        try:
            yield from _sse_from_stream(
                stream_execute(
                    composed_query=rec.composed_query,
                    plan=plan,
                    retrieval_queries=queries,
                    retrieval_scope=scope,
                    project_path=project_path,
                    session_id=session_id,
                    also_project_paths=req.also_project_paths or None,
                ),
                display_query=req.query or rec.query,
            )
            RUNS.finish(req.run_id, "completed")
        except Exception:
            RUNS.finish(req.run_id, "cancelled")
            raise

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.delete("/api/research/runs/{run_id}")
def research_cancel_run(run_id: str):
    if not RUNS.cancel(run_id):
        raise HTTPException(404, "Run not found or not cancellable")
    return {"ok": True, "run_id": run_id}


@app.get("/api/research/runs/{run_id}")
def research_get_run(run_id: str):
    rec = RUNS.get(run_id)
    if not rec:
        raise HTTPException(404, "Run not found")
    if rec.status == "expired":
        raise HTTPException(410, "Plan expired")
    return rec.public_dict()


@app.post("/api/research/stream")
def research_stream(req: ResearchRequest):
    """SSE stream of multi-agent events (flat dual-compat), then result + done.

    Event types: agent_status, stage, plan, artifact, critique, memory, result, done, error.
    Unknown types should be ignored by older clients.
    """
    _require_kb_if_local(req.retrieval_scope or "hybrid")

    token = _reserve_auto(req.project_path)
    scope = req.retrieval_scope or "hybrid"

    def event_gen():
        try:
            yield from _sse_from_stream(
                stream_research(
                    req.query,
                    retrieval_scope=scope,
                    project_path=req.project_path,
                    prior_context=req.prior_context,
                    session_id=req.session_id,
                    also_project_paths=req.also_project_paths or None,
                ),
                display_query=req.query,
            )
        finally:
            RUNS.end_auto(token)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/goals/stream")
def goals_stream(req: GoalRequest):
    """Autonomous multi-pass goal stream (no plan review)."""
    spec = resolve_run_spec(
        kind="goal",
        instruction=req.goal,
        project_path=req.project_path,
        session_id=req.session_id,
        retrieval_scope=req.retrieval_scope,
        max_passes=req.max_passes,
        min_confidence=req.min_confidence,
        also_project_paths=req.also_project_paths or None,
    )
    _require_kb_if_local(spec.retrieval_scope)
    token = _reserve_auto(req.project_path)

    def event_gen():
        try:
            yield from _sse_from_stream(
                run_harness_stream(spec),
                display_query=req.goal,
            )
        finally:
            RUNS.end_auto(token)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/agent/defaults")
def agent_defaults():
    """Frontend defaults for goal vs studio modes. Live env so Capabilities toggles apply."""
    tools = live_allow_list()
    return {
        "agent_mode_default": AGENT_MODE_DEFAULT,
        "plan_review_default": PLAN_REVIEW_DEFAULT,
        "max_goal_passes": live_max_passes("goal"),
        "watch_max_passes": live_max_passes("watch"),
        "min_goal_confidence": live_min_confidence(),
        "auto_memory": tools.write_memory,
        "auto_recall": os.getenv("AUTO_RECALL", "true").lower() == "true",
        "enable_web_search": tools.web,
        "enable_arxiv": tools.arxiv,
        "daily_review_enabled": os.getenv("DAILY_REVIEW_ENABLED", "true").lower() == "true",
        "daily_review_hour": DAILY_REVIEW_HOUR,
        "daily_review_max_goals": DAILY_REVIEW_MAX_GOALS,
        "daily_review_catch_up": DAILY_REVIEW_CATCH_UP,
        "enable_self_critique": ENABLE_SELF_CRITIQUE,
    }


@app.get("/api/digest/today")
def digest_today():
    """Today's daily brief, plus review status. Falls back to most recent prior digest."""
    from datetime import date as date_cls

    digest = get_digest()
    previous = None
    if digest is None:
        for item in list_digests(limit=14):
            try:
                d = date_cls.fromisoformat(item["date"])
            except ValueError:
                continue
            if d < date_cls.today():
                previous = get_digest(d)
                break
    status = review_status_payload()
    return {
        "date": (digest or previous or {}).get("date") if (digest or previous) else status.get("last_run_date"),
        "digest": digest,
        "previous_digest": previous,
        "review": status,
    }


@app.get("/api/digests")
def digests_list(limit: int = 30):
    limit = max(1, min(100, limit))
    return {"digests": list_digests(limit=limit)}


@app.get("/api/review/status")
def review_status():
    return review_status_payload()


@app.get("/api/review/plan")
def review_plan_preview():
    """Preview what today's review would run (no execution)."""
    plan = plan_daily_review()
    return plan_to_dict(plan)


@app.post("/api/review/run-now")
def review_run_now(force: bool = True):
    """Start the daily review in the background. Returns 202 while running."""
    from fastapi.responses import JSONResponse

    from sidecar.scheduler import DailyReviewScheduler, get_scheduler

    sched = get_scheduler()
    if sched is None:
        # Scheduler disabled — still offer async via a one-shot helper
        helper = DailyReviewScheduler(
            acquire_lock=RUNS.try_begin_auto,
            release_lock=RUNS.end_auto,
            enabled=True,
        )
        payload, code = helper.start_async(reason="manual", force=force)
    else:
        payload, code = sched.start_async(reason="manual", force=force)

    if code == 409:
        raise HTTPException(
            409,
            f"Another research graph is in flight ({payload.get('error') or 'busy'})",
        )
    return JSONResponse(content=payload, status_code=code)


@app.post("/api/ingest")
def ingest(req: IngestRequest):
    target = Path(req.path).expanduser().resolve()
    if not target.is_dir():
        raise HTTPException(400, f"Not a directory: {target}")
    if req.reset:
        reset_vector_store()
    count = ingest_directory(target)
    # Suggest research angles from filenames (no extra LLM call)
    suggestions: list[str] = []
    try:
        names = sorted(
            {
                p.stem.replace("-", " ").replace("_", " ")
                for p in target.rglob("*")
                if p.is_file() and p.suffix.lower() in {".pdf", ".md", ".txt"}
            }
        )[:8]
        if names:
            a, b = names[0], names[1] if len(names) > 1 else names[0]
            suggestions = [
                f"What are the key ideas in {a}?",
                f"How does {a} relate to {b}?" if b != a else f"Summarize open questions in {a}",
                "What gaps or contradictions appear across my newly added documents?",
            ]
    except OSError:
        pass
    return {
        "ingested_chunks": count,
        "collection_total": collection_count(),
        "path": str(target),
        "suggestions": suggestions,
        "reset": req.reset,
    }


@app.post("/api/ingest/file")
def ingest_single_file(req: IngestFileRequest):
    target = Path(req.path).expanduser().resolve()
    if not target.is_file():
        raise HTTPException(400, f"Not a file: {target}")
    suffix = target.suffix.lower()
    if suffix not in {".pdf", ".txt", ".md"}:
        raise HTTPException(400, f"Unsupported file type: {suffix}")
    count = ingest_file(target)
    return {
        "ingested_chunks": count,
        "collection_total": collection_count(),
        "path": str(target),
    }


def _topic_has_memory(path: Path) -> tuple[int, bool]:
    from second_brain.agent.watch import last_brief_excerpt, list_watches_in_topic
    from second_brain.memory.claims import LIVE_STATUSES, list_claims

    claims = [c for c in list_claims(str(path), status=None) if c.status in LIVE_STATUSES]
    latest = ""
    for w in list_watches_in_topic(path):
        latest = last_brief_excerpt(path, limit=80, watch_id=w.id)
        if latest:
            break
    return len(claims), len(claims) > 0 or bool(latest)


def _watch_item(watch) -> dict:
    from second_brain.agent.watch import topic_name, watch_is_complete, today_brief_exists

    path = Path(watch.project_path)
    return {
        "watch_id": watch.id,
        "name": watch.name or topic_name(path),
        "project_path": str(path.resolve()),
        "topic": path.name,
        "created": watch.created,
        "enabled": bool(watch.enabled),
        "complete": watch_is_complete(watch),
        "has_brief_today": today_brief_exists(path, watch_id=watch.id),
    }


def _watch_payload(path: Path, *, watch_id: str | None = None) -> dict:
    from second_brain.agent.watch import (
        brief_path_for,
        last_brief_excerpt,
        list_briefs,
        load_watch,
        suggested_focus,
        today_brief_exists,
        topic_name,
        watch_is_complete,
    )

    watch = load_watch(path, watch_id)
    latest = last_brief_excerpt(path, limit=20000, watch_id=watch_id)
    bp = brief_path_for(path, watch_id=watch_id)
    claim_count, has_memory = _topic_has_memory(path)
    focus = (watch.focus or "").strip() if watch else ""
    include = (watch.include or "").strip() if watch else ""
    exclude = (watch.exclude or "").strip() if watch else ""
    trusted = (watch.trusted_sources or "").strip() if watch else ""
    return {
        "watch_id": watch.id if watch else (watch_id or ""),
        "name": (watch.name if watch else "") or topic_name(path),
        "project_path": str(path.resolve()),
        "topic": path.name,
        "created": watch.created if watch else "",
        "enabled": bool(watch.enabled) if watch else False,
        "instruction": watch.raw if watch else "",
        "focus": focus,
        "include": include,
        "exclude": exclude,
        "trusted_sources": trusted,
        "steer_log": watch.steer_log if watch else "",
        "complete": bool(watch and watch_is_complete(watch)),
        "suggested_focus": suggested_focus(path, watch),
        "has_brief_today": today_brief_exists(path, watch_id=watch_id),
        "brief_path": str(bp.resolve()) if bp.is_file() else None,
        "latest_brief": latest,
        "briefs": list_briefs(path, watch_id=watch_id),
        "claim_count": claim_count,
        "has_memory": has_memory,
    }


@app.get("/api/watches")
def watches_get(project_path: str | None = None, watch_id: str | None = None):
    """List watches. `watch_id` query is a compat shim for GET /api/watches/{id}."""
    from second_brain.agent.watch import list_watches, list_watches_in_topic, load_watch
    from second_brain.config import DOCUMENTS_DIR

    if watch_id is not None and watch_id != "":
        if not project_path:
            raise HTTPException(400, "project_path required when watch_id is set")
        path = Path(project_path).expanduser()
        if not path.is_dir():
            raise HTTPException(404, f"Not a topic folder: {path}")
        if load_watch(path, watch_id) is None:
            raise HTTPException(404, "Watch not found")
        return _watch_payload(path, watch_id=watch_id)

    if project_path:
        path = Path(project_path).expanduser()
        if not path.is_dir():
            raise HTTPException(404, f"Not a topic folder: {path}")
        watches = list_watches_in_topic(path)
        _, has_memory = _topic_has_memory(path)
        return {"watches": [_watch_item(w) for w in watches], "has_memory": has_memory}

    root = Path(DOCUMENTS_DIR)
    watches = list_watches(root if root.is_dir() else None)
    return {"watches": [_watch_item(w) for w in watches], "has_memory": False}


@app.get("/api/watches/{watch_id}")
def watches_get_one(watch_id: str, project_path: str):
    from second_brain.agent.watch import load_watch

    path = Path(project_path).expanduser()
    if not path.is_dir():
        raise HTTPException(404, f"Not a topic folder: {path}")
    if load_watch(path, watch_id) is None:
        raise HTTPException(404, "Watch not found")
    return _watch_payload(path, watch_id=watch_id)


@app.post("/api/watches")
def watches_create(req: WatchCreateRequest):
    from second_brain.agent.watch import WatchError, create_watch, default_include

    path = Path(req.project_path).expanduser()
    if not path.is_dir():
        raise HTTPException(404, f"Not a topic folder: {path}")
    include = (req.include or "").strip() or default_include(path)
    try:
        watch = create_watch(
            path,
            name=(req.name or "").strip() or "Untitled",
            focus=(req.focus or "").strip() or None,
            include=include,
            enabled=bool(req.enabled) if req.enabled is not None else False,
        )
    except WatchError as e:
        raise HTTPException(400, str(e)) from e
    return _watch_payload(path, watch_id=watch.id)


def _apply_watch_update(req: WatchUpdateRequest):
    from second_brain.agent.watch import WatchError, default_include, update_watch

    path = Path(req.project_path).expanduser()
    if not path.is_dir():
        raise HTTPException(404, f"Not a topic folder: {path}")
    include = req.include
    if include is not None:
        include = include.strip() or default_include(path)
    try:
        watch = update_watch(
            path,
            watch_id=req.watch_id,
            name=req.name,
            focus=(req.focus or "").strip() or None if req.focus is not None else None,
            include=include,
            exclude=req.exclude,
            trusted_sources=req.trusted_sources,
            enabled=req.enabled,
        )
    except WatchError as e:
        raise HTTPException(400, str(e)) from e
    return _watch_payload(path, watch_id=watch.id)


@app.patch("/api/watches")
def watches_update(req: WatchUpdateRequest):
    return _apply_watch_update(req)


@app.post("/api/watches/update")
def watches_update_post(req: WatchUpdateRequest):
    return _apply_watch_update(req)


@app.post("/api/watches/move")
def watches_move(req: WatchMoveRequest):
    from second_brain.agent.watch import WatchError, move_watch

    src = Path(req.project_path).expanduser()
    dest = Path(req.dest_project_path).expanduser()
    if not src.is_dir():
        raise HTTPException(404, f"Not a topic folder: {src}")
    if not dest.is_dir():
        raise HTTPException(404, f"Not a topic folder: {dest}")
    try:
        watch = move_watch(src, dest, watch_id=req.watch_id)
    except WatchError as e:
        raise HTTPException(400, str(e)) from e
    return _watch_payload(dest, watch_id=watch.id)


@app.post("/api/watches/delete")
def watches_delete(req: WatchDeleteRequest):
    from second_brain.agent.watch import WatchError, delete_watch

    path = Path(req.project_path).expanduser()
    if not path.is_dir():
        raise HTTPException(404, f"Not a topic folder: {path}")
    try:
        delete_watch(path, watch_id=req.watch_id)
    except WatchError as e:
        raise HTTPException(400, str(e)) from e
    return {"ok": True}


@app.post("/api/watches/promote")
def watches_promote(req: WatchPromoteRequest):
    from second_brain.agent.watch import WatchError, promote_legacy_watch

    path = Path(req.project_path).expanduser()
    if not path.is_dir():
        raise HTTPException(404, f"Not a topic folder: {path}")
    try:
        watch = promote_legacy_watch(path, name=req.name)
    except WatchError as e:
        raise HTTPException(400, str(e)) from e
    return _watch_payload(path, watch_id=watch.id)


@app.post("/api/watches/run")
def watches_run(req: WatchRunRequest):
    from second_brain.agent.watch import WatchError, run_watch

    _require_embeddings_ready()
    token = _reserve_auto(req.project_path)
    try:
        result = run_watch(
            req.project_path,
            watch_id=req.watch_id,
            force=req.force,
            session_id=req.session_id,
        )
    except WatchError as e:
        raise HTTPException(400, str(e)) from e
    finally:
        RUNS.end_auto(token)
    return _research_payload(result)


@app.post("/api/watches/stream")
def watches_stream(req: WatchRunRequest):
    from second_brain.agent.watch import WatchError, stream_watch

    _require_embeddings_ready()
    token = _reserve_auto(req.project_path)

    def event_gen():
        try:
            yield from _sse_from_stream(
                stream_watch(
                    req.project_path,
                    watch_id=req.watch_id,
                    force=req.force,
                    session_id=req.session_id,
                    max_passes=req.max_passes,
                ),
                display_query="Watch",
            )
        except WatchError as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            RUNS.end_auto(token)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/watches/steer")
def watches_steer(req: WatchSteerRequest):
    from second_brain.agent.watch import WatchError, append_steer

    note = (req.note or "").strip()
    if not note:
        raise HTTPException(400, "Steer note required")
    try:
        path = append_steer(req.project_path, note, watch_id=req.watch_id)
    except WatchError as e:
        raise HTTPException(400, str(e)) from e
    return {"ok": True, "path": str(path)}


def _cloud_sync_payload(project_path: str, watch_id: str | None) -> dict:
    from second_brain.agent.watch import last_brief_excerpt, load_watch
    from second_brain.memory.learning import read_project_memory_tail

    path = Path(project_path).expanduser()
    watch = load_watch(path, watch_id)
    if watch is None:
        raise HTTPException(404, "Watch not found.")
    return {
        "watch_id": watch.id,
        "topic": path.name,
        "name": watch.name or path.name,
        "focus": watch.focus or "",
        "include": watch.include or "",
        "exclude": watch.exclude or "",
        "trusted_sources": watch.trusted_sources or "",
        "enabled": bool(watch.enabled),
        "cadence": watch.cadence or "weekdays",
        "hour": int(watch.hour or 9),
        "timezone": "Asia/Singapore",
        "last_brief_excerpt": last_brief_excerpt(path, watch_id=watch.id, limit=900),
        "project_tail": read_project_memory_tail(str(path), max_lines=16),
    }


@app.post("/api/cloud-watch/sync")
def cloud_watch_sync(req: CloudWatchSyncRequest):
    """Push one Watch definition to the Cloud Watch service (no-op if not configured)."""
    from second_brain.agent.cloud_watch_sync import cloud_watch_configured, sync_watch_to_cloud

    if not cloud_watch_configured():
        return {"ok": False, "skipped": True, "reason": "not_configured"}
    payload = _cloud_sync_payload(req.project_path, req.watch_id)
    try:
        remote = sync_watch_to_cloud(payload)
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from e
    return {"ok": True, "watch": remote}


@app.post("/api/cloud-watch/pull")
def cloud_watch_pull():
    """Pull pending cloud briefs into the local vault and ack them."""
    from second_brain.agent.cloud_watch_sync import cloud_watch_configured, pull_pending_briefs

    if not cloud_watch_configured():
        return {"ok": False, "skipped": True, "reason": "not_configured", "count": 0, "written": []}
    try:
        result = pull_pending_briefs()
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from e
    return {"ok": True, **result}


@app.get("/api/cloud-watch/status")
def cloud_watch_status():
    from second_brain.agent.cloud_watch_sync import (
        cloud_watch_config,
        cloud_watch_configured,
        cloud_watch_service_available,
        me,
    )

    url, token = cloud_watch_config()
    available = cloud_watch_service_available()
    signed_in = bool(available and token)
    out: dict = {
        "available": available,
        "configured": cloud_watch_configured(),
        "signed_in": signed_in,
        "url": "" if available else "",  # never expose URL to the client UI
        "user": None,
    }
    if signed_in:
        try:
            out["user"] = me()
        except Exception:
            out["user"] = None
            out["signed_in"] = False
            out["configured"] = False
    return out


def _cloud_watch_push_local_llm_best_effort() -> dict | None:
    """After sign-in / Models save: copy local LLM key to Cloud Watch if possible."""
    from second_brain.agent.cloud_watch_sync import push_local_llm_to_cloud

    try:
        return push_local_llm_to_cloud()
    except RuntimeError:
        return None


@app.post("/api/cloud-watch/register")
def cloud_watch_register(req: CloudWatchAuthRequest):
    from second_brain.agent.cloud_watch_sync import cloud_watch_service_available, register

    if not cloud_watch_service_available():
        raise HTTPException(503, "Cloud Watch is not enabled on this build.")
    try:
        data = register(req.email, req.password)
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from e
    token = str(data.get("token") or "")
    if token:
        _write_env({"CLOUD_WATCH_USER_TOKEN": token})
    user = _cloud_watch_push_local_llm_best_effort() or data.get("user")
    return {"ok": True, "user": user, "token_saved": bool(token)}


@app.post("/api/cloud-watch/login")
def cloud_watch_login(req: CloudWatchAuthRequest):
    from second_brain.agent.cloud_watch_sync import cloud_watch_service_available, login

    if not cloud_watch_service_available():
        raise HTTPException(503, "Cloud Watch is not enabled on this build.")
    try:
        data = login(req.email, req.password)
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from e
    token = str(data.get("token") or "")
    if token:
        _write_env({"CLOUD_WATCH_USER_TOKEN": token})
    user = _cloud_watch_push_local_llm_best_effort() or data.get("user")
    return {"ok": True, "user": user, "token_saved": bool(token)}


@app.post("/api/cloud-watch/logout")
def cloud_watch_logout():
    _write_env({"CLOUD_WATCH_USER_TOKEN": ""})
    return {"ok": True}


@app.put("/api/cloud-watch/llm")
def cloud_watch_llm(req: CloudWatchLlmRequest):
    from second_brain.agent.cloud_watch_sync import cloud_watch_configured, put_llm

    if not cloud_watch_configured():
        raise HTTPException(400, "Sign in to Cloud Watch first.")
    try:
        user = put_llm(
            llm_provider=req.llm_provider,
            llm_api_key=req.llm_api_key,
            llm_model=req.llm_model,
        )
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from e
    return {"ok": True, "user": user}


@app.post("/api/cloud-watch/llm/sync")
def cloud_watch_llm_sync():
    """Push the local Models key to Cloud Watch (same key as Research / Ask)."""
    from second_brain.agent.cloud_watch_sync import push_local_llm_to_cloud

    try:
        user = push_local_llm_to_cloud()
    except RuntimeError as e:
        raise HTTPException(400, str(e)) from e
    return {"ok": True, "user": user}


@app.post("/api/digest")
def digest_notes(req: DigestRequest):
    """Remember: save dump, extract sourced claims, link to existing memory."""
    paths = list(req.paths or [])
    if req.path:
        paths.append(req.path)
    if not (req.text or "").strip() and not paths:
        raise HTTPException(400, "Provide text or a file path to remember.")
    if not (req.project_path or "").strip():
        raise HTTPException(400, "project_path is required to remember notes")

    results: list[dict] = []
    try:
        if (req.text or "").strip():
            results.append(
                digest_and_link(
                    text=req.text,
                    title=req.title,
                    project_path=req.project_path,
                    session_id=req.session_id,
                ).to_dict()
            )
        for p in paths:
            results.append(
                digest_and_link(
                    path=p,
                    title=req.title,
                    project_path=req.project_path,
                    session_id=req.session_id,
                ).to_dict()
            )
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

    if len(results) == 1:
        return results[0]

    created = sum(int(r.get("claims_created") or 0) for r in results)
    revised = sum(int(r.get("claims_revised") or 0) for r in results)
    dropped = sum(int(r.get("claims_dropped") or 0) for r in results)
    return {
        "saved_path": results[-1].get("saved_path") if results else None,
        "content_hash": results[-1].get("content_hash") if results else "",
        "idempotent": all(bool(r.get("idempotent")) for r in results) if results else False,
        "claims_created": created,
        "claims_revised": revised,
        "claims_dropped": dropped,
        "linked_sources": [s for r in results for s in (r.get("linked_sources") or [])],
        "open_questions": [],
        "summary": " · ".join(r.get("summary") or "" for r in results if r.get("summary")),
        "results": results,
    }


@app.get("/api/settings")
def get_settings():
    env = _read_env()
    provider = (env.get("LLM_PROVIDER") or "groq").strip().lower()

    def _has(k: str) -> bool:
        return bool((env.get(k) or "").strip())

    connected = {
        "groq": _has("GROQ_API_KEY"),
        "xai": _has("XAI_API_KEY"),
        "openai": _has("OPENAI_API_KEY"),
        "openrouter": _has("OPENROUTER_API_KEY"),
        "openai_compatible": _has("CUSTOM_API_KEY") and (
            _has("CUSTOM_BASE_URL") or _has("LLM_BASE_URL")
        ),
        "ollama": True,
    }
    # Active provider ready?
    if provider == "ollama":
        llm_configured = True
    elif provider == "groq":
        llm_configured = connected["groq"] or _has("LLM_API_KEY")
    elif provider == "xai":
        llm_configured = connected["xai"] or _has("LLM_API_KEY")
    elif provider == "openai":
        llm_configured = connected["openai"] or _has("LLM_API_KEY")
    elif provider == "openrouter":
        llm_configured = connected["openrouter"] or _has("LLM_API_KEY")
    elif provider == "openai_compatible":
        llm_configured = connected["openai_compatible"] or (
            _has("LLM_API_KEY") and _has("LLM_BASE_URL")
        )
    else:
        llm_configured = _has("LLM_API_KEY")

    public_values = {k: v for k, v in env.items() if k not in _HIDDEN_ENV_KEYS}

    return {
        "values": public_values,
        "tavily_configured": bool(env.get("TAVILY_API_KEY")),
        "notion_configured": bool((env.get("NOTION_API_KEY") or "").strip()),
        "groq_configured": connected["groq"],
        "llm_configured": llm_configured,
        "llm_provider": provider,
        "connected_providers": connected,
    }


@app.put("/api/settings")
def update_settings(req: SettingsUpdate):
    allowed = {
        k: v
        for k, v in req.values.items()
        if k in ENV_KEYS and k not in _HIDDEN_ENV_KEYS
    }
    _write_env(allowed)
    llm_keys = {
        "LLM_PROVIDER",
        "LLM_API_KEY",
        "LLM_MODEL",
        "GROQ_API_KEY",
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
        "XAI_API_KEY",
        "CUSTOM_API_KEY",
    }
    if allowed.keys() & llm_keys:
        _cloud_watch_push_local_llm_best_effort()
    return {"updated": list(allowed.keys()), "values": {
        k: v for k, v in _read_env().items() if k not in _HIDDEN_ENV_KEYS
    }}


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
    _require_embeddings_ready()
    docs = retrieve(req.query, top_k=req.top_k)
    return {"query": req.query, "results": _format_retrieval_results(docs)}


@app.post("/api/vault/related")
def vault_related(req: VaultRelatedRequest):
    if collection_count() == 0:
        return {"query": req.text, "results": []}
    _require_embeddings_ready()
    docs = retrieve(req.text, top_k=req.top_k)
    return {"query": req.text, "results": _format_retrieval_results(docs)}


def main():
    import uvicorn

    port = int(os.getenv("SIDECAR_PORT", "8765"))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()