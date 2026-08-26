"""Grok-short router: dispatch when the task is clear; ask at most twice when vague."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from second_brain.agent.policy import (
    Job,
    force_file,
    has_notes_intent,
    has_search_intent,
    is_question,
)
from second_brain.agent.topic_ops import parse_topic_op, parse_topics
from second_brain.agent.supervisor import REFUSE_MESSAGE, decide_act

MAX_CLARIFY = 2

ManagerKind = Literal["ask", "dispatch"]
ManagerJob = Literal[
    "file",
    "answer",
    "research",
    "refuse",
    "watch",
    "retarget",
    "merge",
    "split",
]
AskFocus = Literal["clarify", "confirm"]

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
    r"(^\s*(help|help\s+me|please\s+help|hi|hello|hey)\s*[.!]?\s*$)"
    r"|(^\s*what\s+can\s+you\s+do\b)"
    r"|(\bhelp(\s+me)?(\s+with)?(\s+my)?\s+"
    r"(thesis|fyp|final\s+year|project|research|homework)\b)"
    r"|(\bwhat\s+should\s+i\b)"
    r"|(\bnot\s+sure\b)"
    r"|(\bidk\b)"
    r"|(\bi\s+don['\u2019]t\s+know\b)"
    r"|(\bi\s+need\s+help\b)"
)

_ASKS = (
    "What are you trying to get done?",
    "Your notes only, or should I look up papers too?",
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


def _create_topic(instruction: str, project_path: str | None) -> str:
    if project_path:
        return ""
    return suggest_topic(instruction)


@dataclass
class ManagerTurn:
    kind: ManagerKind
    text: str
    focus: AskFocus | None = None
    job: ManagerJob | None = None
    instruction: str | None = None
    retrieval_scope: Literal["local", "hybrid", "web"] | None = None
    reason: str = ""
    refuse_message: str | None = None
    matching_claim_count: int = 0
    topic: str = ""
    create_topic: str = ""
    retarget_topic: str = ""
    merge_source: str = ""
    merge_dest: str = ""
    also_topics: list[str] = field(default_factory=list)
    also_project_paths: list[str] = field(default_factory=list)
    new_topic: str = ""
    idea: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "text": self.text,
            "focus": self.focus,
            "job": self.job,
            "instruction": self.instruction,
            "retrieval_scope": self.retrieval_scope,
            "reason": self.reason,
            "refuse_message": self.refuse_message,
            "matching_claim_count": self.matching_claim_count,
            "topic": self.topic,
            "create_topic": self.create_topic,
            "retarget_topic": self.retarget_topic,
            "merge_source": self.merge_source,
            "merge_dest": self.merge_dest,
            "also_topics": self.also_topics,
            "also_project_paths": self.also_project_paths,
            "new_topic": self.new_topic,
            "idea": self.idea,
        }


def _prior_user_goal(history: list[dict[str, str]] | None) -> str:
    """Last real user request in this interview. Skip phrases are not the goal."""
    goal = ""
    for item in history or []:
        if str(item.get("role") or "").lower() != "user":
            continue
        content = str(item.get("content") or "").strip()
        if content and not is_skip(content):
            goal = content
    return goal


def _specialist_instruction(message: str, history: list[dict[str, str]] | None) -> str:
    """Route and run on this turn. History is only used when they skip the interview."""
    text = (message or "").strip()
    if is_skip(text):
        return _prior_user_goal(history) or text
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
    if _VAGUE.search(t):
        return True
    if is_question(t):
        return len(t) < 28
    return len(t) < 24


def _ask(count: int) -> ManagerTurn:
    idx = 0 if count <= 0 else 1
    focus: AskFocus = "clarify" if idx == 0 else "confirm"
    return ManagerTurn(kind="ask", text=_ASKS[idx], focus=focus, reason="underspecified")


def _scope_for(job: ManagerJob) -> Literal["local", "hybrid", "web"]:
    if job == "answer":
        return "local"
    if job == "research":
        return "hybrid"
    return "local"


def _dispatch_from_act(
    message: str,
    *,
    project_path: str | None,
    has_attachments: bool,
    instruction: str,
    also_topics: list[str] | None = None,
    also_project_paths: list[str] | None = None,
    forced_job: Job | None = None,
) -> ManagerTurn:
    """Hybrid route: clear heuristics free; fast LLM only when ambiguous; policy clamps."""
    blob = instruction or message
    extras = [p for p in (also_project_paths or []) if p]
    decision = decide_act(
        blob,
        project_path=project_path,
        has_attachments=has_attachments,
        also_project_paths=extras or None,
        forced_job=forced_job,
    )
    job: ManagerJob = decision.job
    refuse = decision.refuse_message if job == "refuse" else None
    create = _create_topic(blob, project_path)
    copy = {
        "file": "Filing that into memory.",
        "answer": "Checking your notes.",
        "research": "I'll look this up.",
        "refuse": refuse or REFUSE_MESSAGE,
    }.get(job, job)
    names = [n for n in (also_topics or []) if n]
    if names and job in {"answer", "research"}:
        extra = ", ".join(names)
        copy = f"I'll check {extra} as well. {copy}"
    if create and job != "refuse":
        copy = f"I'll keep this under {create}. {copy}"
    return ManagerTurn(
        kind="dispatch",
        text=copy,
        job=job,
        instruction=blob,
        retrieval_scope=_scope_for(job),
        reason=decision.reason or job,
        refuse_message=refuse,
        matching_claim_count=decision.matching_claim_count,
        topic=decision.topic or create,
        create_topic=create,
        also_topics=names,
        also_project_paths=extras,
    )


def _turn_from_topic_op(op, *, project_path: str | None) -> ManagerTurn:
    bound = Path(project_path).name if project_path else ""
    if op.kind == "merge":
        return ManagerTurn(
            kind="dispatch",
            text=(
                f"I'll combine {op.source} into {op.dest}. "
                "Claims copy into the destination; I won't merge names automatically."
            ),
            job="merge",
            instruction=f"combine {op.source} into {op.dest}",
            retrieval_scope="local",
            reason="merge topics",
            topic=op.dest or bound,
            merge_source=op.source,
            merge_dest=op.dest,
        )
    if op.kind == "retarget":
        return ManagerTurn(
            kind="dispatch",
            text=(
                f"This chat now writes to {op.target}. "
                "Earlier claims stay in the previous folder."
            ),
            job="retarget",
            instruction=op.target,
            retrieval_scope="local",
            reason="retarget topic",
            topic=op.target,
            retarget_topic=op.target,
        )
    return ManagerTurn(
        kind="dispatch",
        text=(
            f"That's a different subject. I'll open a new chat for {op.target}. "
            "This thread stays on its current folder."
        ),
        job="split",
        instruction=op.target,
        retrieval_scope="local",
        reason="subject change",
        topic=op.target,
        new_topic=op.target,
        create_topic=op.target,
    )


def take_turn(
    message: str,
    *,
    project_path: str | None = None,
    has_attachments: bool = False,
    clarify_count: int = 0,
    history: list[dict[str, str]] | None = None,
    topics: list[dict[str, str]] | None = None,
    workspace_empty: bool | None = None,
    agent: str | None = None,
    forced_job: str | None = None,
) -> ManagerTurn:
    """One router turn. Dispatch when clear; ask at most twice when vague.

    ``workspace_empty`` / ``agent`` are accepted for API compat and ignored.
    ``forced_job`` (answer/research/file) skips propose; policy still clamps.
    """
    _ = workspace_empty, agent
    text = (message or "").strip()
    asked = max(0, int(clarify_count or 0))
    instruction = _specialist_instruction(text, history)
    available = parse_topics(topics)
    op = parse_topic_op(text, bound_path=project_path, available=available)
    force: Job | None = None
    raw_force = (forced_job or "").strip().lower()
    if raw_force in {"file", "answer", "research"}:
        force = raw_force  # type: ignore[assignment]

    if op and op.kind in {"merge", "retarget", "split"} and force is None:
        return _turn_from_topic_op(op, project_path=project_path)

    also_topics = list(op.also_topics) if op and op.kind == "also" else []
    also_paths = list(op.also_paths) if op and op.kind == "also" else []
    routed = (op.remainder if op and op.kind == "also" and op.remainder else None) or instruction or text

    if force is not None:
        return _dispatch_from_act(
            text,
            project_path=project_path,
            has_attachments=has_attachments,
            instruction=routed,
            also_topics=also_topics,
            also_project_paths=also_paths,
            forced_job=force,
        )

    if force_file(text=text, has_attachments=has_attachments):
        return _dispatch_from_act(
            text,
            project_path=project_path,
            has_attachments=True if has_attachments else False,
            instruction=routed,
            also_topics=also_topics,
            also_project_paths=also_paths,
        )

    if is_watch_intent(text):
        create = _create_topic(text, project_path)
        line = "I'll set a watch on that."
        if create:
            line = f"I'll keep this under {create}. {line}"
        return ManagerTurn(
            kind="dispatch",
            text=line,
            job="watch",
            instruction=text,
            retrieval_scope="hybrid",
            reason="watch intent",
            topic=create,
            create_topic=create,
        )

    if is_skip(text):
        goal = instruction or text
        if (
            re.search(r"\blook\b", text, re.I)
            or has_search_intent(text)
            or has_search_intent(goal)
        ) and not has_notes_intent(goal):
            create = _create_topic(goal, project_path)
            line = "I'll look this up."
            if create:
                line = f"I'll keep this under {create}. {line}"
            return ManagerTurn(
                kind="dispatch",
                text=line,
                job="research",
                instruction=goal,
                retrieval_scope="hybrid",
                reason="skip lookup",
                topic=create,
                create_topic=create,
                also_topics=also_topics,
                also_project_paths=also_paths,
            )
        return _dispatch_from_act(
            text,
            project_path=project_path,
            has_attachments=has_attachments,
            instruction=goal,
            also_topics=also_topics,
            also_project_paths=also_paths,
        )

    if asked < MAX_CLARIFY and is_vague(text) and not also_topics:
        return _ask(asked)

    return _dispatch_from_act(
        text,
        project_path=project_path,
        has_attachments=has_attachments,
        instruction=routed,
        also_topics=also_topics,
        also_project_paths=also_paths,
    )
