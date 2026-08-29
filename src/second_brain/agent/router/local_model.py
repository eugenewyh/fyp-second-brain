"""Local job router — TF-IDF + logistic regression for Auto mode."""

from __future__ import annotations

import json
import logging
import math
import re
from pathlib import Path

from second_brain.agent.policy import Job
from second_brain.agent.router.features import enrich_router_text

logger = logging.getLogger(__name__)

_TOKEN = re.compile(r"[a-z0-9']+")
_MODEL_PATH = (
    Path(__file__).resolve().parents[4] / "data" / "job_router" / "model.json"
)

_model_cache: dict | None = None


def _tokenize(text: str) -> list[str]:
    return _TOKEN.findall((text or "").lower())


def _ngrams(tokens: list[str], *, max_n: int = 2) -> list[str]:
    out = list(tokens)
    for n in range(2, max_n + 1):
        for i in range(len(tokens) - n + 1):
            out.append(" ".join(tokens[i : i + n]))
    return out


def _load_model() -> dict | None:
    global _model_cache
    if _model_cache is not None:
        return _model_cache or None
    if not _MODEL_PATH.is_file():
        _model_cache = {}
        return None
    try:
        _model_cache = json.loads(_MODEL_PATH.read_text(encoding="utf-8"))
        return _model_cache
    except Exception:
        logger.debug("Job router model load failed", exc_info=True)
        _model_cache = {}
        return None


def _vectorize(enriched: str, model: dict) -> list[float]:
    vocab: dict[str, int] = model["vocabulary"]
    idf: list[float] = model["idf"]
    max_n = int(model.get("ngram_max") or 2)
    tokens = _ngrams(_tokenize(enriched), max_n=max_n)
    tf: dict[int, int] = {}
    for tok in tokens:
        idx = vocab.get(tok)
        if idx is not None:
            tf[idx] = tf.get(idx, 0) + 1
    if not tf:
        return [0.0] * len(idf)
    vec = [0.0] * len(idf)
    for idx, count in tf.items():
        vec[idx] = (1.0 + math.log(count)) * idf[idx]
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _softmax(scores: list[float]) -> list[float]:
    if not scores:
        return []
    m = max(scores)
    exps = [math.exp(s - m) for s in scores]
    total = sum(exps) or 1.0
    return [e / total for e in exps]


def _min_confidence(model: dict, job: str) -> float:
    thresholds = model.get("class_thresholds") or {}
    default = float(model.get("min_confidence") or 0.42)
    return float(thresholds.get(job, default))


def route_job(
    message: str,
    *,
    matching_claim_count: int = 0,
    has_attachments: bool = False,
    min_confidence: float | None = None,
) -> tuple[Job | None, str, float]:
    """Predict job from bundled model. Returns (job, reason, confidence)."""
    model = _load_model()
    text = (message or "").strip()
    if not model or not text:
        return None, "", 0.0
    if has_attachments:
        return "file", "attachments", 1.0

    enriched = enrich_router_text(
        text,
        matching_claim_count=matching_claim_count,
        has_attachments=has_attachments,
    )
    vec = _vectorize(enriched, model)
    classes: list[str] = model["classes"]
    coef: list[list[float]] = model["coef"]
    intercept: list[float] = model["intercept"]

    logits = [
        sum(c * v for c, v in zip(row, vec, strict=True)) + b
        for row, b in zip(coef, intercept, strict=True)
    ]
    probs = _softmax(logits)
    if not probs:
        return None, "", 0.0

    best_i = max(range(len(probs)), key=lambda i: probs[i])
    conf = probs[best_i]
    job = classes[best_i]
    threshold = min_confidence if min_confidence is not None else _min_confidence(model, job)
    if conf < threshold or job not in {"file", "answer", "research", "refuse"}:
        return None, "", conf
    return job, f"router ({conf:.0%})", conf  # type: ignore[return-value]


def model_loaded() -> bool:
    return _load_model() is not None
