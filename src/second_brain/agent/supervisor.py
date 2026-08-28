"""Grok-style supervisor: recall first, then pick a tool, then policy may deny."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from second_brain.agent.policy import (
    Job,
    apply_policy,
    fallback_job,
    force_file,
    has_notes_intent,
    has_research_intent,
    has_search_intent,
    has_synthesis_intent,
    is_question,
)

logger = logging.getLogger(__name__)

REFUSE_MESSAGE = (
    "I don't have notes on this topic yet. Teach something here first — "
    "then Ask from what you saved."
)

SUPERVISOR_SYSTEM = """You are the Auto router for Nous, a personal knowledge agent.
Pick exactly one job. Reply with JSON only — no markdown, no prose.

Jobs:
- file — remember / teach: user is dumping beliefs, opinions, or notes to save (not asking a question)
- answer — ask: short recall from this topic's existing notes only (no new web/arXiv hunt)
- research — mission: synthesise a stance, multi-part write-up, deepen, find papers, web/arXiv, or what's new
- refuse — off-topic for this project and they did not ask to look anything up

Decision order (stop at the first match):
1. Explicit lookup → research
   Signals: look up, find papers, arXiv, search the web, what's new, latest, dig into sources
2. Synthesis / mission over notes → research (even if they also say "cite my notes")
   Signals: synthesise, stance on, write-up, literature review, report on, multi-part, go deeper, more sources
3. Notes-grounded recall question → answer
   Signals: according to my notes, from my notes, what do I care about, what do my notes say
   Requires overlapping notes > 0. If overlapping notes are 0 → refuse
4. Belief / note dump (statements, not a question) → file
   Signals: I think / I still / I now think / long multi-sentence assertions with no ?
5. In-topic question with overlapping notes > 0 → answer
6. Unrelated to the topic and no lookup ask → refuse
7. Uncertain but on-topic and overlapping notes > 0 → answer
   Uncertain, on-topic, wants breadth/new info → research
   Uncertain and off-topic → refuse

Hard rules:
- Never invent a job outside the four above
- Prefer answer over research for simple recall; prefer research when they want synthesis, depth, or new sources
- "Cite my notes" alone is not research — only with synthesis/mission language
- Overlapping notes = 0 blocks answer; use refuse unless they asked to look it up (then research)
- Topic name matters: off-topic gadget/lifestyle questions in a research/academic topic → refuse unless lookup was explicit
- reason: ≤12 words, plain English

