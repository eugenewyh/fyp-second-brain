"""Gemini Flash-Lite JSON fallback for ambiguous Auto routes."""

from __future__ import annotations

import json
import logging
import re

from second_brain.agent.policy import Job
from second_brain.agent.router.recall import RecallSnapshot

logger = logging.getLogger(__name__)

SUPERVISOR_SYSTEM = """You are the Auto router for Nous, a personal knowledge agent.
Pick exactly one job. Reply with JSON only — no markdown, no prose.

Jobs:
- file — remember / teach: user is dumping beliefs, opinions, or notes to save (not asking a question)
- answer — ask: short recall from this topic's existing notes only (no new web/arXiv hunt)
- research — mission: synthesise, explain, find papers, web/arXiv, what's new, or any general question when memory is empty
- refuse — only when they explicitly asked for "my notes" / "according to my notes" and overlapping notes = 0

Decision order (stop at the first match):
1. Explicit lookup or research mission → research
2. Synthesis / multi-part write-up over notes → research (even if they also say "cite my notes")
3. Notes-grounded recall ("according to my notes", "from my notes") → answer if overlapping notes > 0, else refuse
4. Belief / note dump (statements, not a question) → file
5. In-topic question with overlapping notes > 0 → answer
6. In-topic question with overlapping notes = 0 → research (look outside; do not refuse)
7. Unrelated chit-chat with no question → refuse

Hard rules:
- Never invent a job outside the four above
- General "what is X?" / "explain X" with no notes phrasing → research when overlapping notes = 0
- reason: ≤12 words, plain English
"""


def _parse_job(raw: str) -> Job | None:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    if not isinstance(obj, dict):
        return None
    job = str(obj.get("job") or "").strip().lower()
    if job == "done":
        job = "refuse"
    if job in {"file", "answer", "research", "refuse"}:
        return job  # type: ignore[return-value]
    return None


def llm_choose(message: str, snapshot: RecallSnapshot) -> tuple[Job | None, str]:
    """Ambiguous Auto routes use hidden Gemini Flash-Lite."""
    claims = "\n".join(f"- {c}" for c in snapshot.claim_previews) or "(none)"
    user = (
        f"Topic: {snapshot.topic}\n"
        f"Overlapping notes: {snapshot.matching_claim_count}\n"
        f"Note previews:\n{claims}\n\n"
        f"User message:\n{message}\n\n"
        'Respond with only: {"job":"file"|"answer"|"research"|"refuse","reason":"…"}'
    )
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from second_brain.memory.gemini_lite import gemini_lite_configured, invoke_gemini_lite

        if not gemini_lite_configured():
            logger.debug("Router Gemini lite skipped: no GEMINI_API_KEY")
            return None, ""

        raw = invoke_gemini_lite(
            [SystemMessage(content=SUPERVISOR_SYSTEM), HumanMessage(content=user)],
            temperature=0,
        )
        job = _parse_job(raw)
        reason = ""
        try:
            obj = json.loads(raw.strip())
            if isinstance(obj, dict):
                reason = str(obj.get("reason") or "").strip()
        except json.JSONDecodeError:
            pass
        return job, reason
    except Exception:
        logger.debug("Router Gemini choose failed", exc_info=True)
        return None, ""
