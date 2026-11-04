#!/usr/bin/env python3
"""Write data/job_router/unlabeled_candidates.json for Jev pseudo-labeling."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "job_router" / "unlabeled_candidates.json"
LABELED = ROOT / "data" / "job_router" / "labeled_turns.json"


def row(text: str, *, claims: int = 0, attachments: bool = False) -> dict:
    return {"text": text, "claims": claims, "attachments": attachments}


def main() -> None:
    known = set()
    if LABELED.is_file():
        for r in json.loads(LABELED.read_text(encoding="utf-8")):
            t = str(r.get("text") or "").strip()
            if t:
                known.add(t)

    candidates: list[dict] = []
    seen: set[str] = set()

    def add(text: str, *, claims: int = 0, attachments: bool = False) -> None:
        text = text.strip()
        if not text or text in known or text in seen:
            return
        seen.add(text)
        candidates.append(row(text, claims=claims, attachments=attachments))

    topics = [
        "espresso dial-in",
        "snake plant watering",
        "diffusion LMs",
        "claim write-back",
        "Watch briefs",
        "pour-over ratio",
        "FYP evaluation metrics",
        "indoor humidity for plants",
        "arXiv retrieval",
        "Manager job routing",
    ]

    for t in topics:
        add(f"Remember this: my notes on {t} go under this topic.", claims=0)
        add(f"Save the attached dump about {t}.", claims=1, attachments=True)
        add(f"File these bullets into memory about {t}.", claims=0, attachments=True)
        add(f"According to my notes, what matters most for {t}?", claims=4)
        add(f"What did I already decide about {t}?", claims=6)
        add(f"Summarise my stance on {t} from memory only.", claims=3)
        add(f"Research recent work on {t} and cite sources.", claims=0)
        add(f"Look up best practices for {t} outside my vault.", claims=2)
        add(f"Compare approaches to {t} and write a short report.", claims=1)
        add(f"What grind should I use?", claims=0)  # empty-memory ask → often refuse
        add(f"Based on my notes, how do I handle {t}?", claims=0)
        add(f"Teach: paste dump for {t}", claims=0)
        add(f"Can you recall what I taught you about {t}?", claims=5)
        add(f"Find papers on {t}", claims=0)
        add(f"Keep a Watch on {t} and brief me weekly.", claims=2)

    # Edge-ish phrasings
    add("Don't invent — I haven't taught anything yet. What do my notes say about dose?", claims=0)
    add("I attached a markdown dump — please remember it.", claims=0, attachments=True)
    add("Open research goal: survey grounding metrics for personal RAG.", claims=0)
    add("Quick question from my Coffee notes: water hardness target?", claims=8)
    add("Refuse if you don't have notes: what's my espresso recipe?", claims=0)
    add("Please ingest this Teach dump before I Ask.", claims=0, attachments=True)
    add("Run research on JustGRPO vs baselines with citations.", claims=1)
    add("From memory only — list contested claims about milk steaming.", claims=7)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(candidates, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(candidates)} unlabeled candidates → {OUT}")


if __name__ == "__main__":
    main()
