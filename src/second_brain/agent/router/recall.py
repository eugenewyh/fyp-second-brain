"""Cheap recall snapshot before job proposal."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RecallSnapshot:
    topic: str
    matching_claim_count: int
    claim_previews: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def topic_name(project_path: str | None) -> str:
    if not project_path:
        return "this topic"
    return Path(project_path).name.replace("-", " ").replace("_", " ").strip() or "this topic"


def recall_snapshot(
    message: str,
    project_path: str | None,
    also_project_paths: list[str] | None = None,
) -> RecallSnapshot:
    """Matching claims only — no LLM."""
    topic = topic_name(project_path)
    previews: list[str] = []
    count = 0
    paths = [p for p in [project_path, *(also_project_paths or [])] if p and str(p).strip()]
    seen: set[str] = set()
    try:
        from second_brain.memory.claims import claims_matching_query

        for path in paths:
            key = str(Path(path).resolve()) if path else ""
            if key in seen:
                continue
            seen.add(key)
            matched = claims_matching_query(message, path, limit=5)
            count += len(matched)
            for c in matched[:3]:
                text = (c.claim or "").strip()[:180]
                if text and text not in previews:
                    previews.append(text)
            if len(previews) >= 3:
                previews = previews[:3]
    except Exception:
        logger.debug("Router recall skipped", exc_info=True)
    return RecallSnapshot(topic=topic, matching_claim_count=count, claim_previews=previews)
