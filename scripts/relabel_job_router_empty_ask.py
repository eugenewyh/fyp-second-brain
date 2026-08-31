#!/usr/bin/env python3
"""Relabel empty-memory general questions as research (notes-intent stays refuse)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from second_brain.agent.policy import has_learn_intent, has_notes_intent, is_question  # noqa: E402

LABELED = ROOT / "data" / "job_router" / "labeled_turns.json"

CANONICAL = [
    {
        "text": "Can you tell me what is OCEAN personality?",
        "job": "research",
        "claims": 0,
        "attachments": False,
        "phase": "empty",
    },
    {
        "text": "What is the Big Five personality model?",
        "job": "research",
        "claims": 0,
        "attachments": False,
        "phase": "empty",
    },
    {
        "text": "What is the best espresso machine for a small kitchen?",
        "job": "research",
        "claims": 0,
        "attachments": False,
        "phase": "empty",
    },
    {
        "text": "Explain constrained decoding for diffusion language models",
        "job": "research",
        "claims": 0,
        "attachments": False,
        "phase": "empty",
    },
    {
        "text": "How does GRPO work?",
        "job": "research",
        "claims": 0,
        "attachments": False,
        "phase": "empty",
    },
    {
        "text": "Teach me everything about snake plant care",
        "job": "research",
        "claims": 0,
        "attachments": False,
        "phase": "empty",
    },
    {
        "text": "What do I know about plants?",
        "job": "research",
        "claims": 0,
        "attachments": False,
        "phase": "empty",
    },
    {
        "text": "According to my notes, what grind size do I prefer?",
        "job": "refuse",
        "claims": 0,
        "attachments": False,
        "phase": "empty",
    },
    {
        "text": "According to my notes, what do I care about in DLMs?",
        "job": "refuse",
        "claims": 0,
        "attachments": False,
        "phase": "empty",
    },
    {
        "text": "From my notes, summarize my espresso workflow",
        "job": "refuse",
        "claims": 0,
        "attachments": False,
        "phase": "empty",
    },
]


def _should_research_when_empty(text: str) -> bool:
    t = (text or "").strip()
    if not t or has_notes_intent(t):
        return False
    return is_question(t) or has_learn_intent(t)


def main() -> None:
    rows = json.loads(LABELED.read_text(encoding="utf-8"))
    flipped = 0
    for row in rows:
        text = str(row.get("text") or "")
        claims = int(row.get("claims") or 0)
        job = str(row.get("job") or "").lower()
        if claims > 0 or job != "refuse":
            continue
        if _should_research_when_empty(text):
            row["job"] = "research"
            flipped += 1

    seen = {(r["text"], r["job"]) for r in rows}
    added = 0
    for row in CANONICAL:
        key = (row["text"], row["job"])
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
        added += 1

    LABELED.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"Relabeled {flipped} refuse→research rows; added {added} canonical examples ({len(rows)} total)")


if __name__ == "__main__":
    main()
