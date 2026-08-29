"""Per-section summaries extracted at ingest for Deep Ask context packing."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_UNBOUND = Path("/nonexistent/nous-unbound-topic")


def _has_topic_path(project_path: str | None) -> bool:
    return bool(project_path and str(project_path).strip())


def _project_memory_root(project_path: str | None) -> Path:
    if _has_topic_path(project_path):
        return Path(str(project_path).strip()).expanduser() / "memory"
    return _UNBOUND / "memory"


_SECTION = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.MULTILINE)
_WS = re.compile(r"\s+")
_MAX_SUMMARY = 500


def file_content_hash(text: str) -> str:
    normalized = _WS.sub(" ", (text or "").strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass
class SectionSummary:
    title: str
    summary: str
    order: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SectionIndex:
    source_path: str
    content_hash: str
    sections: list[SectionSummary] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "content_hash": self.content_hash,
            "sections": [s.to_dict() for s in self.sections],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SectionIndex | None:
        if not isinstance(data, dict):
            return None
        raw_sections = data.get("sections") or []
        sections: list[SectionSummary] = []
        for item in raw_sections:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            summary = str(item.get("summary") or "").strip()
            if not title:
                continue
            sections.append(
                SectionSummary(
                    title=title,
                    summary=summary,
                    order=int(item.get("order") or len(sections) + 1),
                )
            )
        source_path = str(data.get("source_path") or "").strip()
        digest = str(data.get("content_hash") or "").strip()
        if not source_path or not digest:
            return None
        return cls(source_path=source_path, content_hash=digest, sections=sections)


def infer_project_from_source(source_path: str | Path) -> str | None:
    """Topic folder = nearest ancestor that contains a memory/ directory."""
    try:
        path = Path(source_path).expanduser().resolve()
    except Exception:
        return None
    for parent in [path.parent, *path.parents]:
        if (parent / "memory").is_dir():
            return str(parent)
    return None


def sections_dir(project_path: str | None) -> Path | None:
    if not _has_topic_path(project_path):
        return None
    return _project_memory_root(project_path) / "sections"


def _cache_path(source_path: str, project_path: str | None = None) -> Path | None:
    project = project_path or infer_project_from_source(source_path)
    base = sections_dir(project)
    if base is None:
        return None
    stem = Path(source_path).stem
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", stem).strip("-")[:80] or "source"
    return base / f"{safe}.json"


def _heuristic_summary(body: str, *, limit: int = _MAX_SUMMARY) -> str:
    text = (body or "").strip()
    if not text:
        return ""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    for para in paragraphs:
        line = _WS.sub(" ", para)
        line = re.sub(r"^[-*•]\s+", "", line)
        if len(line) >= 24:
            if len(line) > limit:
                return line[: limit - 1] + "…"
            return line
    compact = _WS.sub(" ", text)
    if len(compact) > limit:
        return compact[: limit - 1] + "…"
    return compact


def parse_markdown_sections(text: str) -> list[SectionSummary]:
    """Split markdown on ## / ### headings into titled summary bullets."""
    raw = (text or "").strip()
    if not raw:
        return []

    matches = list(_SECTION.finditer(raw))
    if not matches:
        summary = _heuristic_summary(raw)
        if summary:
            return [SectionSummary(title="Overview", summary=summary, order=1)]
        return []

    sections: list[SectionSummary] = []
    order = 0

    # Preamble before first heading (often # Title)
    first = matches[0]
    preamble = raw[: first.start()].strip()
    if preamble:
        title_line = preamble.splitlines()[0].strip().lstrip("#").strip() or "Overview"
        summary = _heuristic_summary(preamble)
        if summary:
            order += 1
            sections.append(SectionSummary(title=title_line, summary=summary, order=order))

    for i, match in enumerate(matches):
        level = len(match.group(1))
        if level == 1 and sections:
            # Document title only when no preamble captured it
            continue
        title = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        body = raw[start:end]
        summary = _heuristic_summary(body)
        if not summary:
            continue
        order += 1
        sections.append(SectionSummary(title=title, summary=summary, order=order))
    return sections


def build_section_index(file_path: Path, *, project_path: str | None = None) -> SectionIndex | None:
    suffix = file_path.suffix.lower()
    if suffix not in {".md", ".txt"}:
        return None
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError:
        logger.debug("Section index skipped — unreadable %s", file_path)
        return None
    resolved = str(file_path.expanduser().resolve())
    digest = file_content_hash(text)
    sections = parse_markdown_sections(text)
    if not sections:
        return None
    return SectionIndex(source_path=resolved, content_hash=digest, sections=sections)


def save_section_index(index: SectionIndex, *, project_path: str | None = None) -> Path | None:
    path = _cache_path(index.source_path, project_path)
    if path is None:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index.to_dict(), indent=2), encoding="utf-8")
    logger.info("Saved %d section summary(ies) for %s", len(index.sections), path.name)
    return path


def load_section_index(
    source_path: str,
    *,
    project_path: str | None = None,
) -> SectionIndex | None:
    path = _cache_path(source_path, project_path)
    if path is None or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    index = SectionIndex.from_dict(data)
    if not index:
        return None
    try:
        resolved = str(Path(source_path).expanduser().resolve())
    except Exception:
        resolved = source_path
    if index.source_path != resolved:
        return None
    try:
        live = Path(resolved).read_text(encoding="utf-8")
    except OSError:
        return index
    if file_content_hash(live) != index.content_hash:
        return None
    return index


def ensure_section_summaries(
    file_path: Path,
    *,
    project_path: str | None = None,
) -> SectionIndex | None:
    """Build or refresh section summaries when the file content changed."""
    index = build_section_index(file_path, project_path=project_path)
    if not index:
        return None
    existing = load_section_index(index.source_path, project_path=project_path)
    if existing and existing.content_hash == index.content_hash:
        return existing
    save_section_index(index, project_path=project_path)
    return index


def format_section_outline(index: SectionIndex, *, max_chars: int = 3500) -> str:
    if not index.sections:
        return ""
    lines = [f"[Section outline — {Path(index.source_path).name}]"]
    budget = max_chars - len(lines[0]) - 2
    for sec in index.sections:
        line = f"{sec.order}. {sec.title}: {sec.summary}"
        if len(line) + 2 > budget:
            lines.append("…")
            break
        lines.append(line)
        budget -= len(line) + 1
    return "\n".join(lines)
