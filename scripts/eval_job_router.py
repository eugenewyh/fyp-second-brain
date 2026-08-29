#!/usr/bin/env python3
"""Compare regex-only, local model, Gemini, and full pipeline routing."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

LABELED = ROOT / "data" / "job_router" / "labeled_turns.json"
REPORT_JSON = ROOT / "evaluation" / "job_router_report.json"
REPORT_MD = ROOT / "evaluation" / "job_router_report.md"


def _metrics(y_true: list[str], y_pred: list[str]) -> dict:
    from sklearn.metrics import accuracy_score, f1_score

    labels = sorted(set(y_true) | set(y_pred))
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", labels=labels, zero_division=0)),
        "n": len(y_true),
    }


def regex_only(text: str, *, claims: int, attachments: bool) -> str:
    from second_brain.agent.policy import fallback_job, force_file, has_research_intent, has_search_intent

    if force_file(text=text, has_attachments=attachments):
        return "file"
    if has_search_intent(text) or has_research_intent(text):
        return "research"
    return fallback_job(text=text, matching_claim_count=claims, has_attachments=attachments)


def local_only(text: str, *, claims: int, attachments: bool) -> tuple[str | None, float]:
    from second_brain.agent.router.local_model import route_job

    job, _, conf = route_job(
        text,
        matching_claim_count=claims,
        has_attachments=attachments,
    )
    return job, conf


def gemini_only(text: str, *, claims: int) -> str | None:
    from second_brain.agent.router.llm_router import llm_choose
    from second_brain.agent.router.recall import RecallSnapshot
    from second_brain.memory.gemini_lite import gemini_lite_configured

    if not gemini_lite_configured():
        return None
    snap = RecallSnapshot(topic="eval", matching_claim_count=claims, claim_previews=[])
    job, _ = llm_choose(text, snap)
    return job


def full_pipeline(text: str, *, claims: int, attachments: bool) -> tuple[str, str]:
    from second_brain.agent.router.turn import route_act

    decision = route_act(
        text,
        project_path="/vault/eval",
        has_attachments=attachments,
        choose_fn=None,
    )
    return decision.job or "refuse", decision.route_tier


def main() -> None:
    rows = json.loads(LABELED.read_text(encoding="utf-8"))
    eval_rows = [
        r
        for r in rows
        if str(r.get("text") or "").strip()
        and str(r.get("job") or "").strip().lower() in {"file", "answer", "research", "refuse"}
    ]

    y_true: list[str] = []
    regex_pred: list[str] = []
    local_pred: list[str] = []
    local_confident: list[bool] = []
    gemini_pred: list[str] = []
    pipeline_pred: list[str] = []
    tier_counts: dict[str, int] = {}

    gemini_available = False
    try:
        from second_brain.memory.gemini_lite import gemini_lite_configured

        gemini_available = gemini_lite_configured()
    except Exception:
        pass

    # Offline reproducible eval: mock recall from labeled claim counts.
    from second_brain.agent.router import llm_router, recall as recall_mod

    real_llm = llm_router.llm_choose
    real_recall = recall_mod.recall_snapshot
    claim_by_text: dict[str, int] = {}

    def mock_recall(message: str, project_path: str | None, also_project_paths=None):
        from second_brain.agent.router.recall import RecallSnapshot

        count = claim_by_text.get(message.strip(), 0)
        return RecallSnapshot(topic="eval", matching_claim_count=count, claim_previews=[])

    llm_router.llm_choose = lambda *_a, **_k: (None, "")
    recall_mod.recall_snapshot = mock_recall

    for row in eval_rows:
        text = str(row["text"])
        claim_by_text[text.strip()] = int(row.get("claims") or 0)
        job = str(row["job"]).lower()
        claims = int(row.get("claims") or 0)
        attachments = bool(row.get("attachments"))
        y_true.append(job)

        regex_pred.append(regex_only(text, claims=claims, attachments=attachments))

        local_job, conf = local_only(text, claims=claims, attachments=attachments)
        local_confident.append(local_job is not None)
        local_pred.append(local_job or regex_only(text, claims=claims, attachments=attachments))

        g_job = gemini_only(text, claims=claims) if gemini_available else None
        gemini_pred.append(g_job or regex_only(text, claims=claims, attachments=attachments))

        p_job, tier = full_pipeline(text, claims=claims, attachments=attachments)
        pipeline_pred.append(p_job)
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    llm_router.llm_choose = real_llm
    recall_mod.recall_snapshot = real_recall

    local_coverage = sum(local_confident) / max(len(local_confident), 1)
    llm_tier_share = tier_counts.get("llm", 0) / max(len(eval_rows), 1)

    report = {
        "n_eval": len(eval_rows),
        "baselines": {
            "regex_only": _metrics(y_true, regex_pred),
            "local_model": {
                **_metrics(y_true, local_pred),
                "coverage": local_coverage,
            },
            "gemini_json": {
            **_metrics(y_true, gemini_pred),
            "configured": gemini_available,
        },
            "full_pipeline": _metrics(y_true, pipeline_pred),
        },
        "pipeline_tier_distribution": tier_counts,
        "gemini_call_rate_on_auto": llm_tier_share,
    }

    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")

    md = [
        "# Job router evaluation",
        "",
        f"Eval set: **{len(eval_rows)}** labeled turns (held-out style — full file).",
        "",
        "## Baselines",
        "",
        "| Baseline | Accuracy | Macro-F1 | Notes |",
        "|----------|----------|----------|-------|",
    ]
    for name, key in [
        ("Regex-only", "regex_only"),
        ("Local model", "local_model"),
        ("Gemini JSON", "gemini_json"),
        ("Full pipeline", "full_pipeline"),
    ]:
        m = report["baselines"][key]
        note = ""
        if key == "local_model":
            note = f"{m['coverage']:.0%} routed without fallback"
        md.append(f"| {name} | {m['accuracy']:.3f} | {m['macro_f1']:.3f} | {note} |")

    md.extend(
        [
            "",
            "## Full pipeline tier distribution",
            "",
        ]
    )
    for tier, count in sorted(tier_counts.items(), key=lambda x: -x[1]):
        md.append(f"- `{tier}`: {count} ({count / len(eval_rows):.0%})")

    md.append("")
    md.append(f"Gemini (`llm` tier) share: **{llm_tier_share:.0%}**")
    REPORT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps(report["baselines"], indent=2))
    print(f"Wrote {REPORT_JSON}")
    print(f"Wrote {REPORT_MD}")


if __name__ == "__main__":
    main()
