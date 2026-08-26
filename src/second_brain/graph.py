"""LangGraph multi-agent research workflow with streaming events for the UI."""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable, Iterator
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from second_brain.agents import (
    analyst_node,
    planner_node,
    retriever_node,
    synthesizer_node,
    verifier_node,
)
from second_brain.config import AUTO_MEMORY, AUTO_RECALL, MAX_REVISIONS
from second_brain.memory.learning import persist_research_memory
from second_brain.memory.recall import recall_for_query
from second_brain.state import GraphState

logger = logging.getLogger(__name__)

EventEmitter = Callable[[str, dict[str, Any]], None]

# Map LangGraph node names → UI progress steps
NODE_TO_STEP = {
    "planner": "planning",
    "retriever": "searching",
    "analyst": "analyzing",
    "verifier": "reviewing",
    "synthesizer": "writing",
}

NODE_LABELS = {
    "planner": "Planner",
    "retriever": "Retriever",
    "analyst": "Analyst",
    "verifier": "Verifier",
    "synthesizer": "Synthesizer",
}


def route_after_verifier(state: GraphState) -> Literal["analyst", "synthesizer"]:
    if state.get("critique_approved"):
        return "synthesizer"
    if state.get("revision_count", 0) >= MAX_REVISIONS:
        return "synthesizer"
    return "analyst"


def _stage_detail(node_name: str, node_output: dict, final: dict) -> str:
    if node_name == "planner":
        return (node_output.get("plan") or "")[:280]
    if node_name == "retriever":
        stats = node_output.get("retrieval_stats") or {}
        return ", ".join(f"{k}: {v}" for k, v in stats.items()) or "Retrieved sources"
    if node_name == "verifier":
        rev = node_output.get("revision_count", final.get("revision_count", 0))
        approved = node_output.get("critique_approved")
        if approved:
            source = (node_output.get("critique_structured") or {}).get("source")
            if source == "forced_max_revisions":
                return f"Forced approve after {rev} revision(s)"
            return f"Approved after {rev} revision(s)"
        return f"Revision requested (attempt {rev})"
    if node_name == "analyst":
        rev = final.get("revision_count", 0)
        return "Revising analysis…" if rev else "Drafting analysis…"
    if node_name == "synthesizer":
        return "Writing final report…"
    return ""


def _emit_post_node(
    emit: EventEmitter,
    node_name: str,
    node_output: dict,
    final: dict,
) -> None:
    """Merge-path events: stage / plan / artifact / critique (not agent_status)."""
    step = NODE_TO_STEP.get(node_name, node_name)
    detail = _stage_detail(node_name, node_output, final)
    emit(
        "stage",
        {
            "node": node_name,
            "step": step,
            "detail": detail,
            "label": NODE_LABELS.get(node_name, node_name),
        },
    )

    if node_name == "planner":
        emit(
            "plan",
            {
                "plan": node_output.get("plan") or "",
                "retrieval_queries": node_output.get("retrieval_queries") or [],
            },
        )
    elif node_name == "retriever":
        emit(
            "artifact",
            {
                "kind": "retrieval",
                "retrieval_stats": node_output.get("retrieval_stats") or {},
                "retrieval_log": (node_output.get("retrieval_log") or [])[:20],
            },
        )
    elif node_name == "verifier":
        structured = node_output.get("critique_structured")
        history_delta = node_output.get("critique_history") or []
        emit(
            "critique",
            {
                "critique": node_output.get("critique") or "",
                "critique_approved": bool(node_output.get("critique_approved")),
                "revision_count": node_output.get(
                    "revision_count", final.get("revision_count", 0)
                ),
                "critique_structured": structured,
                "history_entry": history_delta[0] if history_delta else None,
            },
        )
    elif node_name == "analyst":
        analysis = node_output.get("analysis") or ""
        emit(
            "artifact",
            {
                "kind": "analysis",
                "analysis_excerpt": analysis[:400],
                "analysis_char_count": len(analysis),
            },
        )


