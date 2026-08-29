"""Manager interview helpers shared by route_turn and take_turn shim."""

from __future__ import annotations

import re
from pathlib import Path

from second_brain.agent.policy import has_learn_intent, has_notes_intent, has_search_intent, is_question

MAX_CLARIFY = 1

_SKIP = re.compile(
    r"\b(just do it|just look it up|just go|skip|go ahead|never mind|nevermind|stop asking)\b",
    re.I,
)
_WATCH = re.compile(
    r"\b(watch for|keep an eye|set up a watch|daily brief|keep watching)\b",
    re.I,
)
_VAGUE = re.compile(
    r"(?ix)"
    r"(\bhelp(\s+me)?(\s+with)?(\s+my)?\s+"
    r"(thesis|fyp|final\s+year|project|research|homework)\b)"
    r"|(\bwhat\s+should\s+i\b)"
    r"|(\bnot\s+sure\b)"
    r"|(\bidk\b)"
    r"|(\bi\s+don['\u2019]t\s+know\b)"
    r"|(\bi\s+need\s+help\b)"
)

_LEAD = re.compile(
    r"^(?:please\s+)?(?:find|search(?:\s+for)?|look\s*up|watch(?:\s+for)?|"
    r"research|read(?:\s+about)?|summarise|summarize|explain|help\s+(?:me\s+)?(?:with\s+)?)\s+",
    re.I,
)
_PAPERS_ON = re.compile(r"^(?:papers?|articles?|literature|sources?)\s+(?:on|about)\s+", re.I)
_ON_ABOUT = re.compile(r"^(?:on|about|regarding|re)\s+", re.I)
_MY_WORK = re.compile(r"\b(?:my|our)\s+(fyp|thesis|dissertation|project|paper)\b", re.I)
_BAD_FOLDER = re.compile(r'[\\/:*?"<>|]+')


def suggest_topic(text: str) -> str:
    """Short vault-folder name from a user request. No LLM."""
    blob = (text or "").strip().split("\n", 1)[0]
    blob = blob.rstrip("?.! ").strip()
    if not blob:
        return "Research"
    mine = _MY_WORK.search(blob)
    if mine:
        word = mine.group(1)
        return word.upper() if word.lower() == "fyp" else word.capitalize()
    blob = _LEAD.sub("", blob)
    blob = _PAPERS_ON.sub("", blob)
    blob = _ON_ABOUT.sub("", blob)
    blob = _BAD_FOLDER.sub(" ", blob)
    blob = re.sub(r"\s+", " ", blob).strip(" .")
    words = [w for w in blob.split() if w]
    if not words:
        return "Research"
    clipped = " ".join(words[:6])
    if len(clipped) > 48:
        clipped = clipped[:48].rsplit(" ", 1)[0] or clipped[:48]
    if clipped.lower() in {"this", "it", "help", "please", "stuff"}:
        return "Research"
    return clipped


def create_topic(instruction: str, project_path: str | None) -> str:
    if project_path:
        return ""
    return suggest_topic(instruction)


def prior_user_goal(history: list[dict[str, str]] | None) -> str:
    goal = ""
    for item in history or []:
        if str(item.get("role") or "").lower() != "user":
            continue
        content = str(item.get("content") or "").strip()
        if content and not is_skip(content):
            goal = content
    return goal


def specialist_instruction(message: str, history: list[dict[str, str]] | None) -> str:
    text = (message or "").strip()
    if is_skip(text):
        return prior_user_goal(history) or text
    return text


def is_skip(text: str) -> bool:
    return bool(_SKIP.search((text or "").strip()))


def is_watch_intent(text: str) -> bool:
    return bool(_WATCH.search((text or "").strip()))


def is_vague(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    if has_search_intent(t) or is_skip(t) or is_watch_intent(t):
        return False
    if has_notes_intent(t) or has_learn_intent(t):
        return False
    if re.search(
        r"(?i)\bhelp\s+me\s+(?:understand|learn(?:\s+about)?|with)\s+\S",
        t,
    ):
        return False
    if _VAGUE.search(t):
        return True
    if is_question(t):
        return len(t) < 28
    return len(t) < 24
