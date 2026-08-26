"""Daily digest aggregation — roll up learning cards into a user-facing brief."""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from second_brain.config import DOCUMENTS_DIR
from second_brain.ingestion.pipeline import ingest_file
from second_brain.memory.chroma_store import upsert_documents
from second_brain.memory.learning import (
    extract_executive_summary,
    extract_key_findings,
    extract_open_questions,
    has_topic_path,
    learnings_dir,
    project_memory_root,
)

logger = logging.getLogger(__name__)


def digests_dir(project_path: str | None = None) -> Path:
    if has_topic_path(project_path):
        return project_memory_root(project_path) / "digests"
    # Scheduler check-in only — never used for claims.
    return DOCUMENTS_DIR / "memory" / "digests"


def _split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta: dict[str, str] = {}
    for line in parts[1].strip().splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta, parts[2]


def parse_learning_card(path: Path) -> dict[str, Any] | None:
    """Parse a learning-card markdown file into a structured dict."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        logger.exception("Failed to read learning card %s", path)
        return None
    meta, body = _split_frontmatter(text)
    if meta.get("type") and meta.get("type") != "learning":
        return None
    summary = extract_executive_summary(body)
    if not summary:
        m = re.search(r"(?is)##\s*Summary\s*\n(.*?)(?=\n##\s|\Z)", body)
        if m:
            summary = re.sub(r"\s+", " ", m.group(1)).strip()[:600]
    findings = extract_key_findings(body)
    if not findings:
        m = re.search(r"(?is)##\s*Key findings\s*\n(.*?)(?=\n##\s|\Z)", body)
        if m:
            for line in m.group(1).splitlines():
                bullet = re.sub(r"^[-*•]\s+|\d+[.)]\s+", "", line.strip()).strip()
                if len(bullet) > 12 and bullet.lower() != "(none extracted)":
                    findings.append(bullet[:240])
    questions = extract_open_questions(body)
    if not questions:
        m = re.search(r"(?is)##\s*Open questions\s*\n(.*?)(?=\n##\s|\Z)", body)
        if m:
            for line in m.group(1).splitlines():
                bullet = re.sub(r"^[-*•]\s+|\d+[.)]\s+", "", line.strip()).strip()
                if (
                    len(bullet) > 8
                    and bullet.lower() not in {"(none)", "(n/a)"}
                ):
                    questions.append(bullet[:240])
    try:
        confidence = float(meta.get("confidence") or 0.5)
    except ValueError:
        confidence = 0.5
    return {
        "path": str(path.resolve()),
        "id": meta.get("id") or path.stem,
        "date": meta.get("date") or "",
        "query": meta.get("query") or path.stem,
        "summary": summary,
        "key_findings": findings,
        "open_questions": questions,
        "confidence": confidence,
        "report_path": meta.get("report_path") or "",
        "mtime": path.stat().st_mtime,
    }


def list_learning_cards(
    *,
    project_path: str | None = None,
    since: date | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List learning cards, newest first, optionally filtered by date.

    Includes legacy ``memory/learnings/`` and session-scoped
    ``memory/agents/*/learnings/`` cards.
    """
    paths: list[Path] = []
    legacy = learnings_dir(project_path)
    if legacy.is_dir():
        paths.extend(legacy.glob("*.md"))
    agents_root = project_memory_root(project_path) / "agents"
    if agents_root.is_dir():
        paths.extend(agents_root.glob("*/learnings/*.md"))

    cards: list[dict[str, Any]] = []
    for path in sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True):
        card = parse_learning_card(path)
        if not card:
            continue
        card_date = card.get("date") or ""
        if since and card_date:
            try:
                if date.fromisoformat(card_date) < since:
                    continue
            except ValueError:
                pass
        elif since and not card_date:
            # Fall back to mtime date
            mtime_date = datetime.fromtimestamp(card["mtime"], tz=timezone.utc).date()
            if mtime_date < since:
                continue
        cards.append(card)
        if len(cards) >= limit:
            break
    return cards


def collect_open_questions(
    *,
    project_path: str | None = None,
    lookback_days: int = 14,
    limit: int = 10,
) -> list[dict[str, str]]:
    """Collect open questions from recent learning cards (deduped)."""
    since = date.today() - timedelta(days=max(0, lookback_days))
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for card in list_learning_cards(project_path=project_path, since=since, limit=40):
        for q in card.get("open_questions") or []:
            key = re.sub(r"\s+", " ", q.lower()).strip()
            if key in seen or len(key) < 12:
                continue
            seen.add(key)
            out.append(
                {
                    "question": q,
                    "from_query": card.get("query") or "",
                    "learning_path": card.get("path") or "",
                }
            )
            if len(out) >= limit:
                return out
    return out


