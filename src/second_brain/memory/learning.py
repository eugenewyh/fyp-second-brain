"""Agent learning cards — persistent memory written after research runs."""

from __future__ import annotations

import logging
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from langchain_core.documents import Document

from second_brain.config import DOCUMENTS_DIR  # noqa: F401 — tests patch this; writes never fall back here
from second_brain.ingestion.pipeline import ingest_file
from second_brain.memory.chroma_store import upsert_documents
from second_brain.memory.locks import ingest_lock

logger = logging.getLogger(__name__)

_OPEN_Q = re.compile(
    r"(?im)^(?:[-*•]|\d+[.)])\s*(.+?(?:\?|unclear|unknown|not (?:found|covered|available)).*)$"
)
_SUMMARY_HEADINGS = r"(?:In short|Executive Summary)"
_FINDINGS_HEADINGS = r"(?:What we found|Key Findings)"
_GAPS_HEADINGS = r"(?:What'?s missing|Identified Gaps)"
_GAP_SECTION = re.compile(
    rf"(?is)##\s*(?:{_GAPS_HEADINGS})\s*\n(.*?)(?=\n##\s|\Z)"
)


def _section_body(report: str, headings: str) -> str:
    m = re.search(rf"(?is)##\s*(?:{headings})\s*\n(.*?)(?=\n##\s|\Z)", report or "")
    return m.group(1) if m else ""


def _slugify(text: str, max_len: int = 48) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s or "learning")[:max_len]


def extract_open_questions(report: str, limit: int = 5) -> list[str]:
    """Pull open questions / gaps from the Identified Gaps section or bullets."""
    if not report:
        return []
    section = ""
    m = _GAP_SECTION.search(report)
    if m:
        section = m.group(1)
    else:
        section = report
    found: list[str] = []
    for line in section.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        bullet = re.sub(r"^[-*•]\s+|\d+[.)]\s+", "", line).strip()
        if not bullet:
            continue
        if "?" in bullet or re.search(
            r"\b(gap|missing|unclear|not (found|covered|available)|unknown|limited)\b",
            bullet,
            re.I,
        ):
            found.append(bullet[:240])
        if len(found) >= limit:
            break
    return found


def extract_key_findings(report: str, limit: int = 5) -> list[str]:
    body = _section_body(report, _FINDINGS_HEADINGS)
    if not body:
        return []
    out: list[str] = []
    for line in body.splitlines():
        line = line.strip()
        bullet = re.sub(r"^[-*•]\s+|\d+[.)]\s+", "", line).strip()
        if len(bullet) > 12:
            out.append(bullet[:240])
        if len(out) >= limit:
            break
    return out


def extract_executive_summary(report: str) -> str:
    body = _section_body(report, _SUMMARY_HEADINGS)
    if body:
        return re.sub(r"\s+", " ", body).strip()[:600]
    # Fallback: first non-empty paragraph
    for para in (report or "").split("\n\n"):
        p = para.strip()
        if p and not p.startswith("#"):
            return re.sub(r"\s+", " ", p)[:600]
    return ""


def compute_confidence(state: dict[str, Any]) -> tuple[float, list[str]]:
    """Heuristic confidence 0–1 from retrieval, critique, and revisions."""
    reasons: list[str] = []
    score = 0.55

    stats = state.get("retrieval_stats") or {}
    total_docs = sum(int(v) for v in stats.values() if isinstance(v, (int, float)))
    if total_docs >= 8:
        score += 0.15
        reasons.append(f"Strong retrieval ({total_docs} sources)")
    elif total_docs >= 3:
        score += 0.08
        reasons.append(f"Adequate retrieval ({total_docs} sources)")
    elif total_docs == 0:
        score -= 0.25
        reasons.append("No sources retrieved")
    else:
        score -= 0.08
        reasons.append(f"Thin retrieval ({total_docs} sources)")

    structured = state.get("critique_structured") or {}
    if isinstance(structured, dict):
        if structured.get("grounding_passed") is False:
            score -= 0.15
            reasons.append("Grounding checks failed")
        elif structured.get("grounding_passed") is True:
            score += 0.08
            reasons.append("Grounding passed")
        verdict = structured.get("verdict")
        if verdict == "approved" and structured.get("source") != "forced_max_revisions":
            score += 0.1
            reasons.append("Verifier approved")
        elif structured.get("source") == "forced_max_revisions":
            score -= 0.12
            reasons.append("Forced approve after max revisions")
        issues = structured.get("issues") or []
        blocking = sum(
            1
            for i in issues
            if isinstance(i, dict) and i.get("severity") in ("blocking", "major")
        )
        if blocking:
            score -= min(0.15, 0.05 * blocking)
            reasons.append(f"{blocking} major/blocking critique issue(s)")

    rev = int(state.get("revision_count") or 0)
    if rev == 0 and state.get("critique_approved"):
        score += 0.05
        reasons.append("Approved on first pass")
    elif rev >= 2:
        score -= 0.05
        reasons.append(f"{rev} revision cycle(s)")

    report = state.get("report") or ""
    gaps = extract_open_questions(report)
    if len(gaps) >= 3:
        score -= 0.08
        reasons.append("Many identified gaps")
    elif len(gaps) == 0 and total_docs > 0:
        score += 0.03

    score = max(0.05, min(0.98, round(score, 2)))
    if not reasons:
        reasons.append("Default baseline confidence")
    return score, reasons[:6]