Examples:
User: "Find papers on JustGRPO" → {"job":"research","reason":"explicit paper lookup"}
User: "According to my notes, what do I care about for espresso?" (notes>0) → {"job":"answer","reason":"notes recall"}
User: "Synthesise my stance on DLMs; cite my notes." (notes>0) → {"job":"research","reason":"synthesis over notes"}
User: "I now think grind size matters more than the machine." → {"job":"file","reason":"belief dump"}
User: "Best espresso machine for a small kitchen?" in topic "dlm" (notes=0) → {"job":"refuse","reason":"off-topic no lookup"}
"""


@dataclass
class RecallSnapshot:
    topic: str
    matching_claim_count: int
    claim_previews: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ActDecision:
    job: Job
    reason: str
    matching_claim_count: int
    topic: str
    refuse_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job": self.job,
            "reason": self.reason,
            "matching_claim_count": self.matching_claim_count,
            "topic": self.topic,
            "refuse_message": self.refuse_message,
        }


def topic_name(project_path: str | None) -> str:
    if not project_path:
        return "this topic"
    return Path(project_path).name.replace("-", " ").replace("_", " ").strip() or "this topic"


def recall_snapshot(
    message: str,
    project_path: str | None,
    also_project_paths: list[str] | None = None,
) -> RecallSnapshot:
    """Cheap recall: matching claims only, no LLM."""
    topic = topic_name(project_path)
    previews: list[str] = []
    count = 0
    paths = [p for p in [project_path, *(also_project_paths or [])] if p and str(p).strip()]
    seen: set[str] = set()
    try:
        from second_brain.memory.claims import claims_matching_query

        for path in paths:
            key = str(Path(path).resolve()) if path else ""
            if key in seen:
                continue
            seen.add(key)
            matched = claims_matching_query(message, path, limit=5)
            count += len(matched)
            for c in matched[:3]:
                text = (c.claim or "").strip()[:180]
                if text and text not in previews:
                    previews.append(text)
            if len(previews) >= 3:
                previews = previews[:3]
    except Exception:
        logger.debug("Supervisor recall skipped", exc_info=True)
    return RecallSnapshot(topic=topic, matching_claim_count=count, claim_previews=previews)


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


def _llm_choose(message: str, snapshot: RecallSnapshot) -> tuple[Job | None, str]:
    """Ambiguous Auto routes use hidden Gemini Flash-Lite (same as chat rename)."""
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
            logger.debug("Supervisor Gemini lite skipped: no GEMINI_API_KEY")
            return None, ""

        raw = invoke_gemini_lite(
            [SystemMessage(content=SUPERVISOR_SYSTEM), HumanMessage(content=user)],
            max_tokens=80,
            temperature=0.1,
        )
        if not raw:
            return None, ""
        job = _parse_job(raw)
        reason = ""
        try:
            obj = json.loads(raw) if raw.strip().startswith("{") else {}
            if isinstance(obj, dict):
                reason = str(obj.get("reason") or "")
        except json.JSONDecodeError:
            # Model may wrap JSON — _parse_job already extracted job
            m = re.search(r"\{.*\}", raw, re.S)
            if m:
                try:
                    obj = json.loads(m.group(0))
                    if isinstance(obj, dict):
                        reason = str(obj.get("reason") or "")
                except json.JSONDecodeError:
                    pass
        return job, reason[:240]
    except Exception:
        logger.debug("Supervisor LLM choose skipped", exc_info=True)
        return None, ""


def decide_act(
    message: str,
    *,
    project_path: str | None = None,
    has_attachments: bool = False,
    also_project_paths: list[str] | None = None,
    forced_job: Job | None = None,
    choose_fn=None,
) -> ActDecision:
    """Recall, pick a job, clamp with policy.

    Clear heuristic paths stay free. Ambiguous Auto routes use hidden Gemini
    Flash-Lite (same key/model as chat rename). Falls back to heuristics if unset.
    ``forced_job`` skips propose (Shift+Tab / plus menu) but policy still clamps.
    ``choose_fn`` is for tests.
    """
    text = (message or "").strip()
    snapshot = recall_snapshot(
        text, project_path, also_project_paths=also_project_paths
    )
    reason = ""
    forced = (forced_job or "").strip().lower() if forced_job else ""

    if forced in {"file", "answer", "research", "refuse"}:
        proposed: Job = forced  # type: ignore[assignment]
        reason = "forced"
    elif force_file(text=text, has_attachments=has_attachments):
        proposed = "file"
        reason = "attachments or a long note dump"
    elif has_search_intent(text):
        proposed = "research"
        reason = "explicit lookup"
    elif has_research_intent(text):
        proposed = "research"
        reason = "research mission"
    elif has_synthesis_intent(text) and snapshot.matching_claim_count > 0:
        proposed = "research"
        reason = "synthesis over notes"
    elif has_notes_intent(text):
        proposed = "answer"
        reason = "asked from notes"
    elif not is_question(text) and fallback_job(
        text=text,
        matching_claim_count=snapshot.matching_claim_count,
        has_attachments=has_attachments,
    ) == "file":
        proposed = "file"
        reason = "belief dump"
    elif choose_fn is not None:
        proposed = choose_fn(text, snapshot)
        reason = "test"
    else:
        from second_brain.agent.job_router import route_job

        routed, router_reason, conf = route_job(
            text,
            matching_claim_count=snapshot.matching_claim_count,
            has_attachments=has_attachments,
        )
        if routed is not None:
            proposed = routed
            reason = router_reason or "router"
        else:
            try:
                picked, reason = _llm_choose(text, snapshot)
            except Exception:
                logger.debug("Supervisor LLM choose failed", exc_info=True)
                picked, reason = None, ""
            proposed = picked or fallback_job(
                text=text,
                matching_claim_count=snapshot.matching_claim_count,
                has_attachments=has_attachments,
            )
            if picked is None:
                reason = reason or "fallback"

    job = apply_policy(
        proposed,
        text=text,
        matching_claim_count=snapshot.matching_claim_count,
        has_attachments=has_attachments,
        forced=forced in {"file", "answer", "research"},
    )
    refuse = REFUSE_MESSAGE if job == "refuse" else None
    return ActDecision(
        job=job,
        reason=reason or job,
        matching_claim_count=snapshot.matching_claim_count,
        topic=snapshot.topic,
        refuse_message=refuse,
    )
