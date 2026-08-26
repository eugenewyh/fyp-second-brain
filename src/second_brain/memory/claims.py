"""Durable project claim cards — inspectable beliefs with revision links."""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from langchain_core.documents import Document

from second_brain.ingestion.pipeline import ingest_file
from second_brain.memory.chroma_store import upsert_documents
from second_brain.memory.locks import ingest_lock
from second_brain.memory.learning import (
    LearningCard,
    _safe_session_id,
    _slugify,
    has_topic_path,
    project_memory_root,
)

logger = logging.getLogger(__name__)

# Jaccard token overlap above this revises an existing claim
SIMILARITY_THRESHOLD = 0.42
_STOP = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "of",
    "to",
    "in",
    "on",
    "for",
    "is",
    "are",
    "was",
    "were",
    "be",
    "with",
    "that",
    "this",
    "as",
    "by",
    "from",
    "it",
    "its",
}


# Near-identical restatement of an existing claim (same dump / hash) — do not mint a new slug
IDENTICAL_THRESHOLD = 0.85
MAX_CLAIMS_PER_DUMP = 7
# dump = taught; watch/research = agent. Watch cannot clobber dump.
ORIGIN_DUMP = "dump"
ORIGIN_WATCH = "watch"
ORIGIN_RESEARCH = "research"
PROTECTED_ORIGINS = {ORIGIN_DUMP}
SETTLED_STATUSES = {"settled", "active"}  # active = legacy settled
LIVE_STATUSES = {"settled", "active", "contested"}
WATCH_TTL_DAYS = 30


@dataclass
class SourcedClaim:
    """Atomic claim grounded in a verbatim span of the source dump."""

    claim: str
    source_quote: str


@dataclass
class ClaimCard:
    id: str
    claim: str
    confidence: float = 0.5
    status: str = "settled"  # settled | active (legacy) | contested | superseded
    origin: str = ORIGIN_RESEARCH  # dump | watch | research
    supersedes: str | None = None
    session_id: str | None = None
    report_path: str | None = None
    learning_id: str | None = None
    evidence: list[str] = field(default_factory=list)
    path: str | None = None
    slug: str = ""
    updated: str = ""
    created: str = ""
    source_quote: str = ""
    source_path: str | None = None
    content_hash: str = ""
    expires: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ClaimUpsertResult:
    created: list[ClaimCard] = field(default_factory=list)
    revised: list[ClaimCard] = field(default_factory=list)
    unchanged: list[ClaimCard] = field(default_factory=list)

    @property
    def all_cards(self) -> list[ClaimCard]:
        return [*self.created, *self.revised, *self.unchanged]


def claims_dir(project_path: str | None = None) -> Path:
    return project_memory_root(project_path) / "claims"


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w for w in words if len(w) > 2 and w not in _STOP}


def claim_similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


def _split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta: dict[str, str] = {}
    for line in parts[1].strip().splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, parts[2]


def _parse_claim_file(path: Path) -> ClaimCard | None:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    meta, body = _split_frontmatter(raw)
    claim = (meta.get("claim") or "").strip()
    if not claim:
        # Fallback: first non-empty body line after heading
        for line in body.splitlines():
            line = line.strip()
            if line.startswith("#"):
                continue
            if line:
                claim = line.lstrip("- ").strip()
                break
    if not claim:
        return None
    evidence_raw = meta.get("evidence") or ""
    evidence = [e.strip() for e in evidence_raw.split(",") if e.strip()]
    try:
        conf = float(meta.get("confidence") or 0.5)
    except ValueError:
        conf = 0.5
    return ClaimCard(
        id=meta.get("id") or path.stem,
        claim=claim,
        confidence=conf,
        status=(meta.get("status") or "settled").strip().lower(),
        origin=_parse_origin(meta.get("origin")),
        supersedes=meta.get("supersedes") or None,
        session_id=meta.get("session_id") or None,
        report_path=meta.get("report_path") or None,
        learning_id=meta.get("learning_id") or None,
        evidence=evidence,
        path=str(path.resolve()),
        slug=path.stem,
        updated=meta.get("updated") or "",
        created=meta.get("created") or meta.get("updated") or "",
        source_quote=meta.get("source_quote") or meta.get("span") or "",
        source_path=meta.get("source_path") or None,
        content_hash=meta.get("content_hash") or "",
        expires=meta.get("expires") or "",
    )