@dataclass
class LearningCard:
    id: str
    query: str
    summary: str
    key_findings: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    source_stats: dict[str, int] = field(default_factory=dict)
    confidence: float = 0.5
    confidence_reasons: list[str] = field(default_factory=list)
    critique_summary: str = ""
    project_path: str | None = None
    session_id: str | None = None
    report_path: str | None = None
    learning_path: str | None = None
    ts: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Never write here — a missing topic must not pollute DOCUMENTS_DIR/memory.
_UNBOUND_TOPIC = Path("/nonexistent/nous-unbound-topic")
SKIP_NO_TOPIC_DETAIL = "No topic bound — nothing filed"


def has_topic_path(project_path: str | None) -> bool:
    return bool(project_path and str(project_path).strip())


def learnings_dir(project_path: str | None = None) -> Path:
    return project_memory_root(project_path) / "learnings"


def research_dir(project_path: str | None = None) -> Path:
    if has_topic_path(project_path):
        return Path(str(project_path).strip()).expanduser() / "research"
    return _UNBOUND_TOPIC / "research"


def _safe_session_id(session_id: str | None) -> str | None:
    if not session_id or not str(session_id).strip():
        return None
    # UUID-safe folder name only
    sid = re.sub(r"[^a-zA-Z0-9_-]+", "", str(session_id).strip())
    return sid[:64] or None


def project_memory_root(project_path: str | None = None) -> Path:
    if has_topic_path(project_path):
        return Path(str(project_path).strip()).expanduser() / "memory"
    return _UNBOUND_TOPIC / "memory"


def agent_session_dir(project_path: str | None, session_id: str) -> Path:
    sid = _safe_session_id(session_id)
    if not sid:
        raise ValueError("session_id required")
    return project_memory_root(project_path) / "agents" / sid


def agent_learnings_dir(project_path: str | None, session_id: str) -> Path:
    return agent_session_dir(project_path, session_id) / "learnings"


def agent_memory_path(project_path: str | None, session_id: str) -> Path:
    return agent_session_dir(project_path, session_id) / "memory.md"


def project_memory_path(project_path: str | None = None) -> Path:
    return project_memory_root(project_path) / "project.md"


def project_log_path(project_path: str | None = None) -> Path:
    return project_memory_root(project_path) / "project-log.md"


def _personal_source_wikilinks(state: dict[str, Any], *, limit: int = 6) -> list[str]:
    """Basenames of personal vault sources suitable for [[wikilinks]]."""
    docs = state.get("retrieved_docs") or []
    out: list[str] = []
    seen: set[str] = set()
    for d in docs:
        if not isinstance(d, dict):
            continue
        meta = d.get("metadata") or {}
        if not isinstance(meta, dict):
            continue
        stype = str(meta.get("source_type") or meta.get("doc_type") or "").lower()
        # Prefer personal / vault docs; skip pure web/arxiv when tagged
        if stype in {"web", "arxiv", "tavily"}:
            continue
        raw = (
            meta.get("source")
            or meta.get("source_path")
            or meta.get("file_path")
            or ""
        )
        name = Path(str(raw)).name
        if not name:
            continue
        stem = re.sub(r"\.(md|pdf|txt)$", "", name, flags=re.I)
        if not stem or stem in seen:
            continue
        # Skip auto-generated research dumps as link targets (link report separately)
        if stem.startswith("20") and "-learning" in stem.lower():
            continue
        seen.add(stem)
        out.append(stem)
        if len(out) >= limit:
            break
    return out