def _wrap_node(
    name: str,
    fn: Callable[[GraphState], dict],
    emit: EventEmitter | None,
    cancel_flag: threading.Event | None,
) -> Callable[[GraphState], dict]:
    def wrapped(state: GraphState) -> dict:
        if cancel_flag is not None and cancel_flag.is_set():
            raise RuntimeError("Research cancelled")
        step = NODE_TO_STEP.get(name, name)
        if emit:
            # Wrappers own agent_status only
            emit(
                "agent_status",
                {
                    "node": name,
                    "status": "running",
                    "step": step,
                    "label": NODE_LABELS.get(name, name),
                },
            )
        try:
            out = fn(state)
        except Exception as exc:
            if emit:
                emit(
                    "agent_status",
                    {
                        "node": name,
                        "status": "error",
                        "step": step,
                        "label": NODE_LABELS.get(name, name),
                        "detail": str(exc)[:200],
                    },
                )
            raise

        if emit and isinstance(out, dict):
            # Merge path for stage/critique/etc.
            merged = {**state, **out}
            # Special: verifier revise → iterating on analyst path is inferred by UI
            status = "done"
            if name == "verifier" and not out.get("critique_approved"):
                status = "iterating"
            emit(
                "agent_status",
                {
                    "node": name,
                    "status": status,
                    "step": step,
                    "label": NODE_LABELS.get(name, name),
                    "detail": _stage_detail(name, out, merged),
                },
            )
            _emit_post_node(emit, name, out, merged)
        return out

    return wrapped


def build_graph(
    emit: EventEmitter | None = None,
    cancel_flag: threading.Event | None = None,
):
    """Full auto graph: planner → … → synthesizer (CLI / eval / auto stream)."""
    graph = StateGraph(GraphState)

    graph.add_node("planner", _wrap_node("planner", planner_node, emit, cancel_flag))
    graph.add_node("retriever", _wrap_node("retriever", retriever_node, emit, cancel_flag))
    graph.add_node("analyst", _wrap_node("analyst", analyst_node, emit, cancel_flag))
    graph.add_node("verifier", _wrap_node("verifier", verifier_node, emit, cancel_flag))
    graph.add_node(
        "synthesizer", _wrap_node("synthesizer", synthesizer_node, emit, cancel_flag)
    )

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "retriever")
    graph.add_edge("retriever", "analyst")
    graph.add_edge("analyst", "verifier")
    graph.add_conditional_edges(
        "verifier",
        route_after_verifier,
        {
            "analyst": "analyst",
            "synthesizer": "synthesizer",
        },
    )
    graph.add_edge("synthesizer", END)

    return graph.compile()


def build_plan_graph(
    emit: EventEmitter | None = None,
    cancel_flag: threading.Event | None = None,
):
    """HITL plan phase: START → planner → END."""
    graph = StateGraph(GraphState)
    graph.add_node("planner", _wrap_node("planner", planner_node, emit, cancel_flag))
    graph.add_edge(START, "planner")
    graph.add_edge("planner", END)
    return graph.compile()


def build_execute_graph(
    emit: EventEmitter | None = None,
    cancel_flag: threading.Event | None = None,
):
    """HITL execute phase: START → retriever → analyst ⇄ verifier → synthesizer."""
    graph = StateGraph(GraphState)
    graph.add_node("retriever", _wrap_node("retriever", retriever_node, emit, cancel_flag))
    graph.add_node("analyst", _wrap_node("analyst", analyst_node, emit, cancel_flag))
    graph.add_node("verifier", _wrap_node("verifier", verifier_node, emit, cancel_flag))
    graph.add_node(
        "synthesizer", _wrap_node("synthesizer", synthesizer_node, emit, cancel_flag)
    )
    graph.add_edge(START, "retriever")
    graph.add_edge("retriever", "analyst")
    graph.add_edge("analyst", "verifier")
    graph.add_conditional_edges(
        "verifier",
        route_after_verifier,
        {
            "analyst": "analyst",
            "synthesizer": "synthesizer",
        },
    )
    graph.add_edge("synthesizer", END)
    return graph.compile()


def _initial_state(
    query: str,
    retrieval_scope: str = "hybrid",
    project_path: str | None = None,
    session_id: str | None = None,
    memory_context: str = "",
    memory_recalled_count: int = 0,
    also_project_paths: list[str] | None = None,
) -> GraphState:
    from second_brain.scope import normalize_scope

    return {
        "query": query,
        "messages": [],
        "plan": "",
        "retrieval_queries": [],
        "retrieval_stats": {},
        "retrieval_log": [],
        "retrieved_docs": [],
        "analysis": "",
        "critique": "",
        "critique_approved": False,
        "revision_count": 0,
        "report": "",
        "critique_structured": None,
        "critique_history": [],
        "analysis_history": [],
        "retrieval_scope": normalize_scope(retrieval_scope),
        "project_path": project_path,
        "also_project_paths": list(also_project_paths or []),
        "session_id": session_id,
        "memory_context": memory_context or "",
        "memory_recalled_count": memory_recalled_count,
        "confidence": 0.0,
        "confidence_reasons": [],
        "open_questions": [],
        "learning_path": None,
        "report_path": None,
        "citation_issues": [],
    }