def list_claims(
    project_path: str | None = None,
    *,
    status: str | None = "active",
) -> list[ClaimCard]:
    directory = claims_dir(project_path)
    if not directory.is_dir():
        return []
    out: list[ClaimCard] = []
    for path in sorted(directory.glob("*.md")):
        card = _parse_claim_file(path)
        if not card:
            continue
        if status is not None:
            if status in SETTLED_STATUSES:
                if card.status not in SETTLED_STATUSES:
                    continue
            elif card.status != status:
                continue
        out.append(card)
    return out


def extract_claims_from_learning(card: LearningCard, *, limit: int = 3) -> list[str]:
    """Pull 1–3 short claim strings from findings / summary."""
    claims: list[str] = []
    for finding in card.key_findings:
        text = re.sub(r"^[-*•]\s+", "", (finding or "").strip())
        if len(text) < 12:
            continue
        if len(text) > 220:
            text = text[:217] + "…"
        claims.append(text)
        if len(claims) >= limit:
            break
    if not claims and (card.summary or "").strip():
        summary = card.summary.strip()
        # Split on sentence boundaries lightly
        parts = re.split(r"(?<=[.!?])\s+", summary)
        for p in parts:
            p = p.strip()
            if len(p) < 12:
                continue
            if len(p) > 220:
                p = p[:217] + "…"
            claims.append(p)
            if len(claims) >= limit:
                break
    if not claims and card.query:
        claims.append(f"Research completed on: {card.query[:160]}")
    return claims[:limit]


def _yaml_escape(value: str) -> str:
    return (value or "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def _claim_markdown(card: ClaimCard, *, revises_slug: str | None = None) -> str:
    evidence = ", ".join(card.evidence) if card.evidence else ""
    revises_line = f"Revises [[{revises_slug}]]\n" if revises_slug else ""
    quote_block = ""
    if (card.source_quote or "").strip():
        quote_block = f"> {card.source_quote.strip()}\n"
    return "\n".join(
        [
            "---",
            f"id: {card.id}",
            f'type: claim',
            f'claim: "{_yaml_escape(card.claim)}"',
            f"confidence: {card.confidence}",
            f"status: {card.status}",
            f"origin: {card.origin or ORIGIN_RESEARCH}",
            f"created: {card.created or card.updated}",
            f'supersedes: "{card.supersedes or ""}"',
            f'session_id: "{card.session_id or ""}"',
            f'report_path: "{_yaml_escape(card.report_path or "")}"',
            f'learning_id: "{card.learning_id or ""}"',
            f'evidence: "{_yaml_escape(evidence)}"',
            f'source_quote: "{_yaml_escape(card.source_quote)}"',
            f'source_path: "{_yaml_escape(card.source_path or "")}"',
            f'content_hash: "{card.content_hash or ""}"',
            f'expires: "{card.expires or ""}"',
            f"updated: {card.updated}",
            'tags: ["claim", "agent-memory", "auto-generated"]',
            "---",
            "",
            f"# What we know",
            "",
            revises_line,
            card.claim,
            "",
            quote_block,
            "How sure: from your notes",
            "",
        ]
    )


def _write_claim_file(
    card: ClaimCard,
    *,
    project_path: str | None,
    revises_slug: str | None = None,
    ingest: bool = True,
) -> ClaimCard:
    if not has_topic_path(project_path):
        logger.info("Skipping claim write: no topic bound")
        return card
    with ingest_lock(project_path):
        return _write_claim_file_unlocked(
            card,
            project_path=project_path,
            revises_slug=revises_slug,
            ingest=ingest,
        )


def _write_claim_file_unlocked(
    card: ClaimCard,
    *,
    project_path: str | None,
    revises_slug: str | None = None,
    ingest: bool = True,
) -> ClaimCard:
    directory = claims_dir(project_path)
    directory.mkdir(parents=True, exist_ok=True)
    slug = card.slug or _slugify(card.claim)[:48]
    # Avoid collisions for new claims
    path = directory / f"{slug}.md"
    if not card.slug and path.exists():
        slug = f"{slug}-{card.id[:6]}"
        path = directory / f"{slug}.md"
    card.slug = slug
    card.path = str(path.resolve())
    path.write_text(_claim_markdown(card, revises_slug=revises_slug), encoding="utf-8")
    if ingest:
        try:
            ingest_file(path)
        except Exception:
            logger.exception("Failed to ingest claim %s", path)
            try:
                upsert_documents(
                    [
                        Document(
                            page_content=f"Claim: {card.claim}",
                            metadata={
                                "source": path.name,
                                "source_path": str(path.resolve()),
                                "chunk_index": 0,
                                "doc_type": "claim",
                                "session_id": card.session_id or "",
                                "page": -1,
                            },
                        )
                    ]
                )
            except Exception:
                logger.exception("Fallback claim upsert failed")
    return card


def _mark_superseded(
    old: ClaimCard,
    *,
    project_path: str | None,
    ingest: bool = True,
) -> None:
    if not old.path:
        return
    path = Path(old.path)
    if not path.is_file():
        return
    old.status = "superseded"
    old.updated = datetime.now(timezone.utc).isoformat()
    path.write_text(_claim_markdown(old), encoding="utf-8")
    if ingest:
        try:
            ingest_file(path)
        except Exception:
            logger.exception("Failed to re-ingest superseded claim %s", path)


def _parse_origin(raw: str | None) -> str:
    v = (raw or "").strip().lower()
    if v in {ORIGIN_DUMP, ORIGIN_WATCH, ORIGIN_RESEARCH}:
        return v
    return ORIGIN_RESEARCH


def _is_protected(card: ClaimCard) -> bool:
    return (card.origin or "") in PROTECTED_ORIGINS


def default_watch_expires(*, days: int = WATCH_TTL_DAYS) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=max(1, days))).date().isoformat()


