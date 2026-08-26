"""Whether a topic channel has anything to remember yet."""

from __future__ import annotations

from pathlib import Path

from second_brain.memory.claims import list_claims

_SKIP_DIR_NAMES = {"memory", "briefs", "watches", "research"}
_SKIP_BASENAMES = {"instruction.md", "idea.md", "readme.md"}
_NOTE_SUFFIXES = {".md", ".txt", ".pdf"}


def idea_body(project_path: str | None) -> str:
    if not project_path:
        return ""
    path = Path(project_path) / "IDEA.md"
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    text = text.lstrip("\ufeff")
    lines = text.splitlines()
    if lines and lines[0].strip().lower() in {"# idea", "#idea"}:
        text = "\n".join(lines[1:])
    return text.strip()


def _is_rememberable_file(path: Path, root: Path) -> bool:
    name = path.name.lower()
    if name.startswith("."):
        return False
    if name in _SKIP_BASENAMES:
        return False
    if path.suffix.lower() not in _NOTE_SUFFIXES:
        return False
    try:
        rel = path.relative_to(root)
    except ValueError:
        return False
    parts = {p.lower() for p in rel.parts[:-1]}
    if parts & _SKIP_DIR_NAMES:
        return False
    return True


def has_rememberable_notes(project_path: str | None) -> bool:
    if not project_path:
        return False
    root = Path(project_path)
    if not root.is_dir():
        return False
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if _is_rememberable_file(path, root):
            return True
    return False


def has_claims(project_path: str | None) -> bool:
    if not project_path:
        return False
    try:
        return bool(list_claims(project_path, status=None))
    except Exception:
        return False


def channel_is_empty(project_path: str | None) -> bool:
    """True only for an existing topic folder with no IDEA, claims, or real notes.

    Missing paths are not empty — callers (and tests) treat them as unknown/ready.
    """
    if not project_path:
        return False
    root = Path(project_path)
    if not root.is_dir():
        return False
    if idea_body(project_path):
        return False
    if has_claims(project_path):
        return False
    if has_rememberable_notes(project_path):
        return False
    return True