def _load_memory(
    query: str,
    project_path: str | None = None,
    prior_context: str | None = None,
    session_id: str | None = None,
    also_project_paths: list[str] | None = None,
) -> tuple[str, int, list[str]]:
    if not AUTO_RECALL:
        if prior_context and prior_context.strip():
            return prior_context.strip()[:3500], 0, []
        return "", 0, []
    ctx = recall_for_query(
        query,
        project_path=project_path,
        session_id=session_id,
        prior_context=prior_context,
        also_project_paths=also_project_paths,
    )
    return ctx.text, ctx.recalled_count, ctx.sources


def _finalize_memory(final: dict) -> dict:
    """Persist learnings after a successful research run; enrich state dict."""
    if not AUTO_MEMORY:
        return final
    if not (final.get("report") or "").strip():
        return final
    project_path = (final.get("project_path") or "").strip() or None
    try:
        meta = persist_research_memory(
            final,
            project_path=project_path,
            session_id=final.get("session_id"),
            write_report=True,
            ingest=True,
            origin=str(final.get("claim_origin") or "research"),
        )
        return {**final, **meta}
    except Exception:
        logger.exception("persist_research_memory failed")
        return final


def seed_execute_state(
    *,
    composed_query: str,
    plan: str,
    retrieval_queries: list[str],
    retrieval_scope: str = "hybrid",
    project_path: str | None = None,
    session_id: str | None = None,
    memory_context: str = "",
    memory_recalled_count: int = 0,
    also_project_paths: list[str] | None = None,
) -> GraphState:
    """Full GraphState for execute graph (user-approved plan + queries)."""
    state = _initial_state(
        composed_query,
        retrieval_scope=retrieval_scope,
        project_path=project_path,
        session_id=session_id,
        memory_context=memory_context,
        memory_recalled_count=memory_recalled_count,
        also_project_paths=also_project_paths,
    )
    state["plan"] = plan.strip()
    state["retrieval_queries"] = [q.strip() for q in retrieval_queries if q.strip()]
    return state


def run_plan(
    query: str,
    retrieval_scope: str = "hybrid",
    project_path: str | None = None,
    prior_context: str | None = None,
    session_id: str | None = None,
    also_project_paths: list[str] | None = None,
) -> GraphState:
    graph = build_plan_graph()
    mem_text, mem_n, _ = _load_memory(
        query, project_path, prior_context, session_id, also_project_paths
    )
    logger.info(
        "Running plan-only workflow for: %s (scope=%s project=%s memory=%d session=%s)",
        query,
        retrieval_scope,
        project_path,
        mem_n,
        session_id,
    )
    return graph.invoke(
        _initial_state(
            query,
            retrieval_scope=retrieval_scope,
            project_path=project_path,
            session_id=session_id,
            memory_context=mem_text,
            memory_recalled_count=mem_n,
            also_project_paths=also_project_paths,
        )
    )


def run_research(
    query: str,
    retrieval_scope: str = "hybrid",
    project_path: str | None = None,
    prior_context: str | None = None,
    persist_memory: bool = True,
    session_id: str | None = None,
    claim_origin: str = "research",
    also_project_paths: list[str] | None = None,
) -> GraphState:
    graph = build_graph()
    mem_text, mem_n, _ = _load_memory(
        query, project_path, prior_context, session_id, also_project_paths
    )
    logger.info(
        "Starting research workflow for: %s (scope=%s project=%s memory=%d session=%s)",
        query,
        retrieval_scope,
        project_path,
        mem_n,
        session_id,
    )
    final = graph.invoke(
        _initial_state(
            query,
            retrieval_scope=retrieval_scope,
            project_path=project_path,
            session_id=session_id,
            memory_context=mem_text,
            memory_recalled_count=mem_n,
            also_project_paths=also_project_paths,
        )
    )
    final = dict(final)
    final["claim_origin"] = claim_origin
    if persist_memory:
        final = _finalize_memory(final)
    return final  # type: ignore[return-value]