def _parse_expires(raw: str | None) -> datetime | None:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        if "T" in text:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        day = datetime.fromisoformat(text).date()
        return datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    except ValueError:
        return None


def expire_watch_claims(
    project_path: str | None,
    *,
    now: datetime | None = None,
    ingest: bool = False,
) -> int:
    """Archive expired watch-only claims. Never dump or settled research."""
    if not has_topic_path(project_path):
        return 0
    now = now or datetime.now(timezone.utc)
    archived = 0
    for card in list_claims(project_path, status=None):
        if (card.origin or "") != ORIGIN_WATCH:
            continue
        if card.status == "superseded":
            continue
        if card.status == "contested":
            continue
        expires_at = _parse_expires(card.expires)
        if expires_at is None or expires_at > now:
            continue
        _mark_superseded(card, project_path=project_path, ingest=ingest)
        archived += 1
    return archived


def expire_watch_claims_in_vault(documents_dir: Path | None = None, *, ingest: bool = False) -> int:
    """Walk topic folders under the vault and expire watch claims in each."""
    from second_brain.config import DOCUMENTS_DIR

    root = documents_dir or DOCUMENTS_DIR
    if not root.is_dir():
        return 0
    total = 0
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        if not (child / "memory" / "claims").is_dir():
            continue
        total += expire_watch_claims(str(child), ingest=ingest)
    return total


