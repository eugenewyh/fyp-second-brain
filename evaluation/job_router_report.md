# Job router evaluation

Eval set: **412** labeled turns (held-out style — full file).

## Baselines

| Baseline | Accuracy | Macro-F1 | Notes |
|----------|----------|----------|-------|
| Regex-only | 0.881 | 0.805 |  |
| Local model | 0.990 | 0.986 | 99% routed without fallback |
| Gemini JSON | 0.784 | 0.739 |  |
| Full pipeline | 0.733 | 0.636 |  |

## Full pipeline tier distribution

- `rule`: 260 (63%)
- `local`: 141 (34%)
- `fallback`: 10 (2%)
- `llm`: 1 (0%)

Gemini (`llm` tier) share: **0%**