def stream_research(
    query: str,
    cancel_flag: threading.Event | None = None,
    retrieval_scope: str = "hybrid",
    project_path: str | None = None,
    prior_context: str | None = None,
    persist_memory: bool = True,
    session_id: str | None = None,
    claim_origin: str = "research",
    also_project_paths: list[str] | None = None,
) -> Iterator[tuple[str, Any]]:
    """Yield events for full auto multi-agent run."""
    events: queue.Queue[tuple[str, Any] | None] = queue.Queue()

    def emit(kind: str, payload: dict[str, Any]) -> None:
        events.put((kind, payload))

    def worker() -> None:
        try:
            mem_text, mem_n, mem_sources = _load_memory(
                query, project_path, prior_context, session_id, also_project_paths
            )
            emit(
                "memory",
                {
                    "phase": "recalled",
                    "recalled_count": mem_n,
                    "sources": mem_sources[:12],
                    "detail": f"Recalled {mem_n} prior finding(s)" if mem_n else "No prior memory",
                },
            )
            graph = build_graph(emit=emit, cancel_flag=cancel_flag)
            logger.info(
                "Streaming research workflow for: %s (scope=%s project=%s session=%s)",
                query,
                retrieval_scope,
                project_path,
                session_id,
            )
            final = graph.invoke(
                _initial_state(
                    query,
                    retrieval_scope=retrieval_scope,
                    project_path=project_path,
                    session_id=session_id,
                    memory_context=mem_text,
                    memory_recalled_count=mem_n,
                    also_project_paths=also_project_paths,
                )
            )
            final = dict(final)
            final["claim_origin"] = claim_origin
            if persist_memory:
                final = _finalize_memory(final)
                emit(
                    "memory",
                    {
                        "phase": "written",
                        "learning_path": final.get("learning_path"),
                        "report_path": final.get("report_path"),
                        "confidence": final.get("confidence"),
                        "detail": final.get("memory_detail")
                        or (
                            "Saved learning card + report to memory"
                            if final.get("memory_written")
                            else "Memory write skipped"
                        ),
                    },
                )
            events.put(("complete", final))
        except Exception as exc:
            logger.exception("stream_research failed")
            events.put(("error", {"message": str(exc)}))
        finally:
            events.put(None)

    thread = threading.Thread(target=worker, daemon=True, name="research-stream")
    thread.start()
    while True:
        item = events.get()
        if item is None:
            break
        yield item
    thread.join(timeout=1.0)


def stream_execute(
    *,
    composed_query: str,
    plan: str,
    retrieval_queries: list[str],
    cancel_flag: threading.Event | None = None,
    retrieval_scope: str = "hybrid",
    project_path: str | None = None,
    session_id: str | None = None,
    persist_memory: bool = True,
    also_project_paths: list[str] | None = None,
) -> Iterator[tuple[str, Any]]:
    """Yield events for execute graph (no planner)."""
    seed = seed_execute_state(
        composed_query=composed_query,
        plan=plan,
        retrieval_queries=retrieval_queries,
        retrieval_scope=retrieval_scope,
        project_path=project_path,
        session_id=session_id,
        also_project_paths=also_project_paths,
    )
    if not seed["retrieval_queries"]:
        yield ("error", {"message": "retrieval_queries must be non-empty"})
        return
    if not seed["plan"]:
        yield ("error", {"message": "plan must be non-empty"})
        return

    events: queue.Queue[tuple[str, Any] | None] = queue.Queue()

    def emit(kind: str, payload: dict[str, Any]) -> None:
        events.put((kind, payload))

    def worker() -> None:
        try:
            graph = build_execute_graph(emit=emit, cancel_flag=cancel_flag)
            logger.info("Streaming execute workflow for: %s", composed_query[:80])
            # Mark planner done for dashboard
            emit(
                "agent_status",
                {
                    "node": "planner",
                    "status": "done",
                    "step": "planning",
                    "label": "Planner",
                    "detail": "Plan approved",
                },
            )
            final = graph.invoke(seed)
            # Ensure plan fields preserved
            final = {
                **final,
                "plan": seed["plan"],
                "retrieval_queries": seed["retrieval_queries"],
                "query": composed_query,
                "session_id": session_id or seed.get("session_id"),
            }
            if persist_memory:
                final = _finalize_memory(final)
                emit(
                    "memory",
                    {
                        "phase": "written",
                        "learning_path": final.get("learning_path"),
                        "report_path": final.get("report_path"),
                        "confidence": final.get("confidence"),
                        "detail": final.get("memory_detail")
                        or (
                            "Saved learning card + report to memory"
                            if final.get("memory_written")
                            else "Memory write skipped"
                        ),
                    },
                )
            events.put(("complete", final))
        except Exception as exc:
            logger.exception("stream_execute failed")
            events.put(("error", {"message": str(exc)}))
        finally:
            events.put(None)

    thread = threading.Thread(target=worker, daemon=True, name="research-execute")
    thread.start()
    while True:
        item = events.get()
        if item is None:
            break
        yield item
    thread.join(timeout=1.0)