def upsert_claims_from_learning(
    card: LearningCard,
    *,
    project_path: str | None = None,
    session_id: str | None = None,
    ingest: bool = True,
    origin: str = ORIGIN_RESEARCH,
    mint_settled: bool = True,
    expires: str | None = None,
) -> list[ClaimCard]:
    """Create or revise claim cards from a learning card. Returns new/updated active claims."""
    if not has_topic_path(project_path):
        logger.info("Skipping claim upsert: no topic bound")
        return []
    texts = extract_claims_from_learning(card)
    if not texts:
        return []

    existing = list_claims(project_path, status="active")
    sid = _safe_session_id(session_id or card.session_id)
    evidence: list[str] = []
    if card.report_path:
        stem = Path(card.report_path).stem
        if stem:
            evidence.append(stem)
    if card.learning_path:
        stem = Path(card.learning_path).stem
        if stem and stem not in evidence:
            evidence.append(stem)

    now = datetime.now(timezone.utc).isoformat()
    origin = _parse_origin(origin)
    expires_val = (expires or "").strip()
    if origin == ORIGIN_WATCH and not expires_val:
        expires_val = default_watch_expires()
    if origin != ORIGIN_WATCH:
        expires_val = ""
    results: list[ClaimCard] = []

    def _new_card(text: str, *, status: str, supersedes: str | None = None) -> ClaimCard:
        return ClaimCard(
            id=uuid4().hex[:12],
            claim=text,
            confidence=card.confidence,
            status=status,
            origin=origin,
            supersedes=supersedes,
            session_id=sid,
            report_path=card.report_path,
            learning_id=card.id,
            evidence=evidence,
            updated=now,
            created=now,
            expires=expires_val,
        )

    for text in texts:
        best: ClaimCard | None = None
        best_score = 0.0
        for old in existing:
            score = claim_similarity(text, old.claim)
            if score > best_score:
                best_score = score
                best = old

        if best and best_score >= SIMILARITY_THRESHOLD and _is_protected(best) and origin != ORIGIN_DUMP:
            if best_score >= IDENTICAL_THRESHOLD:
                result_skip = best
                results.append(result_skip)
                continue
            contested = _write_claim_file(
                _new_card(text, status="contested"),
                project_path=project_path,
                ingest=ingest,
            )
            existing.append(contested)
            results.append(contested)
            logger.info("Contested dump claim %s with %s (sim=%.2f)", best.id, contested.id, best_score)
            continue

        if best and best_score >= SIMILARITY_THRESHOLD and not mint_settled:
            contested = _write_claim_file(
                _new_card(text, status="contested"),
                project_path=project_path,
                ingest=ingest,
            )
            existing.append(contested)
            results.append(contested)
            continue

        if best and best_score >= SIMILARITY_THRESHOLD:
            _mark_superseded(best, project_path=project_path, ingest=ingest)
            # Remove from active pool so further texts don't match it again
            existing = [c for c in existing if c.id != best.id]
            new = _write_claim_file(
                _new_card(text, status="settled", supersedes=best.id),
                project_path=project_path,
                revises_slug=best.slug,
                ingest=ingest,
            )
            existing.append(new)
            results.append(new)
            logger.info(
                "Revised claim %s → %s (sim=%.2f)",
                best.id,
                new.id,
                best_score,
            )
        else:
            status = "settled" if mint_settled else "contested"
            new = _write_claim_file(
                _new_card(text, status=status),
                project_path=project_path,
                ingest=ingest,
            )
            existing.append(new)
            results.append(new)

    return results


def upsert_sourced_claims(
    sourced: list[SourcedClaim],
    *,
    project_path: str | None = None,
    session_id: str | None = None,
    source_path: str | None = None,
    content_hash: str = "",
    neighbors: list[ClaimCard] | None = None,
    ingest: bool = True,
    confidence: float = 0.55,
    origin: str = ORIGIN_DUMP,
) -> ClaimUpsertResult:
    """Create or revise claims from a Remember dump. Prefer revise; skip identical re-dumps."""
    result = ClaimUpsertResult()
    if not sourced or not has_topic_path(project_path):
        return result

    existing = list_claims(project_path, status="active")
    sid = _safe_session_id(session_id)
    evidence: list[str] = []
    if source_path:
        stem = Path(source_path).stem
        if stem:
            evidence.append(stem)
    now = datetime.now(timezone.utc).isoformat()
    origin = _parse_origin(origin)
    neighbor_ids = {c.id for c in (neighbors or []) if c.id}

    for item in sourced[:MAX_CLAIMS_PER_DUMP]:
        text = (item.claim or "").strip()
        if len(text) < 12:
            continue

        best: ClaimCard | None = None
        best_score = 0.0
        for old in existing:
            score = claim_similarity(text, old.claim)
            # Recalled neighbors win ties so dumps revise known beliefs
            if score > best_score or (
                score == best_score and best and old.id in neighbor_ids and best.id not in neighbor_ids
            ):
                best_score = score
                best = old

        if best and best_score >= IDENTICAL_THRESHOLD:
            # Same belief — keep slug; refresh quote/hash in place
            best.source_quote = item.source_quote or best.source_quote
            best.origin = origin or best.origin
            best.status = "settled"
            best.source_path = source_path or best.source_path
            best.content_hash = content_hash or best.content_hash
            best.updated = now
            if stem := (Path(source_path).stem if source_path else ""):
                if stem not in best.evidence:
                    best.evidence = [*best.evidence, stem]
            _write_claim_file(best, project_path=project_path, ingest=ingest)
            result.unchanged.append(best)
            continue

        if best and best_score >= SIMILARITY_THRESHOLD:
            _mark_superseded(best, project_path=project_path, ingest=ingest)
            existing = [c for c in existing if c.id != best.id]
            new = ClaimCard(
                id=uuid4().hex[:12],
                claim=text,
                confidence=confidence,
                status="settled",
                origin=origin,
                supersedes=best.id,
                session_id=sid,
                evidence=evidence,
                updated=now,
                source_quote=item.source_quote,
                source_path=source_path,
                content_hash=content_hash,
            )
            new = _write_claim_file(
                new,
                project_path=project_path,
                revises_slug=best.slug,
                ingest=ingest,
            )
            existing.append(new)
            result.revised.append(new)
            logger.info("Revised claim %s → %s (sim=%.2f)", best.id, new.id, best_score)
            continue

        new = ClaimCard(
            id=uuid4().hex[:12],
            claim=text,
            confidence=confidence,
            status="settled",
            origin=origin,
            session_id=sid,
            evidence=evidence,
            updated=now,
            source_quote=item.source_quote,
            source_path=source_path,
            content_hash=content_hash,
        )
        new = _write_claim_file(new, project_path=project_path, ingest=ingest)
        existing.append(new)
        result.created.append(new)

    return result


