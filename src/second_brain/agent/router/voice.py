"""LLM manager voice — natural one-liners after routing (Gemini lite, template fallback)."""

from __future__ import annotations

import logging
import re
from dataclasses import replace

from second_brain.agent.router.decision import RouteDecision

logger = logging.getLogger(__name__)

_VOICE_SYSTEM = """You are Nous, a calm personal knowledge assistant for one topic folder.
Write what the user sees next: one or two short sentences in plain conversational English.
No markdown, bullets, JSON, or role labels. Do not say you already finished the task —
you are only acknowledging the plan before work starts.

Modes:
- meta: greet and explain Teach (save notes), Ask (recall notes), Research (look outside), Watch (scheduled briefs).
- clarify: ask one specific follow-up about what they want done; do not repeat generic "what are you trying to get done".
- file: acknowledge you will save or digest what they sent.
- answer: acknowledge you will answer from their saved notes on this topic.
- research: acknowledge you will look this up or run a research pass.
- refuse: gently say this topic has no matching notes yet; suggest Teach first or Research if they want outside sources.
- watch: acknowledge setting up a recurring brief.

Stay under 240 characters unless refuse needs one extra sentence for clarity.
"""


def _strip_quotes(text: str) -> str:
    t = (text or "").strip()
    if len(t) >= 2 and t[0] == t[-1] and t[0] in {'"', "'"}:
        return t[1:-1].strip()
    return t


def _kind_label(decision: RouteDecision) -> str:
    if decision.kind == "meta":
        return "meta"
    if decision.kind == "clarify":
        return "clarify"
    return str(decision.job or "dispatch")


def _user_prompt(decision: RouteDecision, *, user_message: str) -> str:
    also = ", ".join(decision.also_topics) if decision.also_topics else "(none)"
    create = decision.create_topic or "(existing folder)"
    fallback = decision.text or ""
    focus = decision.focus or "clarify"
    return (
        f"Mode: {_kind_label(decision)}\n"
        f"Topic: {decision.topic or 'this topic'}\n"
        f"Saved notes overlapping this message: {decision.matching_claim_count}\n"
        f"New folder suggestion: {create}\n"
        f"Also check topics: {also}\n"
        f"Clarify focus: {focus}\n"
        f"Template fallback (same intent, improve wording): {fallback}\n\n"
        f"User message:\n{user_message.strip()}\n\n"
        "Reply with only the user-visible line(s)."
    )


def _should_voice(decision: RouteDecision) -> bool:
    if decision.job in {"merge", "retarget", "split"}:
        return False
    return decision.kind in {"meta", "clarify", "dispatch"}


def generate_voice(decision: RouteDecision, *, user_message: str) -> str | None:
    """Return natural manager copy, or None to keep the routed template."""
    if not _should_voice(decision):
        return None
    if not (user_message or "").strip() and decision.kind != "meta":
        return None

    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from second_brain.memory.gemini_lite import gemini_lite_configured, invoke_gemini_lite

        if not gemini_lite_configured():
            return None

        raw = invoke_gemini_lite(
            [
                SystemMessage(content=_VOICE_SYSTEM),
                HumanMessage(content=_user_prompt(decision, user_message=user_message)),
            ],
            max_tokens=120,
            temperature=0.35,
        )
        line = _strip_quotes(raw or "")
        line = re.sub(r"\s+", " ", line).strip()
        if len(line) < 8 or len(line) > 400:
            return None
        return line
    except Exception:
        logger.debug("Manager voice skipped", exc_info=True)
        return None


def apply_voice(decision: RouteDecision, *, user_message: str) -> RouteDecision:
    """Polish user-visible text; keep routing fields unchanged."""
    line = generate_voice(decision, user_message=user_message)
    if not line:
        return decision
    updated = replace(decision, text=line, reason=(decision.reason or "") + "+voice")
    if updated.job == "refuse":
        updated = replace(updated, refuse_message=line)
    return updated
