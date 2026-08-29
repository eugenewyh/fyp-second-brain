"""Cache comprehensive study-guide answers per pinned source."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from second_brain.ingestion.sections import file_content_hash, load_section_index
from second_brain.memory.learning import has_topic_path, project_memory_root

logger = logging.getLogger(__name__)


@dataclass
class StudyGuideEntry:
    source_path: str
    content_hash: str
    question_key: str
    answer: str
    created: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StudyGuideEntry | None:
        if not isinstance(data, dict):
            return None
        answer = str(data.get("answer") or "").strip()
        source_path = str(data.get("source_path") or "").strip()
        digest = str(data.get("content_hash") or "").strip()
        question_key = str(data.get("question_key") or "").strip()
        if not answer or not source_path or not digest or not question_key:
            return None
        return cls(
            source_path=source_path,
            content_hash=digest,
            question_key=question_key,
            answer=answer,
            created=str(data.get("created") or ""),
        )


def _guides_dir(project_path: str | None) -> Path | None:
    if not has_topic_path(project_path):
        return None
    return project_memory_root(project_path) / "study_guides"


def _question_key(question: str) -> str:
    t = (question or "").strip().lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t[:120] or "question"


def _cache_file(project_path: str | None, source_path: str, question_key: str) -> Path | None:
    base = _guides_dir(project_path)
    if base is None:
        return None
    stem = Path(source_path).stem
    safe_stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", stem).strip("-")[:60] or "source"
    safe_q = re.sub(r"[^a-z0-9_-]+", "-", question_key).strip("-")[:60] or "q"
    return base / f"{safe_stem}__{safe_q}.json"


def _live_content_hash(source_path: str) -> str | None:
    index = load_section_index(source_path)
    if index:
        return index.content_hash
    try:
        text = Path(source_path).expanduser().read_text(encoding="utf-8")
    except OSError:
        return None
    return file_content_hash(text)


def get_cached_study_guide(
    question: str,
    source_path: str,
    *,
    project_path: str | None = None,
) -> str | None:
    qkey = _question_key(question)
    path = _cache_file(project_path, source_path, qkey)
    if path is None or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    entry = StudyGuideEntry.from_dict(data)
    if not entry:
        return None
    live_hash = _live_content_hash(source_path)
    if not live_hash or live_hash != entry.content_hash:
        return None
    try:
        resolved = str(Path(source_path).expanduser().resolve())
    except Exception:
        resolved = source_path
    if entry.source_path != resolved:
        return None
    logger.info("Study guide cache hit for %s", Path(source_path).name)
    return entry.answer


def save_study_guide(
    question: str,
    source_path: str,
    answer: str,
    *,
    project_path: str | None = None,
) -> Path | None:
    qkey = _question_key(question)
    digest = _live_content_hash(source_path)
    if not digest or not (answer or "").strip():
        return None
    try:
        resolved = str(Path(source_path).expanduser().resolve())
    except Exception:
        resolved = source_path
    entry = StudyGuideEntry(
        source_path=resolved,
        content_hash=digest,
        question_key=qkey,
        answer=answer.strip(),
        created=datetime.now(timezone.utc).isoformat(),
    )
    path = _cache_file(project_path, source_path, qkey)
    if path is None:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entry.to_dict(), indent=2), encoding="utf-8")
    logger.info("Cached study guide for %s", Path(source_path).name)
    return path
