#!/usr/bin/env python3
"""Train the local Manager job router and write data/job_router/model.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from second_brain.agent.router.features import enrich_router_text

LABELED = ROOT / "data" / "job_router" / "labeled_turns.json"
MODEL_OUT = ROOT / "data" / "job_router" / "model.json"
METRICS_OUT = ROOT / "evaluation" / "job_router_train_metrics.json"


def main() -> None:
    try:
        import numpy as np
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import (
            classification_report,
            confusion_matrix,
            f1_score,
        )
        from sklearn.model_selection import train_test_split
        from sklearn.pipeline import Pipeline
    except ImportError as exc:
        raise SystemExit("Install scikit-learn: pip install scikit-learn") from exc

    rows = json.loads(LABELED.read_text(encoding="utf-8"))
    texts: list[str] = []
    labels: list[str] = []
    enriched: list[str] = []

    for row in rows:
        text = str(row.get("text") or "").strip()
        job = str(row.get("job") or "").strip().lower()
        claims = int(row.get("claims") or 0)
        attachments = bool(row.get("attachments"))
        if not text or job not in {"file", "answer", "research", "refuse"}:
            continue
        texts.append(text)
        labels.append(job)
        enriched.append(
            enrich_router_text(
                text,
                matching_claim_count=claims,
                has_attachments=attachments,
            )
        )

    if len(labels) < 40:
        raise SystemExit(f"Need more labeled rows (have {len(labels)})")

    x_train, x_test, y_train, y_test = train_test_split(
        enriched,
        labels,
        test_size=0.15,
        random_state=42,
        stratify=labels,
    )
    x_train, x_val, y_train, y_val = train_test_split(
        x_train,
        y_train,
        test_size=0.176,
        random_state=42,
        stratify=y_train,
    )

    pipe = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(ngram_range=(1, 3), min_df=1, max_features=1200),
            ),
            (
                "clf",
                LogisticRegression(max_iter=600, class_weight="balanced", random_state=42),
            ),
        ]
    )
    pipe.fit(x_train, y_train)

    classes = [str(c) for c in pipe.named_steps["clf"].classes_]
    val_probs = pipe.predict_proba(x_val)
    val_pred = pipe.predict(x_val)
    test_pred = pipe.predict(x_test)

    def tune_thresholds(probs, y_true, class_names: list[str]) -> dict[str, float]:
        thresholds: dict[str, float] = {}
        for i, cls in enumerate(class_names):
            best_t = 0.42
            best_f1 = -1.0
            y_bin = [1 if y == cls else 0 for y in y_true]
            for t in np.linspace(0.25, 0.75, 21):
                pred_bin = [1 if probs[j][i] >= t else 0 for j in range(len(y_true))]
                f1 = f1_score(y_bin, pred_bin, zero_division=0)
                if f1 > best_f1:
                    best_f1 = f1
                    best_t = float(t)
            thresholds[cls] = round(best_t, 3)
        return thresholds

    class_thresholds = tune_thresholds(val_probs, y_val, classes)

    tfidf: TfidfVectorizer = pipe.named_steps["tfidf"]
    clf: LogisticRegression = pipe.named_steps["clf"]

    cm = confusion_matrix(y_test, test_pred, labels=classes)
    report = classification_report(y_test, test_pred, labels=classes, output_dict=True)

    payload = {
        "version": 2,
        "classes": classes,
        "vocabulary": {str(k): int(v) for k, v in tfidf.vocabulary_.items()},
        "idf": [float(x) for x in tfidf.idf_.tolist()],
        "coef": [[float(x) for x in row] for row in clf.coef_.tolist()],
        "intercept": [float(x) for x in clf.intercept_.tolist()],
        "n_train": len(y_train),
        "n_val": len(y_val),
        "n_test": len(y_test),
        "ngram_max": 3,
        "min_confidence": 0.42,
        "class_thresholds": class_thresholds,
    }

    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    MODEL_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {MODEL_OUT}")

    metrics = {
        "n_labeled": len(labels),
        "n_train": len(y_train),
        "n_val": len(y_val),
        "n_test": len(y_test),
        "class_thresholds": class_thresholds,
        "val_macro_f1": float(f1_score(y_val, val_pred, average="macro")),
        "test_macro_f1": float(f1_score(y_test, test_pred, average="macro")),
        "test_report": report,
        "test_confusion_matrix": {
            "labels": classes,
            "matrix": cm.tolist(),
        },
    }
    METRICS_OUT.parent.mkdir(parents=True, exist_ok=True)
    METRICS_OUT.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"Held-out macro-F1: {metrics['test_macro_f1']:.3f}")
    print(f"Wrote {METRICS_OUT}")


if __name__ == "__main__":
    main()
