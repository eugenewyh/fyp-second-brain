"""Auto-recall of past learnings, claims, and research for the planner."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from second_brain.config import RETRIEVAL_TOP_K
from second_brain.memory.learning import (
    agent_memory_path,
    project_memory_path,
    _safe_session_id,
)
from second_brain.memory.retriever import retrieve

logger = logging.getLogger(__name__)

MAX_MEMORY_CHARS = 3500


@dataclass
class MemoryContext:
    text: str = ""
    recalled_count: int = 0
    sources: list[str] = field(default_factory=list)
    claim_count: int = 0
    has_chat_memory: bool = False
    contested_claims: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "recalled_count": self.recalled_count,
            "sources": self.sources,
            "claim_count": self.claim_count,
            "has_chat_memory": self.has_chat_memory,
            "contested_claims": self.contested_claims,
        }


def memory_is_useful(
    ctx: MemoryContext,
    *,
    has_ephemeral: bool = False,
    on_topic: bool | None = None,
) -> bool:
    """True when Ask may answer from notes that match this question."""
    if has_ephemeral:
        return True
    if on_topic is False:
        return False
    return ctx.claim_count > 0


def _prefer_agent_memory(docs: list, *, session_id: str | None = None) -> list:
    """Boost session → claims → project memory → learnings ahead of other vault docs."""
    sid = (_safe_session_id(session_id) or "").lower()
    session_hits: list = []
    claim_hits: list = []
    project_hits: list = []
    preferred: list = []
    rest: list = []
    for d in docs:
        meta = d.metadata or {}
        source = str(meta.get("source", "")).lower()
        path = str(meta.get("source_path", "")).lower()
        doc_type = str(meta.get("doc_type", "")).lower()
        meta_sid = str(meta.get("session_id", "")).lower()

        if sid and (sid in path or (meta_sid and meta_sid == sid)):
            session_hits.append(d)
            continue
        if doc_type == "claim" or "/memory/claims/" in path:
            claim_hits.append(d)
            continue
        if (
            "/memory/project.md" in path
            or path.endswith("memory/project.md")
            or doc_type in {"agent-memory", "project-memory"}
        ):
            if "agents/" not in path and "/claims/" not in path:
                project_hits.append(d)
                continue
        if (
            doc_type in {"learning", "research-report", "agent-memory"}
            or "/memory/learnings/" in path
            or "/memory/agents/" in path
            or "/research/" in path
            or (source.startswith("20") and "research" in path)
        ):
            preferred.append(d)
        else:
            rest.append(d)
    return session_hits + claim_hits + project_hits + preferred + rest


def _read_file_excerpt(path: Path, *, limit: int = 900) -> str:
    try:
        if not path.is_file():
            return ""
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            text = parts[2]
    text = text.strip()
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return text


def _append_block(
    blocks: list[str],
    sources: list[str],
    block: str,
    source: str,
    budget: int,
) -> int:
    if not block or len(block) > budget:
        return budget
    blocks.append(block)
    sources.append(source)
    return budget - len(block) - 2


def _topic_claim_and_project_blocks(
    query: str,
    project_path: str | None,
    *,
    label: str,
    blocks: list[str],
    sources: list[str],
    budget: int,
    contested_out: list[dict[str, Any]] | None = None,
) -> tuple[int, int]:
    """Append claims + project.md for one folder. Returns (budget, claim_count)."""
    claim_count = 0
    try:
        from second_brain.memory.claims import claims_matching_query

        matched = claims_matching_query(query, project_path, limit=5)
        if matched:
            claim_count = len(matched)
            lines = []
            for c in matched:
                slug = c.slug or "claim"
                if (c.status or "").lower() == "contested":
                    lines.append(f"- [[{slug}]] (contested) {c.claim}")
                    if contested_out is not None:
                        contested_out.append(
                            {
                                "id": c.id,
                                "claim": c.claim,
                                "origin": c.origin,
                                "status": c.status,
                                "slug": c.slug,
                            }
                        )
                else:
                    lines.append(f"- [[{slug}]] ({c.confidence:.0%}) {c.claim}")
                if c.path:
                    sources.append(c.path)
            budget = _append_block(
                blocks, sources, f"[{label} claims]\n" + "\n".join(lines), "claims", budget
            )
    except Exception:
        logger.debug("Claim recall skipped", exc_info=True)

    pm = project_memory_path(project_path)
    excerpt = _read_file_excerpt(pm, limit=900)
    if excerpt:
        budget = _append_block(
            blocks,
            sources,
            f"[{label} memory]\n{excerpt}",
            str(pm.resolve()),
            budget,
        )
    return budget, claim_count


def recall_for_query(
    query: str,
    *,
    project_path: str | None = None,
    session_id: str | None = None,
    top_k: int = 6,
    prior_context: str | None = None,
    also_project_paths: list[str] | None = None,
) -> MemoryContext:
    """Retrieve compact prior understanding for planner injection.

    Preference: chat memory → matching claims → project.md → Chroma vault hits.
    """
    if not query or not query.strip():
        return MemoryContext()

    blocks: list[str] = []
    sources: list[str] = []
    budget = MAX_MEMORY_CHARS
    has_chat_memory = False
    claim_count = 0
    contested_claims: list[dict[str, Any]] = []

    if prior_context and prior_context.strip():
        pc = prior_context.strip()[:1500]
        budget = _append_block(
            blocks, sources, f"[User-provided prior context]\n{pc}", "prior_context", budget
        )

    sid = _safe_session_id(session_id)
    if sid:
        am = agent_memory_path(project_path, sid)
        excerpt = _read_file_excerpt(am, limit=700)
        if excerpt:
            has_chat_memory = True
            budget = _append_block(
                blocks,
                sources,
                f"[Chat memory]\n{excerpt}",
                str(am.resolve()),
                budget,
            )

    # Active claims + project.md for the bound topic, then any explicit extra topics
    budget, n = _topic_claim_and_project_blocks(
        query,
        project_path,
        label="Project",
        blocks=blocks,
        sources=sources,
        budget=budget,
        contested_out=contested_claims,
    )
    claim_count += n
    extra_paths = [
        p
        for p in (also_project_paths or [])
        if p and str(p).strip() and str(p).strip() != str(project_path or "").strip()
    ]
    for extra in extra_paths:
        label = Path(extra).name or "Also"
        budget, n = _topic_claim_and_project_blocks(
            query,
            extra,
            label=f"Also {label}",
            blocks=blocks,
            sources=sources,
            budget=budget,
            contested_out=contested_claims,
        )
        claim_count += n

    try:
        docs = retrieve(
            query,
            top_k=max(top_k, RETRIEVAL_TOP_K),
            project_path=project_path,
            also_project_paths=extra_paths or None,
        )
    except Exception:
        logger.exception("Memory recall failed")
        docs = []

    docs = _prefer_agent_memory(docs, session_id=sid)[:top_k]

    for i, doc in enumerate(docs, start=1):
        source = doc.metadata.get("source", "unknown")
        path = doc.metadata.get("source_path", "")
        if path and any(str(path) == s for s in sources):
            continue
        excerpt = (doc.page_content or "").strip().replace("\n", " ")
        if len(excerpt) > 400:
            excerpt = excerpt[:400] + "…"
        block = f"[{i}] {source}: {excerpt}"
        if len(block) > budget:
            break
        blocks.append(block)
        sources.append(str(path or source))
        budget -= len(block) + 2

    text = ""
    if blocks:
        text = (
            "Prior knowledge from the user's second brain and past agent learnings "
            "(use to avoid repeating work; deepen and connect):\n" + "\n".join(blocks)
        )

    logger.info("Recalled %d memory snippet(s) for query (session=%s)", len(sources), sid)
    return MemoryContext(
        text=text,
        recalled_count=len(sources),
        sources=sources,
        claim_count=claim_count,
        has_chat_memory=has_chat_memory,
        contested_claims=contested_claims,
    )
