# Job router evaluation

Eval set: **805** labeled turns (held-out style — full file).

## Baselines

| Baseline | Accuracy | Macro-F1 | Notes |
|----------|----------|----------|-------|
| Regex-only | 0.882 | 0.856 |  |
| Local model | 0.996 | 0.994 | 98% routed without fallback |
| Gemini JSON | 0.882 | 0.856 |  |
| Full pipeline | 0.952 | 0.945 |  |

## Full pipeline tier distribution

- `rule`: 746 (93%)
- `local`: 59 (7%)

Gemini (`llm` tier) share: **0%**