def claims_matching_query(
    query: str,
    project_path: str | None = None,
    *,
    limit: int = 5,
) -> list[ClaimCard]:
    """Rank settled then contested claims by token overlap with the query.

    Settled matches fill the budget first; contested siblings share the same
    similarity gate so Ask can surface disagreements without crowding them out.
    """
    settled = list_claims(project_path, status="active")
    contested = list_claims(project_path, status="contested")

    def _scored(cards: list[ClaimCard]) -> list[tuple[float, ClaimCard]]:
        scored = [(claim_similarity(query, c.claim), c) for c in cards]
        scored = [(s, c) for s, c in scored if s > 0.05]
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored

    out: list[ClaimCard] = []
    for _, c in _scored(settled):
        if len(out) >= limit:
            break
        out.append(c)
    for _, c in _scored(contested):
        if len(out) >= limit:
            break
        out.append(c)
    return out


def merge_topic_claims(
    source_path: str,
    dest_path: str,
    *,
    ingest: bool = True,
) -> dict[str, Any]:
    """Copy claims from source into dest. Rewrite supersedes. Do not delete source."""
    if not has_topic_path(source_path) or not has_topic_path(dest_path):
        return {"copied": 0, "skipped": 0, "source": source_path, "dest": dest_path}
    src = str(Path(source_path).expanduser())
    dest = str(Path(dest_path).expanduser())
    if Path(src).resolve() == Path(dest).resolve():
        return {"copied": 0, "skipped": 0, "source": src, "dest": dest}

    source_cards = list_claims(src, status=None)
    dest_cards = list_claims(dest, status=None)
    dest_by_id = {c.id: c for c in dest_cards}
    copied = 0
    skipped = 0
    id_map: dict[str, str] = {}

    pending: list[ClaimCard] = []
    for card in source_cards:
        twin = next(
            (d for d in dest_cards if claim_similarity(card.claim, d.claim) >= IDENTICAL_THRESHOLD),
            None,
        )
        if twin:
            id_map[card.id] = twin.id
            skipped += 1
            continue
        new_id = card.id if card.id not in dest_by_id else uuid4().hex[:12]
        id_map[card.id] = new_id
        slug = card.slug or _slugify(card.claim)[:48]
        dest_file = claims_dir(dest) / f"{slug}.md"
        if dest_file.exists() and dest_by_id.get(card.id) is None:
            slug = f"{slug}-{new_id[:6]}"
        pending.append(
            replace(
                card,
                id=new_id,
                slug=slug,
                path=None,
                supersedes=card.supersedes,
            )
        )

    for card in pending:
        mapped = id_map.get(card.supersedes or "", card.supersedes)
        card = replace(card, supersedes=mapped)
        _write_claim_file(card, project_path=dest, ingest=ingest)
        copied += 1

    if copied:
        from second_brain.memory.learning import project_memory_path

        note = (
            f"\n\n## Merged from {Path(src).name}\n\n"
            f"Copied {copied} claim(s). Source folder was not deleted.\n"
        )
        mem = project_memory_path(dest)
        mem.parent.mkdir(parents=True, exist_ok=True)
        prior = mem.read_text(encoding="utf-8") if mem.is_file() else "# Project memory\n"
        mem.write_text(prior.rstrip() + note, encoding="utf-8")

    return {
        "copied": copied,
        "skipped": skipped,
        "source": src,
        "dest": dest,
        "source_name": Path(src).name,
        "dest_name": Path(dest).name,
    }