def _report_wikilink(report_path: str | None) -> str | None:
    if not report_path:
        return None
    stem = Path(report_path).stem
    return stem or None


def _card_markdown(card: LearningCard, *, related_links: list[str] | None = None) -> str:
    findings = "\n".join(f"- {f}" for f in card.key_findings) or "- (none extracted)"
    questions = "\n".join(f"- {q}" for q in card.open_questions) or "- (none)"
    reasons = "\n".join(f"- {r}" for r in card.confidence_reasons) or "- (n/a)"
    stats = ", ".join(f"{k}: {v}" for k, v in (card.source_stats or {}).items()) or "none"
    related = related_links or []
    related_block = (
        "\n".join(f"- [[{link}]]" for link in related) if related else "- (none)"
    )
    session_line = f'session_id: "{card.session_id or ""}"'
    return "\n".join(
        [
            "---",
            f"id: {card.id}",
            f'date: {card.ts[:10] if card.ts else ""}',
            f'query: "{card.query.replace(chr(34), chr(92) + chr(34))}"',
            f"type: learning",
            f"confidence: {card.confidence}",
            f'sources: "{stats}"',
            f'tags: ["learning", "agent-memory", "auto-generated"]',
            f'report_path: "{(card.report_path or "").replace(chr(34), "")}"',
            session_line,
            "---",
            "",
            f"# Learning: {card.query}",
            "",
            "## Summary",
            card.summary or "_(empty)_",
            "",
            "## Key findings",
            findings,
            "",
            "## Open questions",
            questions,
            "",
            "## Related",
            related_block,
            "",
            "## Confidence",
            f"**{card.confidence:.0%}**",
            reasons,
            "",
            "## Critique",
            card.critique_summary or "_(none)_",
            "",
        ]
    )


def _append_memory_bullet(path: Path, *, title: str, bullet: str, ingest: bool = True) -> None:
    """Append a dated bullet under a rolling memory markdown file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).date().isoformat()
    line = f"- ({day}) {bullet.strip()}"
    if path.is_file():
        existing = path.read_text(encoding="utf-8")
        if bullet.strip() and bullet.strip() in existing:
            return
        if not existing.endswith("\n"):
            existing += "\n"
        path.write_text(existing + line + "\n", encoding="utf-8")
    else:
        body = "\n".join(
            [
                "---",
                f'type: agent-memory',
                f'title: "{title.replace(chr(34), "")}"',
                "---",
                "",
                f"# {title}",
                "",
                line,
                "",
            ]
        )
        path.write_text(body, encoding="utf-8")
    if ingest:
        try:
            ingest_file(path)
        except Exception:
            logger.exception("Failed to ingest memory file %s", path)


def update_agent_session_memory(
    card: LearningCard,
    *,
    project_path: str | None,
    session_id: str,
    claim_slugs: list[str] | None = None,
    ingest: bool = True,
) -> Path:
    """Upsert a short bullet into this chat's memory.md (prefer claim wikilinks)."""
    path = agent_memory_path(project_path, session_id)
    summary = (card.summary or card.query or "").strip()
    if len(summary) > 220:
        summary = summary[:217] + "…"
    claim_links = ""
    if claim_slugs:
        claim_links = " · " + " ".join(f"[[{s}]]" for s in claim_slugs[:3])
    bullet = f"**{card.query[:80]}** — {summary}{claim_links}"
    _append_memory_bullet(path, title="Chat agent memory", bullet=bullet, ingest=ingest)
    return path


