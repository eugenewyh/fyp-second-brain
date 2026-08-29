"""Feature enrichment for the local TF-IDF job router (train + inference)."""

from __future__ import annotations


def phase_bucket(matching_claim_count: int) -> str:
    if matching_claim_count <= 0:
        return "empty"
    if matching_claim_count <= 2:
        return "seed"
    return "ready"


def qlen_bucket(text: str) -> str:
    n = len((text or "").strip())
    if n < 28:
        return "short"
    if n < 120:
        return "medium"
    return "long"


def enrich_router_text(
    text: str,
    *,
    matching_claim_count: int,
    has_attachments: bool,
) -> str:
    claim_bucket = "c0" if matching_claim_count <= 0 else "c1" if matching_claim_count <= 2 else "c3"
    attach = 1 if has_attachments else 0
    phase = phase_bucket(matching_claim_count)
    qlen = qlen_bucket(text)
    qmark = 1 if "?" in text else 0
    return (
        f"{text.strip()} claims={claim_bucket} attach={attach} "
        f"phase={phase} qlen={qlen} qmark={qmark}"
    )
