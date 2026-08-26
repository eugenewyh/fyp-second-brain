"""Parse explicit topic routing: retarget, merge, split, cross-topic retrieve."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

TopicOpKind = Literal["retarget", "merge", "split", "also"]

_MERGE = re.compile(
    r"(?is)^\s*(?:please\s+)?(?:combine|merge)\s+"
    r"(.+?)\s+(?:into|with)\s+(.+?)\s*[.!]?\s*$"
)
_RETARGET = re.compile(
    r"(?is)^\s*(?:please\s+)?"
    r"(?:this\s+is\s+(?:part\s+of|under)|"
    r"(?:file|put|keep)\s+(?:this|it)\s+(?:under|in|as\s+part\s+of)|"
    r"this\s+belongs\s+(?:in|under)|"
    r"file\s+(?:this|it)\s+under|"
    r"(?:bind|retarget)\s+(?:this\s+)?(?:to|under)|"
    r"this\s+is\s+my)\s+"
    r"(.+?)\s*[.!]?\s*$"
)
_SPLIT_FORGET = re.compile(
    r"(?is)^\s*forget\s+.+?[,—–-]\s*let'?s\s+(?:do|talk\s+about|look\s+at|switch\s+to)\s+"
    r"(.+?)(?:\s+instead)?\s*[.!]?\s*$"
)
_NEW_CHAT = re.compile(
    r"(?is)^\s*(?:start\s+a\s+new\s+chat|new\s+chat|new\s+topic|"
    r"different\s+(?:topic|subject)|switch\s+topics?)\s*"
    r"(?:(?:on|about|for|:)\s*(.+))?\s*$"
)
_SWITCH_TO = re.compile(
    r"(?is)^\s*(?:switch\s+to|let'?s\s+switch\s+to)\s+(.+?)\s*[.!]?\s*$"
)
_ALSO_TAIL = re.compile(
    r"(?is)(?:^|\s)(?:also\s+(?:check|look(?:\s+at)?|pull\s+from|search|include|use)|"
    r"pull\s+from)\s+(?:my\s+|the\s+)?(.+?)(?:\s+notes|\s+as\s+well)?\s*$"
)
_AND_NOTES = re.compile(
    r"(?is)(?:^|\s)and\s+(?:my\s+|the\s+)?(.+?)\s+notes\s*[.!]?\s*$"
)


@dataclass
class TopicRef:
    name: str
    path: str = ""


@dataclass
class TopicOp:
    kind: TopicOpKind
    target: str = ""
    target_path: str = ""
    source: str = ""
    source_path: str = ""
    dest: str = ""
    dest_path: str = ""
    also_topics: list[str] = field(default_factory=list)
    also_paths: list[str] = field(default_factory=list)
    remainder: str = ""


def clean_topic_name(raw: str) -> str:
    t = (raw or "").strip().strip("\"'`")
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"^(?:my|the|our)\s+", "", t, flags=re.I)
    t = re.sub(r"\s+(?:notes|folder|topic|project)$", "", t, flags=re.I)
    t = re.sub(r'[\\/:*?"<>|]+', " ", t)
    t = re.sub(r"\s+", " ", t).strip(" .")
    if not t:
        return ""
    if len(t) > 48:
        t = t[:48].rsplit(" ", 1)[0] or t[:48]
    return t


def match_topic(raw: str, available: list[TopicRef]) -> TopicRef:
    needle = clean_topic_name(raw)
    if not needle:
        return TopicRef(name="")
    lower = needle.lower()
    for ref in available:
        if ref.name.lower() == lower:
            return TopicRef(name=ref.name, path=ref.path)
    hits = [
        ref
        for ref in available
        if lower in ref.name.lower() or ref.name.lower() in lower
    ]
    if len(hits) == 1:
        return TopicRef(name=hits[0].name, path=hits[0].path)
    return TopicRef(name=needle, path="")


def folder_name(project_path: str | None) -> str:
    if not project_path or not str(project_path).strip():
        return ""
    return Path(str(project_path).strip()).name


def parse_topics(raw: list[dict[str, str]] | list[TopicRef] | None) -> list[TopicRef]:
    out: list[TopicRef] = []
    for item in raw or []:
        if isinstance(item, TopicRef):
            if item.name:
                out.append(item)
            continue
        name = str(item.get("name") or "").strip()
        path = str(item.get("path") or "").strip()
        if name:
            out.append(TopicRef(name=name, path=path))
    return out


def parse_topic_op(
    text: str,
    *,
    bound_path: str | None = None,
    available: list[TopicRef] | None = None,
) -> TopicOp | None:
    """Detect an explicit routing phrase. None = stay on the bound topic."""
    t = (text or "").strip()
    if not t:
        return None
    refs = available or []
    bound = folder_name(bound_path)

    m = _MERGE.match(t)
    if m:
        src = match_topic(m.group(1), refs)
        dest = match_topic(m.group(2), refs)
        if not src.name or not dest.name or src.name.lower() == dest.name.lower():
            return None
        return TopicOp(
            kind="merge",
            source=src.name,
            source_path=src.path,
            dest=dest.name,
            dest_path=dest.path,
        )

    m = _SPLIT_FORGET.match(t) or _NEW_CHAT.match(t)
    if m:
        raw_name = (m.group(1) or "").strip()
        dest = match_topic(raw_name, refs) if raw_name else TopicRef(name="")
        name = dest.name or clean_topic_name(raw_name) or "Research"
        if bound and name.lower() == bound.lower():
            return None
        return TopicOp(kind="split", target=name, target_path=dest.path)

    m = _SWITCH_TO.match(t)
    if m:
        dest = match_topic(m.group(1), refs)
        if not dest.name:
            return None
        if bound and dest.name.lower() == bound.lower():
            return None
        if dest.path or any(r.name.lower() == dest.name.lower() for r in refs):
            return TopicOp(kind="retarget", target=dest.name, target_path=dest.path)
        return TopicOp(kind="split", target=dest.name, target_path=dest.path)

    m = _RETARGET.match(t)
    if m:
        dest = match_topic(m.group(1), refs)
        if not dest.name:
            return None
        if bound and dest.name.lower() == bound.lower():
            return None
        return TopicOp(kind="retarget", target=dest.name, target_path=dest.path)

    also = _extract_also(t, refs)
    if also:
        return also
    return None


def _extract_also(text: str, refs: list[TopicRef]) -> TopicOp | None:
    """Cross-topic retrieve only when the named folder exists in the workspace."""
    if not refs:
        return None
    m = _ALSO_TAIL.search(text) or _AND_NOTES.search(text)
    if not m:
        return None
    dest = match_topic(m.group(1), refs)
    hit: TopicRef | None = None
    for r in refs:
        if dest.path and r.path and dest.path == r.path:
            hit = r
            break
        if dest.name and r.name.lower() == dest.name.lower():
            hit = r
            break
    # Reject invented tails like "and what I'd buy next. Cite my notes"
    if not hit:
        return None
    remainder = (text[: m.start()] + " " + text[m.end() :]).strip()
    remainder = re.sub(r"\s+", " ", remainder).strip(" ,.")
    return TopicOp(
        kind="also",
        also_topics=[hit.name],
        also_paths=[hit.path] if hit.path else [],
        remainder=remainder,
    )
