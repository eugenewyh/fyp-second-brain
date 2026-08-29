#!/usr/bin/env python3
"""Expand job_router labeled_turns.json to 200+ examples with phase/qlen features."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "job_router" / "labeled_turns.json"


def _phase(claims: int) -> str:
    if claims <= 0:
        return "empty"
    if claims <= 2:
        return "seed"
    return "ready"


def row(text: str, job: str, *, claims: int = 0, attachments: bool = False) -> dict:
    return {
        "text": text,
        "job": job,
        "claims": claims,
        "attachments": attachments,
        "phase": _phase(claims),
    }


def main() -> None:
    existing = json.loads(OUT.read_text(encoding="utf-8")) if OUT.is_file() else []
    seen = {(r["text"], r["job"]) for r in existing}
    rows: list[dict] = list(existing)

    def add(text: str, job: str, *, claims: int = 0, attachments: bool = False) -> None:
        key = (text, job)
        if key in seen:
            return
        seen.add(key)
        rows.append(row(text, job, claims=claims, attachments=attachments))

    research_stems = [
        "Research {topic} for beginners",
        "Look up {topic} best practices",
        "Find papers on {topic}",
        "Investigate {topic} for my FYP",
        "Write a report on {topic}",
        "Compare {topic} approaches vs baselines",
        "What are the latest developments in {topic}?",
        "Explore state of the art in {topic}",
        "Deep dive into {topic} with sources",
        "Survey recent work on {topic}",
    ]
    topics = [
        "indoor plant care",
        "specialty coffee roasting",
        "diffusion language models",
        "multi-agent RAG",
        "personal knowledge management",
        "houseplant pests",
        "espresso extraction",
        "constrained decoding",
        "LangGraph agents",
        "FYP report structure",
        "snake plant care",
        "pour-over technique",
        "JustGRPO",
        "hallucination mitigation",
        "watch brief automation",
    ]
    for stem in research_stems:
        for topic in topics:
            add(stem.format(topic=topic), "research", claims=0)

    for topic in topics[:8]:
        add(f"Go deeper on {topic} with more sources", "research", claims=3)
        add(
            f"Synthesise my stance on {topic}. Cite my notes.",
            "research",
            claims=4,
        )

    answer_stems = [
        "According to my notes, what do I think about {topic}?",
        "From my notes, summarize {topic}",
        "What do my notes say about {topic}?",
        "Based on my library, what mistakes did I make with {topic}?",
        "What about {topic}?",
        "Explain my stance on {topic} from memory",
        "Teach me everything about {topic}",
        "Walk me through {topic} from my notes",
    ]
    for stem in answer_stems:
        for topic in topics[:10]:
            add(stem.format(topic=topic), "answer", claims=3)
            add(stem.format(topic=topic), "answer", claims=5)

    refuse_stems = [
        "What is the best {thing} for a small kitchen?",
        "How do I fix a yellow {thing} leaf?",
        "Should I buy a {thing}?",
        "What is {thing}?",
        "Explain {thing}",
        "Who won the {thing}?",
        "What's the weather in {thing}?",
        "Help me with my {thing}",
        "Summarize my thesis chapter on {thing}",
    ]
    things = ["espresso machine", "monstera", "burr grinder", "JustGRPO", "transformers", "World Cup", "KL", "homework"]
    for stem in refuse_stems:
        for thing in things:
            add(stem.format(thing=thing), "refuse", claims=0)

    for q in [
        "According to my notes, what do I care about in DLMs?",
        "What do I know about plants?",
        "What does my notes say about espresso temperature?",
    ]:
        add(q, "refuse", claims=0)

    file_stems = [
        "I now think {claim}.",
        "I still believe {claim}.",
        "My notes on {topic}:\n\n{claim}",
        "Notes from today's reading — {claim}",
    ]
    claims_text = [
        "grind size matters more than the machine",
        "constrained decoding reduces invalid JSON",
        "water weekly with bright indirect light",
        "18g in, 36g out, 28 seconds",
        "parallel decode that breaks JSON is a fail",
    ]
    for stem in file_stems:
        for claim in claims_text:
            add(stem.format(claim=claim, topic="coffee"), "file", claims=0)
            add(stem.format(claim=claim, topic="plants"), "file", claims=2)

    for i in range(12):
        add(f"Attached lecture notes batch {i}", "file", claims=0, attachments=True)
        add("What is this?", "file", claims=0, attachments=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"Wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
