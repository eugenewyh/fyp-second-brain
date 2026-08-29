"""Meta intents — capability replies instead of vague clarify loops."""

from __future__ import annotations

import re

_META_GREETING = re.compile(
    r"(?ix)"
    r"^\s*(hi|hello|hey|yo|good\s+(morning|afternoon|evening))\s*[.!?]?\s*$"
)
_META_CAPABILITY = re.compile(
    r"(?ix)"
    r"^\s*what\s+can\s+you\s+do\b"
    r"|^\s*what\s+do\s+you\s+do\b"
    r"|^\s*how\s+does\s+this\s+work\b"
    r"|^\s*help\s*$"
)


_META_COMBO = re.compile(
    r"(?ix)"
    r"^\s*(?:hi|hello|hey)[,.]?\s+what\s+can\s+you\s+do\b"
)


def is_meta_intent(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    return bool(
        _META_GREETING.search(t)
        or _META_CAPABILITY.search(t)
        or _META_COMBO.search(t)
    )


def capability_reply(*, topic: str, has_memory: bool) -> str:
    memory_line = (
        "This topic already has notes — Ask recalls them, Research can look outside."
        if has_memory
        else "This topic is empty — start with Teach, then Ask or Research."
    )
    return (
        f"I'm Nous for {topic}. "
        "Teach saves notes here. Ask recalls from memory. "
        "Research runs agents with sources. Watch schedules briefs. "
        f"{memory_line}"
    )
