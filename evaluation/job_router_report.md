# Job router evaluation

Eval set: **518** labeled turns (held-out style — full file).

## Baselines

| Baseline | Accuracy | Macro-F1 | Notes |
|----------|----------|----------|-------|
| Regex-only | 0.867 | 0.786 |  |
| Local model | 1.000 | 1.000 | 97% routed without fallback |
| Gemini JSON | 0.867 | 0.786 |  |
| Full pipeline | 0.956 | 0.953 |  |

## Full pipeline tier distribution

- `rule`: 446 (86%)
- `local`: 71 (14%)
- `fallback`: 1 (0%)

Gemini (`llm` tier) share: **0%**
