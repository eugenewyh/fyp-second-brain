"""Ask depth detection and source pinning for memory-only explain paths."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from second_brain.agent.policy import has_learn_intent
from second_brain.memory.claims import list_claims

AskDepth = Literal["quick", "comprehensive"]

_COMPREHENSIVE = re.compile(
    r"\b("
    r"everything|all about|the whole|entire(?: lecture| topic| chapter)?|"
    r"full (?:lecture|notes|overview|summary|guide)|"
    r"complete (?:overview|guide|summary)|"
    r"walk me through(?: all| everything)?"
    r")\b",
    re.I,
)
_LEC_HINT = re.compile(r"\b(lec\s*\d+|Lec\d+)\b", re.I)
_FILE_HINT = re.compile(r"\b([A-Za-z][\w-]*(?:\.md|\.pdf)?)\b")

_QUERY_STOP = {
    "teach",
    "about",
    "everything",
    "explain",
    "help",
    "understand",
    "learn",
    "walk",
    "through",
    "notes",
    "from",
    "what",
    "the",
    "all",
    "me",
    "session",
    "bean",
    "beans",
    "this",
    "that",
    "these",
    "those",
    "lecture",
    "topic",
    "subject",
    "file",
    "document",
    "note",
}


def ask_depth(query: str) -> AskDepth:
    """Quick recall vs comprehensive explain-from-memory."""
    t = (query or "").strip()
    if has_learn_intent(t) and _COMPREHENSIVE.search(t):
        return "comprehensive"
    return "quick"


def _normalize_path(path: str) -> str:
    try:
        return str(Path(path).expanduser().resolve())
    except Exception:
        return str(path).strip()


def _path_tokens(path: str) -> set[str]:
    p = Path(path)
    tokens = {p.stem.lower(), p.name.lower()}
    for part in re.split(r"[_\-\s]+", p.stem):
        if len(part) > 2:
            tokens.add(part.lower())
    m = re.match(r"lec(\d+)", p.stem, re.I)
    if m:
        tokens.add(f"lec{m.group(1)}")
    compact = re.sub(r"[_\-\s]+", "", p.stem.lower())
    if compact:
        tokens.add(compact)
    return tokens


def _hint_tokens(hints: list[str]) -> set[str]:
    out: set[str] = set()
    for h in hints:
        h = h.lower().strip()
        out.add(h)
        out.add(re.sub(r"\s+", "", h))
        if h.endswith((".md", ".pdf")):
            out.add(Path(h).stem.lower())
    return out


def _extract_hints(query: str) -> list[str]:
    hints: list[str] = []
    for m in _LEC_HINT.finditer(query):
        hints.append(re.sub(r"\s+", "", m.group(1)))
    for m in _FILE_HINT.finditer(query):
        token = m.group(1)
        if token.lower() in _QUERY_STOP:
            continue
        if len(token) < 4 and not _LEC_HINT.match(token):
            continue
        hints.append(token)
    return hints


def _score_source(candidate: str, hints: set[str]) -> float:
    if not hints:
        return 0.0
    ctokens = _path_tokens(candidate)
    best = 0.0
    stem_compact = re.sub(r"[_\-\s]+", "", Path(candidate).stem.lower())
    for h in hints:
        h = h.lower()
        h_compact = re.sub(r"\s+", "", h)
        if h in ctokens or h_compact in ctokens:
            best = max(best, 1.0)
        elif h_compact in stem_compact:
            best = max(best, 0.95)
        elif any(h in t or h_compact in t for t in ctokens):
            best = max(best, 0.85)
        elif any(t in h or t in h_compact for t in ctokens if len(t) >= 4):
            best = max(best, 0.7)
    return best


def _candidate_sources(
    project_path: str | None,
    *,
    note_path: str | None = None,
) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()

    def add(raw: str | None) -> None:
        if not raw or not str(raw).strip():
            return
        norm = _normalize_path(str(raw))
        if norm not in seen:
            seen.add(norm)
            candidates.append(norm)

    if note_path:
        add(note_path)

    if not project_path:
        return candidates

    for card in list_claims(project_path, status=None):
        add(card.source_path)

    root = Path(project_path).expanduser()
    if root.is_dir():
        for ext in (".md", ".pdf", ".txt"):
            for p in root.rglob(f"*{ext}"):
                parts = {part.lower() for part in p.parts}
                if "memory" in parts and p.name in {"project.md", "memory.md"}:
                    continue
                if "/memory/claims/" in str(p).replace("\\", "/"):
                    continue
                add(str(p.resolve()))

    return candidates


def resolve_pinned_source(
    query: str,
    project_path: str | None,
    *,
    note_path: str | None = None,
    min_score: float = 0.7,
) -> str | None:
    """Pin retrieval to one source file when the query or open note names it."""
    hints = _extract_hints(query)
    hint_set = _hint_tokens(hints)

    if note_path and note_path.strip():
        norm_note = _normalize_path(note_path)
        if not hint_set:
            if has_learn_intent(query) or ask_depth(query) == "comprehensive":
                return norm_note
        elif _score_source(norm_note, hint_set) >= min_score:
            return norm_note
        elif has_learn_intent(query) or ask_depth(query) == "comprehensive":
            return norm_note

    if not hint_set:
        return None

    best_path: str | None = None
    best_score = 0.0
    for cand in _candidate_sources(project_path, note_path=note_path):
        score = _score_source(cand, hint_set)
        if score > best_score:
            best_score = score
            best_path = cand
    if best_score >= min_score:
        return best_path
    return None


def source_path_matches(candidate: str | None, pinned: str | None) -> bool:
    """True when candidate doc/claim path refers to the pinned source."""
    if not candidate or not pinned:
        return False
    c = _normalize_path(candidate)
    p = _normalize_path(pinned)
    if c == p:
        return True
    if Path(c).name.lower() == Path(p).name.lower():
        return True
    if c.endswith(p) or p.endswith(c):
        return True
    return _score_source(c, _hint_tokens([Path(p).stem, Path(p).name])) >= 0.85
