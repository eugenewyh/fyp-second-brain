"""Paths the vault watcher and bulk ingest must not index as Teach dumps."""

from __future__ import annotations

from pathlib import Path

# Relative to vault root — daily review also skips learnings cards as docs
_EXTRA_SKIP_PREFIXES = (
    "memory/digests",
    "memory/learnings",
)


def should_skip_ingest_path(path: Path, root: Path) -> bool:
    """Return True when *path* should not be ingested under *root*."""
    try:
        rel = path.resolve().relative_to(root.resolve())
    except ValueError:
        return True

    posix = rel.as_posix()
    for prefix in _EXTRA_SKIP_PREFIXES:
        if posix == prefix or posix.startswith(prefix + "/"):
            return True

    if "digests" in rel.parts:
        return True
    if "briefs" in rel.parts or "memory" in rel.parts or "watches" in rel.parts:
        return True
    if "research" in rel.parts:
        return True
    if rel.name.lower() == "instruction.md":
        return True
    return False
