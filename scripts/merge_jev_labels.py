#!/usr/bin/env python3
"""Merge high-confidence Jev proposals into data/job_router/labeled_turns.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELED = ROOT / "data" / "job_router" / "labeled_turns.json"
PROPOSALS = ROOT / "data" / "job_router" / "jev_proposals.json"
JOBS = {"file", "answer", "research", "refuse"}


def _phase(claims: int) -> str:
    if claims <= 0:
        return "empty"
    if claims <= 2:
        return "seed"
    return "ready"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--proposals", type=Path, default=PROPOSALS)
    ap.add_argument("--into", type=Path, default=LABELED)
    ap.add_argument(
        "--min-confidence",
        type=float,
        default=0.85,
        help="Only merge proposals with confidence >= this (default: 0.85)",
    )
    ap.add_argument(
        "--tag-source",
        action="store_true",
        help="Keep source=jev on merged rows (default: strip to train schema)",
    )
    args = ap.parse_args()

    if not args.proposals.is_file():
        raise SystemExit(f"Missing proposals: {args.proposals}\nRun: cd scripts/jev_job_label && npm run label")

    proposals = json.loads(args.proposals.read_text(encoding="utf-8"))
    existing = json.loads(args.into.read_text(encoding="utf-8")) if args.into.is_file() else []
    seen = {str(r.get("text") or "").strip() for r in existing}

    added = 0
    skipped_conf = 0
    skipped_dup = 0
    for p in proposals:
        text = str(p.get("text") or "").strip()
        job = str(p.get("job") or "").strip().lower()
        conf = float(p.get("confidence") or 0)
        if not text or job not in JOBS:
            continue
        if conf < args.min_confidence:
            skipped_conf += 1
            continue
        if text in seen:
            skipped_dup += 1
            continue
        claims = int(p.get("claims") or 0)
        row = {
            "text": text,
            "job": job,
            "claims": claims,
            "attachments": bool(p.get("attachments")),
            "phase": _phase(claims),
        }
        if args.tag_source:
            row["source"] = "jev"
            row["confidence"] = conf
        existing.append(row)
        seen.add(text)
        added += 1

    args.into.parent.mkdir(parents=True, exist_ok=True)
    args.into.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    print(
        f"Merged {added} rows into {args.into} "
        f"(now {len(existing)}; skipped_conf={skipped_conf}, skipped_dup={skipped_dup})"
    )
    print("Next: python3 scripts/train_job_router.py && python3 scripts/eval_job_router.py")


if __name__ == "__main__":
    main()