def _append_project_log(
    card: LearningCard,
    *,
    project_path: str | None,
    session_id: str | None,
    claim_slugs: list[str] | None = None,
) -> Path:
    """Append-only history so consolidation does not erase the trail."""
    path = project_log_path(project_path)
    sid = _safe_session_id(session_id) or "unscoped"
    day = datetime.now(timezone.utc).date().isoformat()
    summary = (card.summary or card.query or "").strip()
    if len(summary) > 180:
        summary = summary[:177] + "…"
    links = ""
    if claim_slugs:
        links = " " + " ".join(f"[[{s}]]" for s in claim_slugs[:3])
    bullet = (
        f"[chat:{sid[:8]}] **{card.query[:72]}** "
        f"({card.confidence:.0%}) — {summary or 'learning recorded'}{links}"
    )
    _append_memory_bullet(path, title="Project memory log", bullet=f"({day}) {bullet}", ingest=False)
    return path


def _extract_section_bullets(text: str, heading: str) -> list[str]:
    """Collect bullet lines under a ## heading until the next ##."""
    if not text:
        return []
    pattern = re.compile(
        rf"(?ims)^##\s*{re.escape(heading)}\s*\n(.*?)(?=^##\s|\Z)"
    )
    m = pattern.search(text)
    if not m:
        return []
    out: list[str] = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if line.startswith("- "):
            out.append(line[2:].strip())
    return out


def _optional_llm_polish_sections(body: str) -> str:
    """Tighten wording with fast LLM when configured; never required."""
    try:
        from second_brain.memory.llm import invoke_llm
        from langchain_core.messages import HumanMessage, SystemMessage

        if not os.getenv("LLM_FAST_MODEL", "").strip() and not os.getenv("LLM_API_KEY", "").strip():
            # Still try if a provider key exists via get_llm; keep short timeout path
            pass
        prompt = (
            "Tighten the following project memory markdown. Keep the exact ## headings "
            "(Settled claims, Open questions, Recent revisions, Active chats). "
            "Do not invent new claims. Return markdown only.\n\n" + body
        )
        resp = invoke_llm(
            [
                SystemMessage(content="You edit personal knowledge base memory notes."),
                HumanMessage(content=prompt),
            ],
            role="fast",
        )
        text = (getattr(resp, "content", None) or str(resp) or "").strip()
        if "## Settled claims" in text and "## Open questions" in text:
            return text
    except Exception:
        logger.debug("LLM polish of project.md skipped", exc_info=True)
    return body