def _digest_markdown(
    *,
    digest_date: date,
    cards: list[dict[str, Any]],
    goals_run: list[dict[str, Any]],
    new_files: list[str],
) -> str:
    findings: list[str] = []
    questions: list[str] = []
    summaries: list[str] = []
    for card in cards:
        if card.get("summary"):
            summaries.append(f"- **{card.get('query', 'Learning')}**: {card['summary']}")
        for f in card.get("key_findings") or []:
            findings.append(f"- {f}")
        for q in card.get("open_questions") or []:
            questions.append(f"- {q}")

    # Deduplicate while preserving order
    def _dedupe(items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for item in items:
            key = re.sub(r"\s+", " ", item.lower()).strip()
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
        return out

    findings = _dedupe(findings)[:12]
    questions = _dedupe(questions)[:10]
    summaries = _dedupe(summaries)[:8]

    goals_lines = []
    for g in goals_run:
        conf = g.get("confidence")
        conf_s = f" ({conf:.0%})" if isinstance(conf, (int, float)) else ""
        goals_lines.append(f"- {g.get('goal', '')[:200]}{conf_s}")

    files_lines = [f"- `{Path(p).name}`" for p in new_files[:20]] or ["- (none)"]

    return "\n".join(
        [
            "---",
            f"date: {digest_date.isoformat()}",
            "type: digest",
            f"learnings: {len(cards)}",
            f"goals: {len(goals_run)}",
            'tags: ["digest", "daily", "auto-generated"]',
            "---",
            "",
            f"# Daily brief — {digest_date.isoformat()}",
            "",
            "## What I learned",
            "\n".join(summaries) if summaries else "- (no learning cards today)",
            "",
            "## Key findings",
            "\n".join(findings) if findings else "- (none extracted)",
            "",
            "## Still open",
            "\n".join(questions) if questions else "- (none)",
            "",
            "## Goals reviewed",
            "\n".join(goals_lines) if goals_lines else "- (none)",
            "",
            "## Vault changes considered",
            "\n".join(files_lines),
            "",
        ]
    )


def write_daily_digest(
    *,
    digest_date: date | None = None,
    cards: list[dict[str, Any]] | None = None,
    goals_run: list[dict[str, Any]] | None = None,
    new_files: list[str] | None = None,
    project_path: str | None = None,
    ingest: bool = True,
) -> Path:
    """Write (or overwrite) the digest markdown for a given day."""
    digest_date = digest_date or date.today()
    cards = cards if cards is not None else list_learning_cards(
        project_path=project_path, since=digest_date, limit=30
    )
    # Prefer cards whose date matches today; fall back to goals' learning paths
    day_cards = [c for c in cards if (c.get("date") or "") == digest_date.isoformat()]
    if not day_cards and cards:
        day_cards = cards[: max(1, len(goals_run or []))]

    directory = digests_dir(project_path)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{digest_date.isoformat()}.md"
    text = _digest_markdown(
        digest_date=digest_date,
        cards=day_cards,
        goals_run=goals_run or [],
        new_files=new_files or [],
    )
    path.write_text(text, encoding="utf-8")

    if ingest:
        try:
            ingest_file(path)
        except Exception:
            logger.exception("Failed to ingest digest into Chroma")
            try:
                upsert_documents(
                    [
                        Document(
                            page_content=text[:4000],
                            metadata={
                                "source": path.name,
                                "source_path": str(path.resolve()),
                                "chunk_index": 0,
                                "doc_type": "digest",
                                "page": -1,
                            },
                        )
                    ]
                )
            except Exception:
                logger.exception("Fallback digest upsert failed")

    logger.info("Wrote daily digest → %s (%d learnings)", path, len(day_cards))
    return path


def get_digest(
    digest_date: date | None = None,
    *,
    project_path: str | None = None,
) -> dict[str, Any] | None:
    """Load a digest by date. Returns None if missing."""
    digest_date = digest_date or date.today()
    path = digests_dir(project_path) / f"{digest_date.isoformat()}.md"
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    meta, body = _split_frontmatter(text)
    return {
        "date": digest_date.isoformat(),
        "path": str(path.resolve()),
        "content": text,
        "body": body.strip(),
        "learnings": int(meta.get("learnings") or 0) if str(meta.get("learnings", "")).isdigit() else 0,
        "goals": int(meta.get("goals") or 0) if str(meta.get("goals", "")).isdigit() else 0,
        "summary": extract_executive_summary(body)
        or (body.split("\n\n")[0][:400] if body else ""),
    }


def list_digests(
    *,
    project_path: str | None = None,
    limit: int = 30,
) -> list[dict[str, Any]]:
    """List digests newest-first."""
    directory = digests_dir(project_path)
    if not directory.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.md"), reverse=True):
        stem = path.stem
        try:
            d = date.fromisoformat(stem)
        except ValueError:
            continue
        item = get_digest(d, project_path=project_path)
        if item:
            # Keep list payloads light
            out.append(
                {
                    "date": item["date"],
                    "path": item["path"],
                    "learnings": item["learnings"],
                    "goals": item["goals"],
                    "summary": (item.get("summary") or "")[:280],
                }
            )
        if len(out) >= limit:
            break
    return out
