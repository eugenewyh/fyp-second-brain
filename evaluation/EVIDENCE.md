# Evaluation evidence checklist (FYP Sem 2)

**Corpus:** ingested `dlm` vault (diffusion-LM notes). The Semester 1 Java 52-query set was retired because those PDFs are no longer in the knowledge base.

**Suite:** 20 queries in [`benchmarks.json`](benchmarks.json) — 8 Ask (`personal_vault`) + 8 research (`hybrid`/`research`) + 4 honest-gap (`edge_gaps`).

## Commands

Preview:

```bash
source .venv/bin/activate
python scripts/run_evaluation.py --dry-run
```

Smoke (Ask + gap, ~1 min):

```bash
python scripts/run_evaluation.py --ids PV01,PV03,EG01 --sleep 8
```

Full suite (pace OpenRouter/Groq):

```bash
python scripts/run_evaluation.py --sleep 15 -o evaluation/results/nous_dlm.json
python scripts/run_evaluation.py --sleep 15 --resume evaluation/results/nous_dlm.json -o evaluation/results/nous_dlm.json
```

Ask-only (faster, no agent graph):

```bash
python scripts/run_evaluation.py -c personal_vault --sleep 8
```

Self-critique ablation (research categories):

```bash
python scripts/run_evaluation.py -m research --sleep 15 -o evaluation/results/ablation_on.json
python scripts/run_evaluation.py --ablation-off -m research --sleep 15 -o evaluation/results/ablation_off.json
```

Note: `-c` is a single category; run hybrid and research as two jobs or omit `-c` for all 20.

Baselines (Claude / Grok **chat**, no vault):

1. Copy [`baseline_template.csv`](baseline_template.csv) → `evaluation/baselines_scored.csv`
2. Paste Nous answers from the JSON; paste Claude/Grok chat answers; score 1–5
3. Compare:

```bash
python scripts/compare_baselines.py evaluation/results/nous_dlm.json evaluation/baselines_scored.csv -o evaluation/results/comparison.json
python scripts/generate_eval_report.py evaluation/results/nous_dlm.json
```

## UAT / release

- Questionnaire: [`uat_questionnaire.md`](uat_questionnaire.md)
- Package: `scripts/package_release.sh`
- Demo: [`DEMO.md`](../DEMO.md)

## Status

| Artifact | Status |
|----------|--------|
| 20-query DLM harness | Ready |
| Gold / honest-gap / invented metrics | Ready |
| `--sleep` / `--resume` / `--ablation-off` | Ready |
| Full 20-run results | Pending |
| Ablation ON/OFF | Pending |
| Claude + Grok baseline CSV | Template only |
| UAT responses | Pending |
