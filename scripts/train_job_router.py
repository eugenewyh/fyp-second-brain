#!/usr/bin/env python3
"""Train the local Manager job router and write data/job_router/model.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

LABELED = ROOT / "data" / "job_router" / "labeled_turns.json"
MODEL_OUT = ROOT / "data" / "job_router" / "model.json"


def main() -> None:
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import classification_report
        from sklearn.model_selection import cross_val_score
        from sklearn.pipeline import Pipeline
    except ImportError as exc:
        raise SystemExit("Install scikit-learn: pip install scikit-learn") from exc

    rows = json.loads(LABELED.read_text(encoding="utf-8"))
    texts: list[str] = []
    labels: list[str] = []
    extras: list[str] = []

    for row in rows:
        text = str(row.get("text") or "").strip()
        job = str(row.get("job") or "").strip().lower()
        claims = int(row.get("claims") or 0)
        attachments = bool(row.get("attachments"))
        if not text or job not in {"file", "answer", "research", "refuse"}:
            continue
        texts.append(text)
        labels.append(job)
        claim_bucket = "c0" if claims <= 0 else "c1" if claims <= 2 else "c3"
        extras.append(f" claims={claim_bucket} attach={1 if attachments else 0}")

    enriched = [t + e for t, e in zip(texts, extras, strict=True)]

    pipe = Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=800)),
            (
                "clf",
                LogisticRegression(max_iter=400, class_weight="balanced", random_state=42),
            ),
        ]
    )
    scores = cross_val_score(pipe, enriched, labels, cv=5)
    print(f"5-fold accuracy: {scores.mean():.3f} (+/- {scores.std():.3f})")

    pipe.fit(enriched, labels)
    pred = pipe.predict(enriched)
    print(classification_report(labels, pred))

    tfidf: TfidfVectorizer = pipe.named_steps["tfidf"]
    clf: LogisticRegression = pipe.named_steps["clf"]

    payload = {
        "version": 1,
        "classes": [str(c) for c in clf.classes_],
        "vocabulary": {str(k): int(v) for k, v in tfidf.vocabulary_.items()},
        "idf": [float(x) for x in tfidf.idf_.tolist()],
        "coef": [[float(x) for x in row] for row in clf.coef_.tolist()],
        "intercept": [float(x) for x in clf.intercept_.tolist()],
        "n_train": len(labels),
    }
    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    MODEL_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {MODEL_OUT}")


if __name__ == "__main__":
    main()
