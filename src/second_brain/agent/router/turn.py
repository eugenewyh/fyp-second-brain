"""Single entry point for routing a user turn."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Literal

from second_brain.agent.router.context import (
    MAX_CLARIFY,
    create_topic,
    is_skip,
    is_vague,
    is_watch_intent,
    specialist_instruction,
)
from second_brain.agent.policy import (
    Job,
    apply_policy,
    empty_topic_question,
    fallback_job,
    force_file,
    has_learn_intent,
    has_notes_intent,
    has_research_intent,
    has_search_intent,
    has_synthesis_intent,
    is_question,
)
from second_brain.agent.router import llm_router, local_model, recall
from second_brain.agent.router.copy import CLARIFY_ASKS, DISPATCH_COPY, REFUSE_MESSAGE
from second_brain.agent.router.decision import RouteDecision
from second_brain.agent.router.meta import capability_reply, is_meta_intent
from second_brain.agent.router.recall import RecallSnapshot
from second_brain.agent.topic_ops import parse_topic_op, parse_topics

logger = logging.getLogger(__name__)


def _scope_for(job: str) -> Literal["local", "hybrid", "web"]:
    if job == "answer":
        return "local"
    if job == "research":
        return "hybrid"
    return "local"


def _clarify_turn(count: int) -> RouteDecision:
    idx = 0 if count <= 0 else 1
    focus: Literal["clarify", "confirm"] = "clarify" if idx == 0 else "confirm"
    return RouteDecision(
        kind="clarify",
        text=CLARIFY_ASKS[idx],
        focus=focus,
        reason="underspecified",
        route_tier="fallback",
    )


def _turn_from_topic_op(op, *, project_path: str | None) -> RouteDecision:
    bound = Path(project_path).name if project_path else ""
    if op.kind == "merge":
        return RouteDecision(
            kind="dispatch",
            text=(
                f"I'll combine {op.source} into {op.dest}. "
                "Claims copy into the destination; I won't merge names automatically."
            ),
            job="merge",
            instruction=f"combine {op.source} into {op.dest}",
            retrieval_scope="local",
            reason="merge topics",
            route_tier="topic",
            topic=op.dest or bound,
            merge_source=op.source,
            merge_dest=op.dest,
        )
    if op.kind == "retarget":
        return RouteDecision(
            kind="dispatch",
            text=(
                f"This chat now writes to {op.target}. "
                "Earlier claims stay in the previous folder."
            ),
            job="retarget",
            instruction=op.target,
            retrieval_scope="local",
            reason="retarget topic",
            route_tier="topic",
            topic=op.target,
            retarget_topic=op.target,
        )
    return RouteDecision(
        kind="dispatch",
        text=(
            f"That's a different subject. I'll open a new chat for {op.target}. "
            "This thread stays on its current folder."
        ),
        job="split",
        instruction=op.target,
        retrieval_scope="local",
        reason="subject change",
        route_tier="topic",
        topic=op.target,
        new_topic=op.target,
        create_topic=op.target,
    )


def _watch_dispatch(
    text: str,
    *,
    project_path: str | None,
    reason: str,
    route_tier: str,
) -> RouteDecision:
    create = create_topic(text, project_path)
    line = "I'll set a watch on that."
    if create:
        line = f"I'll keep this under {create}. {line}"
    return RouteDecision(
        kind="dispatch",
        text=line,
        job="watch",
        instruction=text,
        retrieval_scope="hybrid",
        reason=reason,
        route_tier=route_tier,  # type: ignore[arg-type]
        topic=create,
        create_topic=create,
    )


def _propose_job(
    text: str,
    snapshot: RecallSnapshot,
    *,
    has_attachments: bool,
    forced: Job | None,
    choose_fn=None,
) -> tuple[Job, str, str, float]:
    """Return (proposed_job, reason, route_tier, confidence)."""
    forced_s = (forced or "").strip().lower() if forced else ""
    if forced_s in {"file", "answer", "research", "refuse"}:
        return forced_s, "forced", "forced", 1.0  # type: ignore[return-value]

    if force_file(text=text, has_attachments=has_attachments):
        return "file", "attachments or a long note dump", "rule", 1.0
    if has_search_intent(text):
        return "research", "explicit lookup", "rule", 1.0
    if has_research_intent(text):
        return "research", "research mission", "rule", 1.0
    if has_synthesis_intent(text) and snapshot.matching_claim_count > 0:
        return "research", "synthesis over notes", "rule", 1.0
    if has_notes_intent(text):
        return "answer", "asked from notes", "rule", 1.0
    if has_learn_intent(text) and snapshot.matching_claim_count > 0:
        return "answer", "wants explanation from notes", "rule", 1.0
    if snapshot.matching_claim_count <= 0 and empty_topic_question(text):
        return "research", "empty topic question", "rule", 1.0
    if not is_question(text) and fallback_job(
        text=text,
        matching_claim_count=snapshot.matching_claim_count,
        has_attachments=has_attachments,
    ) == "file":
        return "file", "belief dump", "rule", 1.0

    if choose_fn is not None:
        picked = choose_fn(text, snapshot)
        return picked, "test", "fallback", 0.0

    routed, router_reason, conf = local_model.route_job(
        text,
        matching_claim_count=snapshot.matching_claim_count,
        has_attachments=has_attachments,
    )
    if routed is not None:
        return routed, router_reason or "router", "local", conf

    try:
        picked, reason = llm_router.llm_choose(text, snapshot)
    except Exception:
        logger.debug("Router LLM choose failed", exc_info=True)
        picked, reason = None, ""
    if picked is not None:
        return picked, reason or "llm", "llm", 0.0

    fb = fallback_job(
        text=text,
        matching_claim_count=snapshot.matching_claim_count,
        has_attachments=has_attachments,
    )
    return fb, reason or "fallback", "fallback", 0.0


def _dispatch_from_routing(
    message: str,
    *,
    project_path: str | None,
    has_attachments: bool,
    instruction: str,
    also_topics: list[str] | None = None,
    also_project_paths: list[str] | None = None,
    forced_job: Job | None = None,
    choose_fn=None,
) -> RouteDecision:
    blob = instruction or message
    extras = [p for p in (also_project_paths or []) if p]
    snapshot = recall.recall_snapshot(blob, project_path, also_project_paths=extras or None)
    forced_s = (forced_job or "").strip().lower() if forced_job else ""

    proposed, reason, tier, confidence = _propose_job(
        blob,
        snapshot,
        has_attachments=has_attachments,
        forced=forced_job,
        choose_fn=choose_fn,
    )
    job = apply_policy(
        proposed,
        text=blob,
        matching_claim_count=snapshot.matching_claim_count,
        has_attachments=has_attachments,
        forced=forced_s in {"file", "answer", "research"},
    )
    refuse = REFUSE_MESSAGE if job == "refuse" else None
    create = create_topic(blob, project_path)
    copy = DISPATCH_COPY.get(job, job)
    if refuse:
        copy = refuse
    elif (
        job == "research"
        and snapshot.matching_claim_count <= 0
        and not has_search_intent(blob)
        and not has_research_intent(blob)
    ):
        copy = "Nothing saved on this topic yet — I'll look outside."
    names = [n for n in (also_topics or []) if n]
    if names and job in {"answer", "research"}:
        extra = ", ".join(names)
        copy = f"I'll check {extra} as well. {copy}"
    if create and job != "refuse":
        copy = f"I'll keep this under {create}. {copy}"

    return RouteDecision(
        kind="dispatch",
        text=copy,
        job=job,  # type: ignore[arg-type]
        instruction=blob,
        retrieval_scope=_scope_for(job),
        route_tier=tier,  # type: ignore[arg-type]
        confidence=confidence,
        reason=reason or job,
        refuse_message=refuse,
        matching_claim_count=snapshot.matching_claim_count,
        topic=snapshot.topic or create,
        create_topic=create,
        also_topics=names,
        also_project_paths=extras,
    )


def route_act(
    message: str,
    *,
    project_path: str | None = None,
    has_attachments: bool = False,
    also_project_paths: list[str] | None = None,
    forced_job: Job | None = None,
    choose_fn=None,
) -> RouteDecision:
    """Job proposal + policy clamp only (no manager interview / topic ops)."""
    return _dispatch_from_routing(
        message,
        project_path=project_path,
        has_attachments=has_attachments,
        instruction=(message or "").strip(),
        also_project_paths=also_project_paths,
        forced_job=forced_job,
        choose_fn=choose_fn,
    )


def route_turn(
    message: str,
    *,
    project_path: str | None = None,
    has_attachments: bool = False,
    clarify_count: int = 0,
    history: list[dict[str, str]] | None = None,
    topics: list[dict[str, str]] | None = None,
    forced_job: str | None = None,
    choose_fn=None,
) -> RouteDecision:
    """Single routing pipeline: forced → topic → meta → rules → recall → local → llm → policy."""
    text = (message or "").strip()
    asked = max(0, int(clarify_count or 0))
    instruction = specialist_instruction(text, history)
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

    if raw_force == "watch":
        return _watch_dispatch(text or instruction, project_path=project_path, reason="forced watch", route_tier="forced")

    if is_meta_intent(text) and force is None and not also_topics:
        snap = recall.recall_snapshot(text, project_path)
        return RouteDecision(
            kind="meta",
            text=capability_reply(topic=snap.topic, has_memory=snap.matching_claim_count > 0),
            route_tier="meta",
            reason="capability",
            topic=snap.topic,
            matching_claim_count=snap.matching_claim_count,
        )

    if force is not None:
        return _dispatch_from_routing(
            text,
            project_path=project_path,
            has_attachments=has_attachments,
            instruction=routed,
            also_topics=also_topics,
            also_project_paths=also_paths,
            forced_job=force,
            choose_fn=choose_fn,
        )

    if force_file(text=text, has_attachments=has_attachments):
        return _dispatch_from_routing(
            text,
            project_path=project_path,
            has_attachments=True if has_attachments else False,
            instruction=routed,
            also_topics=also_topics,
            also_project_paths=also_paths,
            choose_fn=choose_fn,
        )

    if is_watch_intent(text):
        return _watch_dispatch(text, project_path=project_path, reason="watch intent", route_tier="rule")

    if is_skip(text):
        goal = instruction or text
        if (
            re.search(r"\blook\b", text, re.I)
            or has_search_intent(text)
            or has_search_intent(goal)
        ) and not has_notes_intent(goal):
            create = create_topic(goal, project_path)
            line = "I'll look this up."
            if create:
                line = f"I'll keep this under {create}. {line}"
            return RouteDecision(
                kind="dispatch",
                text=line,
                job="research",
                instruction=goal,
                retrieval_scope="hybrid",
                reason="skip lookup",
                route_tier="rule",
                topic=create,
                create_topic=create,
                also_topics=also_topics,
                also_project_paths=also_paths,
            )
        return _dispatch_from_routing(
            text,
            project_path=project_path,
            has_attachments=has_attachments,
            instruction=goal,
            also_topics=also_topics,
            also_project_paths=also_paths,
            choose_fn=choose_fn,
        )

    if asked < MAX_CLARIFY and is_vague(text) and not also_topics:
        return _clarify_turn(asked)

    return _dispatch_from_routing(
        text,
        project_path=project_path,
        has_attachments=has_attachments,
        instruction=routed,
        also_topics=also_topics,
        also_project_paths=also_paths,
        choose_fn=choose_fn,
    )