def consolidate_project_memory(
    card: LearningCard,
    *,
    project_path: str | None = None,
    session_id: str | None = None,
    claim_slugs: list[str] | None = None,
    ingest: bool = True,
) -> Path:
    """Rewrite project.md into structured sections from active claims + open questions."""
    from second_brain.memory.claims import list_claims

    path = project_memory_path(project_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Preserve prior open questions / chats from existing file
    existing = ""
    if path.is_file():
        try:
            existing = path.read_text(encoding="utf-8")
        except OSError:
            existing = ""

    prior_open = _extract_section_bullets(existing, "Open questions")
    prior_chats = _extract_section_bullets(existing, "Active chats")

    active = list_claims(project_path, status="active")
    all_claims = list_claims(project_path, status=None)

    settled_lines: list[str] = []
    for c in active:
        slug = c.slug or Path(c.path or "").stem
        conf = f"{c.confidence:.0%}"
        settled_lines.append(f"- [[{slug}]] ({conf}) — {c.claim}")

    open_qs: list[str] = []
    seen_q: set[str] = set()
    for q in list(card.open_questions or []) + prior_open:
        qn = (q or "").strip()
        if not qn:
            continue
        key = qn.lower()
        if key in seen_q:
            continue
        seen_q.add(key)
        open_qs.append(f"- {qn}")
        if len(open_qs) >= 12:
            break
    if not open_qs:
        open_qs = ["- (none yet)"]

    revisions: list[str] = []
    slug_by_id = {c.id: (c.slug or Path(c.path or "").stem) for c in all_claims}
    for c in all_claims:
        if c.supersedes and c.status == "active":
            old_slug = slug_by_id.get(c.supersedes, c.supersedes[:8])
            new_slug = c.slug or Path(c.path or "").stem
            revisions.append(f"- [[{new_slug}]] revises [[{old_slug}]]")
    revisions = revisions[-8:]
    if not revisions:
        revisions = ["- (none yet)"]

    chats: list[str] = []
    seen_chat: set[str] = set()
    sid = _safe_session_id(session_id or card.session_id)
    if sid:
        prior_chats = [f"`{sid}`"] + prior_chats
    for item in prior_chats:
        raw = item.strip().strip("`")
        if not raw or raw in seen_chat:
            continue
        seen_chat.add(raw)
        chats.append(f"- `{raw}`")
        if len(chats) >= 16:
            break
    if not chats:
        chats = ["- (none yet)"]

    if not settled_lines:
        settled_lines = ["- (none yet)"]

    now = datetime.now(timezone.utc).isoformat()
    body = "\n".join(
        [
            "## Settled claims",
            *settled_lines,
            "",
            "## Open questions",
            *open_qs,
            "",
            "## Recent revisions",
            *revisions,
            "",
            "## Active chats",
            *chats,
            "",
        ]
    )
    body = _optional_llm_polish_sections(body)

    # Append log entry before rewrite
    try:
        _append_project_log(
            card,
            project_path=project_path,
            session_id=sid,
            claim_slugs=claim_slugs,
        )
    except Exception:
        logger.exception("Failed to append project-log.md")

    doc = "\n".join(
        [
            "---",
            'type: project-memory',
            'title: "Project memory"',
            f"updated: {now}",
            "---",
            "",
            "# Project memory",
            "",
            body,
        ]
    )
    path.write_text(doc, encoding="utf-8")
    if ingest:
        try:
            ingest_file(path)
        except Exception:
            logger.exception("Failed to ingest consolidated project.md")
    return path


def promote_to_project_memory(
    card: LearningCard,
    *,
    project_path: str | None,
    session_id: str | None = None,
    claim_slugs: list[str] | None = None,
    ingest: bool = True,
) -> Path:
    """Backward-compatible name — consolidates structured project.md."""
    return consolidate_project_memory(
        card,
        project_path=project_path,
        session_id=session_id,
        claim_slugs=claim_slugs,
        ingest=ingest,
    )


def read_project_memory_section(
    project_path: str | None = None,
    *,
    heading: str = "Settled claims",
    max_lines: int = 12,
) -> str:
    """Return bullet lines under a project.md section for UI peek."""
    path = project_memory_path(project_path)
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    bullets = _extract_section_bullets(text, heading)
    return "\n".join(f"- {b}" for b in bullets[:max_lines])


def read_project_memory_tail(
    project_path: str | None = None,
    *,
    max_lines: int = 12,
) -> str:
    """Prefer Settled claims section; fall back to last body lines."""
    settled = read_project_memory_section(
        project_path, heading="Settled claims", max_lines=max_lines
    )
    if settled and "(none yet)" not in settled:
        return settled
    path = project_memory_path(project_path)
    if not path.is_file():
        return settled
    try:
        lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    except OSError:
        return settled
    body = [
        ln
        for ln in lines
        if not ln.startswith("---") and not ln.startswith("# ") and not ln.startswith("type:")
    ]
    return "\n".join(body[-max_lines:]) or settled


def read_agent_memory_tail(
    project_path: str | None,
    session_id: str,
    *,
    max_lines: int = 10,
) -> str:
    """Last bullets from a chat's memory.md for UI peek."""
    sid = _safe_session_id(session_id)
    if not sid:
        return ""
    path = agent_memory_path(project_path, sid)
    if not path.is_file():
        return ""
    try:
        lines = [
            ln.strip()
            for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip().startswith("- ")
        ]
    except OSError:
        return ""
    return "\n".join(lines[-max_lines:])


def write_report_file(
    state: dict[str, Any],
    *,
    project_path: str | None = None,
) -> Path:
    """Persist full research report under research/."""
    query = (state.get("query") or "research").strip()
    report = state.get("report") or ""
    conf, conf_reasons = compute_confidence(state)
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%d-%H%M%S")
    slug = _slugify(query)
    directory = research_dir(project_path)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{stamp}-{slug}.md"
    stats = state.get("retrieval_stats") or {}
    stats_s = ", ".join(f"{k}: {v}" for k, v in stats.items())
    fm = [
        "---",
        f"date: {now.date().isoformat()}",
        f'query: "{query.replace(chr(34), chr(92) + chr(34))}"',
        f'sources: "{stats_s}"',
        'tags: ["research", "auto-generated"]',
        f"revisions: {state.get('revision_count', 0)}",
        f"confidence: {conf}",
        "type: research-report",
        "---",
        "",
        f"# {query}",
        "",
        report,
        "",
        f"_Confidence: {conf:.0%} — {'; '.join(conf_reasons[:3])}_",
        "",
    ]
    path.write_text("\n".join(fm), encoding="utf-8")
    return path


def write_learning_card(
    state: dict[str, Any],
    *,
    project_path: str | None = None,
    report_path: str | None = None,
    session_id: str | None = None,
    ingest: bool = True,
) -> LearningCard:
    """Write a learning card markdown file and optionally index it."""
    query = (state.get("query") or "").strip()
    report = state.get("report") or ""
    conf, conf_reasons = compute_confidence(state)
    now = datetime.now(timezone.utc)
    card_id = uuid4().hex[:12]
    sid = _safe_session_id(session_id or state.get("session_id"))
    card = LearningCard(
        id=card_id,
        query=query,
        summary=extract_executive_summary(report),
        key_findings=extract_key_findings(report),
        open_questions=extract_open_questions(report),
        source_stats={
            str(k): int(v)
            for k, v in (state.get("retrieval_stats") or {}).items()
            if isinstance(v, (int, float))
        },
        confidence=conf,
        confidence_reasons=conf_reasons,
        critique_summary=(state.get("critique") or "")[:500],
        project_path=project_path,
        session_id=sid,
        report_path=report_path,
        ts=now.isoformat(),
    )

    related: list[str] = []
    report_link = _report_wikilink(report_path)
    if report_link:
        related.append(report_link)
    for stem in _personal_source_wikilinks(state):
        if stem not in related:
            related.append(stem)

    with ingest_lock(project_path):
        return _write_learning_card_unlocked(
            card,
            project_path=project_path,
            report_path=report_path,
            sid=sid,
            ingest=ingest,
            related=related,
            query=query,
        )


def _write_learning_card_unlocked(
    card: LearningCard,
    *,
    project_path: str | None,
    report_path: str | None,
    sid: str | None,
    ingest: bool,
    related: list[str],
    query: str,
) -> LearningCard:
    if sid:
        directory = agent_learnings_dir(project_path, sid)
    else:
        directory = learnings_dir(project_path)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    path = directory / f"{stamp}-{_slugify(query)}.md"
    path.write_text(_card_markdown(card, related_links=related), encoding="utf-8")
    card.learning_path = str(path.resolve())

    if ingest:
        try:
            ingest_file(path)
            if report_path:
                rp = Path(report_path)
                if rp.is_file():
                    ingest_file(rp)
        except Exception:
            logger.exception("Failed to ingest learning/report into Chroma")
            # Fallback: direct upsert of a compact learning document
            try:
                text = (
                    f"Learning about: {query}\n\n{card.summary}\n\n"
                    + "\n".join(card.key_findings)
                )
                upsert_documents(
                    [
                        Document(
                            page_content=text[:4000],
                            metadata={
                                "source": path.name,
                                "source_path": str(path.resolve()),
                                "chunk_index": 0,
                                "doc_type": "learning",
                                "session_id": sid or "",
                                "page": -1,
                            },
                        )
                    ]
                )
            except Exception:
                logger.exception("Fallback learning upsert failed")

    logger.info(
        "Wrote learning card %s (confidence=%.2f session=%s) → %s",
        card.id,
        card.confidence,
        sid,
        path,
    )
    return card


def _empty_persist_meta(
    state: dict[str, Any],
    *,
    session_id: str | None,
    detail: str,
) -> dict[str, Any]:
    conf, reasons = compute_confidence(state)
    return {
        "confidence": conf,
        "confidence_reasons": reasons,
        "open_questions": extract_open_questions(state.get("report") or ""),
        "learning_path": None,
        "report_path": None,
        "learning_id": None,
        "session_id": _safe_session_id(session_id or state.get("session_id")),
        "agent_memory_path": None,
        "project_memory_path": None,
        "claim_count": 0,
        "claim_slugs": [],
        "claims_revised": 0,
        "memory_written": False,
        "memory_detail": detail,
        "contested_claims": [],
    }


def persist_research_memory(
    state: dict[str, Any],
    *,
    project_path: str | None = None,
    session_id: str | None = None,
    write_report: bool = True,
    ingest: bool = True,
    origin: str = "research",
) -> dict[str, Any]:
    """Write report + learning + claims; consolidate chat + project memory."""
    from second_brain.memory.claims import (
        ORIGIN_RESEARCH,
        ORIGIN_WATCH,
        default_watch_expires,
        upsert_claims_from_learning,
    )
    from second_brain.memory.relevance import SKIP_FILE_DETAIL, should_file_research

    bound = (project_path or state.get("project_path") or "").strip() or None
    if not has_topic_path(bound):
        logger.info("Skipping memory write: no topic bound")
        return _empty_persist_meta(
            state,
            session_id=session_id,
            detail=SKIP_NO_TOPIC_DETAIL,
        )
    project_path = bound

    query = (state.get("query") or state.get("goal") or "").strip()
    file_ok, file_reason = should_file_research(
        query,
        project_path,
        origin=origin or ORIGIN_RESEARCH,
    )
    if not file_ok:
        logger.info("Skipping topic memory write (%s): %s", file_reason, query[:80])
        return _empty_persist_meta(
            state,
            session_id=session_id,
            detail=SKIP_FILE_DETAIL,
        )

    report_path: str | None = None
    if write_report and (state.get("report") or "").strip():
        try:
            report_path = str(write_report_file(state, project_path=project_path).resolve())
        except Exception:
            logger.exception("Failed to write research report file")

    sid = _safe_session_id(session_id or state.get("session_id"))
    card = write_learning_card(
        state,
        project_path=project_path,
        report_path=report_path,
        session_id=sid,
        ingest=ingest,
    )

    structured = state.get("critique_structured")
    forced = (
        isinstance(structured, dict) and structured.get("source") == "forced_max_revisions"
    )
    mint_settled = bool(state.get("critique_approved")) and not forced
    origin = origin or ORIGIN_RESEARCH
    expires = default_watch_expires() if origin == ORIGIN_WATCH else None

    claim_cards = []
    try:
        claim_cards = upsert_claims_from_learning(
            card,
            project_path=project_path,
            session_id=sid,
            ingest=ingest,
            origin=origin,
            mint_settled=mint_settled,
            expires=expires,
        )
    except Exception:
        logger.exception("Failed to upsert claim cards")

    claim_slugs = [c.slug for c in claim_cards if c.slug]
    claim_count = len(claim_cards)
    revised = sum(1 for c in claim_cards if c.supersedes)
    contested = [
        {
            "id": c.id,
            "claim": c.claim,
            "origin": c.origin,
            "status": c.status,
            "slug": c.slug,
        }
        for c in claim_cards
        if c.status == "contested"
    ]

    agent_mem: str | None = None
    project_mem: str | None = None
    if sid:
        try:
            agent_mem = str(
                update_agent_session_memory(
                    card,
                    project_path=project_path,
                    session_id=sid,
                    claim_slugs=claim_slugs,
                    ingest=ingest,
                ).resolve()
            )
        except Exception:
            logger.exception("Failed to update agent session memory")
    try:
        project_mem = str(
            consolidate_project_memory(
                card,
                project_path=project_path,
                session_id=sid,
                claim_slugs=claim_slugs,
                ingest=ingest,
            ).resolve()
        )
    except Exception:
        logger.exception("Failed to consolidate project memory")

    conf, reasons = compute_confidence(state)
    if sid and claim_count:
        detail = f"Updated chat memory · {claim_count} claim(s)"
        if revised:
            detail += f" · {revised} revision(s)"
        detail += " · linked to project"
    elif sid:
        detail = "Updated chat memory · linked to project"
    elif claim_count:
        detail = f"Saved {claim_count} claim(s) · linked to project"
    else:
        detail = "Saved learning · linked to project"
    if contested:
        detail += f" · {len(contested)} contested with your notes"

    return {
        "confidence": conf,
        "confidence_reasons": reasons,
        "open_questions": card.open_questions,
        "learning_path": card.learning_path,
        "report_path": report_path or card.report_path,
        "learning_id": card.id,
        "session_id": sid,
        "agent_memory_path": agent_mem,
        "project_memory_path": project_mem,
        "claim_count": claim_count,
        "claim_slugs": claim_slugs,
        "claims_revised": revised,
        "memory_written": True,
        "memory_detail": detail,
        "contested_claims": contested,
    }
