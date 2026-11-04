"""Remember-path: digest a dump into sourced claims and wikilinks (no LearningCards)."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from second_brain.config import SUPPORTED_EXTENSIONS
from second_brain.ingestion.loaders import load_file
from second_brain.ingestion.pipeline import ingest_file
from second_brain.ingestion.sections import ensure_section_summaries, infer_project_from_source
from second_brain.memory.claims import (
    MAX_CLAIMS_PER_DUMP,
    ClaimCard,
    SourcedClaim,
    claims_matching_query,
    list_claims,
    upsert_sourced_claims,
)
from second_brain.memory.learning import (
    LearningCard,
    _UNBOUND_TOPIC,
    _safe_session_id,
    _slugify,
    consolidate_project_memory,
    has_topic_path,
    project_memory_root,
    update_agent_session_memory,
)

logger = logging.getLogger(__name__)

MAX_CLAIMS = MAX_CLAIMS_PER_DUMP  # 7
MIN_TARGET_CLAIMS = 3
DIGEST_INDEX_NAME = "digest-index.json"

_SKIP_PATH_MARKERS = (
    "/memory/",
    "/memory/claims/",
    "/memory/digests/",
    "/memory/learnings/",
    "/memory/agents/",
    "/research/",
    "/briefs/",
    "/watches/",
    "/instruction.md",
    "\\memory\\",
    "\\memory\\claims\\",
    "\\memory\\digests\\",
    "\\memory\\learnings\\",
    "\\memory\\agents\\",
    "\\research\\",
    "\\watches\\",
)

_LINKED_SECTION = re.compile(r"(?is)\n##\s*Linked\s*\n.*\Z")
_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```")
_WS = re.compile(r"\s+")


@dataclass
class DigestResult:
    saved_path: str
    content_hash: str
    idempotent: bool = False
    claims_created: int = 0
    claims_revised: int = 0
    claims_dropped: int = 0
    linked_sources: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    summary: str = ""
    claim_slugs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_for_hash(text: str) -> str:
    return _WS.sub(" ", (text or "").strip())


def content_hash(text: str) -> str:
    return hashlib.sha256(normalize_for_hash(text).encode("utf-8")).hexdigest()


def quote_in_source(quote: str, source: str) -> bool:
    q = normalize_for_hash(quote)
    s = normalize_for_hash(source)
    return bool(q) and len(q) >= 12 and q.lower() in s.lower()


def is_memory_trace_path(path: Path | str) -> bool:
    raw = str(path).replace("\\", "/").lower()
    if raw.endswith("/digest-index.json") or raw.endswith("digest-index.json"):
        return True
    padded = f"/{raw.strip('/')}/"
    return any(m.replace("\\", "/") in padded or m.replace("\\", "/") in raw for m in _SKIP_PATH_MARKERS)


def _inbox_dir(project_path: str | None) -> Path:
    if has_topic_path(project_path):
        return Path(str(project_path).strip()).expanduser() / "inbox"
    return _UNBOUND_TOPIC / "inbox"


def _vault_root(project_path: str | None) -> Path:
    if has_topic_path(project_path):
        return Path(str(project_path).strip()).expanduser()
    return _UNBOUND_TOPIC


def _under_vault(path: Path, project_path: str | None) -> bool:
    try:
        path.resolve().relative_to(_vault_root(project_path).resolve())
        return True
    except ValueError:
        return False


def _index_path(project_path: str | None) -> Path:
    return project_memory_root(project_path) / DIGEST_INDEX_NAME


def _load_index(project_path: str | None) -> dict[str, Any]:
    path = _index_path(project_path)
    if not path.is_file():
        return {"by_hash": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"by_hash": {}}
    if not isinstance(data, dict):
        return {"by_hash": {}}
    by_hash = data.get("by_hash")
    if not isinstance(by_hash, dict):
        data["by_hash"] = {}
    return data


def _save_index(project_path: str | None, data: dict[str, Any]) -> None:
    path = _index_path(project_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _load_text(path: Path) -> str:
    docs = load_file(path)
    parts = [(d.page_content or "").strip() for d in docs if (d.page_content or "").strip()]
    return "\n\n".join(parts)


def _heuristic_claims(text: str, *, limit: int = MIN_TARGET_CLAIMS) -> list[SourcedClaim]:
    parts = re.split(r"(?<=[.!?])\s+", normalize_for_hash(text))
    out: list[SourcedClaim] = []
    for sent in parts:
        sent = sent.strip()
        if len(sent) < 40:
            continue
        claim = sent if len(sent) <= 220 else sent[:217] + "…"
        quote = sent if len(sent) <= 280 else sent[:277] + "…"
        if not quote_in_source(quote.rstrip("…"), text) and not quote_in_source(sent[:80], text):
            # Use a verified window from the original
            window = text[text.lower().find(sent[:40].lower()) :][:180].strip()
            if not quote_in_source(window, text):
                continue
            quote = window
        out.append(SourcedClaim(claim=claim, source_quote=quote))
        if len(out) >= limit:
            break
    return out


def _parse_claim_payload(raw: str) -> list[dict[str, str]]:
    text = (raw or "").strip()
    if not text:
        return []
    m = _JSON_FENCE.search(text)
    if m:
        text = m.group(1).strip()
    # Tolerate a leading/trailing prose wrapper
    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        data = data.get("claims") or data.get("items") or []
    if not isinstance(data, list):
        return []
    out: list[dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        claim = str(item.get("claim") or item.get("text") or "").strip()
        quote = str(item.get("source_quote") or item.get("quote") or "").strip()
        if claim:
            out.append({"claim": claim, "source_quote": quote})
    return out


def extract_sourced_claims(
    text: str,
    *,
    neighbors: list[ClaimCard] | None = None,
    limit: int | None = None,
) -> list[SourcedClaim]:
    """Fast-LLM extract; drop unverifiable quotes. Cap at `limit` (default MAX_CLAIMS)."""
    cap = MAX_CLAIMS if limit is None else max(1, min(int(limit), 24))
    lo = min(3, cap)
    neighbor_block = ""
    if neighbors:
        lines = [f"- {c.claim}" for c in neighbors[:8] if c.claim]
        if lines:
            neighbor_block = (
                "Existing neighboring claims (prefer restating these so they can be revised):\n"
                + "\n".join(lines)
                + "\n\n"
            )
    prompt = (
        f"Extract {lo} to {cap} atomic factual claims from the note. "
        "Write each claim as a plain factual sentence a non-expert can read. "
        "Do not introduce field jargon the source does not use. "
        "Each claim MUST include a verbatim source_quote copied from the note. "
        "Do not invent quotes. Prefer revising a neighbor over creating a duplicate idea. "
        'Return JSON only: [{"claim": "...", "source_quote": "..."}]\n\n'
        f"{neighbor_block}"
        f"Note:\n{text[:8000]}"
    )
    raw = ""
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from second_brain.memory.llm import invoke_llm

        resp = invoke_llm(
            [
                SystemMessage(
                    content="You extract grounded claims for a personal knowledge base. "
                    "Each claim is a plain sentence a non-expert can read. JSON only."
                ),
                HumanMessage(content=prompt),
            ],
            role="fast",
        )
        raw = resp.content if isinstance(resp.content, str) else str(resp.content)
    except Exception:
        logger.debug("Claim LLM extract skipped", exc_info=True)

    parsed = _parse_claim_payload(raw)
    sourced: list[SourcedClaim] = []
    for item in parsed:
        quote = item.get("source_quote") or ""
        claim = item.get("claim") or ""
        if not quote_in_source(quote, text):
            continue
        if len(claim) > 220:
            claim = claim[:217] + "…"
        sourced.append(SourcedClaim(claim=claim, source_quote=quote[:400]))
        if len(sourced) >= cap:
            break

    if not sourced:
        sourced = _heuristic_claims(text)

    verified: list[SourcedClaim] = []
    for item in sourced:
        if quote_in_source(item.source_quote, text):
            verified.append(item)
        if len(verified) >= cap:
            break
    return verified


def _write_inbox_note(
    *,
    text: str,
    title: str,
    content_hash_value: str,
    project_path: str | None,
    dest: Path,
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    body = text.strip()
    if dest.suffix.lower() == ".md":
        fm = "\n".join(
            [
                "---",
                "type: inbox",
                f'title: "{title.replace(chr(34), "")}"',
                f"content_hash: {content_hash_value}",
                f"updated: {now}",
                "---",
                "",
            ]
        )
        if body.startswith("---"):
            dest.write_text(body + "\n", encoding="utf-8")
        else:
            dest.write_text(fm + body + "\n", encoding="utf-8")
        return
    dest.write_text(body + "\n", encoding="utf-8")


def _replace_linked_section(path: Path, slugs: list[str], linked_stems: list[str]) -> None:
    if path.suffix.lower() not in {".md", ".txt"}:
        return
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    links: list[str] = []
    seen: set[str] = set()
    for slug in slugs:
        key = slug.lower()
        if not slug or key in seen:
            continue
        seen.add(key)
        links.append(f"- [[{slug}]]")
    for stem in linked_stems:
        key = stem.lower()
        if not stem or key in seen:
            continue
        seen.add(key)
        links.append(f"- [[{stem}]]")
    if not links:
        links = ["- (none yet)"]
    section = "\n## Linked\n\n" + "\n".join(links) + "\n"
    if _LINKED_SECTION.search(text):
        text = _LINKED_SECTION.sub(section, text)
    else:
        text = text.rstrip() + "\n" + section
    path.write_text(text, encoding="utf-8")


def _neighbor_claims(text: str, project_path: str | None) -> list[ClaimCard]:
    excerpt = text[:500]
    matched = claims_matching_query(excerpt, project_path, limit=8)
    if matched:
        return matched
    return list_claims(project_path, status="active")[:8]


def _ingest_paths(paths: list[Path]) -> None:
    seen: set[str] = set()
    for path in paths:
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen:
            continue
        seen.add(key)
        try:
            ingest_file(path)
        except Exception:
            logger.debug("Ingest failed for %s", path, exc_info=True)


def _collect_claim_ingest_paths(
    upsert: Any,
    *,
    project_path: str | None,
) -> list[Path]:
    paths: list[Path] = []
    for card in upsert.all_cards:
        if card.path:
            paths.append(Path(card.path))
    superseded_ids = {c.supersedes for c in upsert.revised if c.supersedes}
    if superseded_ids:
        for old in list_claims(project_path, status=None):
            if old.id in superseded_ids and old.path:
                paths.append(Path(old.path))
    return paths


def _digest_summary(
    *,
    idempotent: bool,
    created: int,
    revised: int,
    unchanged_count: int,
    extracted: list[SourcedClaim],
) -> str:
    summary_bits: list[str] = []
    if idempotent:
        summary_bits.append("Already remembered this dump")
    if created:
        summary_bits.append(f"{created} new claim" + ("s" if created != 1 else ""))
    if revised:
        summary_bits.append(f"{revised} revised")
    if unchanged_count:
        summary_bits.append(f"{unchanged_count} unchanged")
    if not extracted:
        summary_bits.append("No sourced claims (quotes did not verify)")
    return " · ".join(summary_bits) or "Remembered"


def digest_and_link(
    *,
    text: str | None = None,
    title: str | None = None,
    path: str | None = None,
    project_path: str | None = None,
    session_id: str | None = None,
    ingest: bool = True,
) -> DigestResult:
    """Save (or reuse) a dump, extract sourced claims, link, consolidate project.md."""
    if not has_topic_path(project_path):
        raise ValueError("project_path is required to remember notes")
    source_path: Path | None = Path(path).expanduser() if path and str(path).strip() else None
    if source_path and is_memory_trace_path(source_path):
        raise ValueError("Refusing to digest memory or research traces")

    body = (text or "").strip()
    if not body and source_path:
        if not source_path.is_file():
            raise FileNotFoundError(f"Not a file: {source_path}")
        suffix = source_path.suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {suffix}")
        body = _load_text(source_path)
    if not body:
        raise ValueError("Nothing to remember — provide text or a file path")

    digest_hash = content_hash(body)
    index = _load_index(project_path)
    by_hash: dict[str, Any] = index.setdefault("by_hash", {})
    prior = by_hash.get(digest_hash) if isinstance(by_hash.get(digest_hash), dict) else None
    idempotent = False
    saved: Path

    if prior and prior.get("path"):
        existing = Path(str(prior["path"]))
        if existing.is_file():
            claim_ids = prior.get("claim_ids") or []
            if claim_ids:
                return DigestResult(
                    saved_path=str(existing.resolve()),
                    content_hash=digest_hash,
                    idempotent=True,
                    summary="Already remembered this dump",
                )
            saved = existing
            idempotent = True
        else:
            saved = _place_dump(
                body=body,
                title=title,
                source_path=source_path,
                project_path=project_path,
                digest_hash=digest_hash,
            )
    else:
        saved = _place_dump(
            body=body,
            title=title,
            source_path=source_path,
            project_path=project_path,
            digest_hash=digest_hash,
        )

    if not ingest:
        try:
            ensure_section_summaries(saved, project_path=project_path or infer_project_from_source(saved))
        except Exception:
            logger.debug("Section summaries skipped for %s", saved, exc_info=True)

    neighbors = _neighbor_claims(body, project_path)
    extracted = extract_sourced_claims(body, neighbors=neighbors)
    dropped = 0
    if len(extracted) > MAX_CLAIMS:
        dropped += len(extracted) - MAX_CLAIMS
        extracted = extracted[:MAX_CLAIMS]

    upsert = upsert_sourced_claims(
        extracted,
        project_path=project_path,
        session_id=session_id,
        source_path=str(saved.resolve()),
        content_hash=digest_hash,
        neighbors=neighbors,
        ingest=False,
    )

    slugs = [c.slug for c in upsert.all_cards if c.slug]
    linked_stems: list[str] = []
    for c in neighbors:
        stem = Path(c.path).stem if c.path else c.slug
        if stem:
            linked_stems.append(stem)
    _replace_linked_section(saved, slugs, linked_stems[:8])

    created = len(upsert.created)
    revised = len(upsert.revised)
    summary = _digest_summary(
        idempotent=idempotent,
        created=created,
        revised=revised,
        unchanged_count=len(upsert.unchanged),
        extracted=extracted,
    )

    card = LearningCard(
        id="digest",
        query=title or saved.stem,
        summary=summary,
        open_questions=[],
        confidence=0.55,
        session_id=_safe_session_id(session_id),
        project_path=project_path,
    )
    project_md: Path | None = None
    try:
        project_md = consolidate_project_memory(
            card,
            project_path=project_path,
            session_id=session_id,
            claim_slugs=slugs,
            ingest=False,
            polish=False,
        )
    except Exception:
        logger.exception("project.md consolidate failed after digest")
    session_md: Path | None = None
    sid = _safe_session_id(session_id)
    if sid:
        try:
            session_md = update_agent_session_memory(
                card,
                project_path=project_path,
                session_id=sid,
                claim_slugs=slugs,
                ingest=False,
            )
        except Exception:
            logger.exception("chat memory.md update failed after digest")

    by_hash[digest_hash] = {
        "path": str(saved.resolve()),
        "claim_ids": [c.id for c in upsert.all_cards],
        "updated": datetime.now(timezone.utc).isoformat(),
    }
    _save_index(project_path, index)

    if ingest:
        to_ingest = [saved, *_collect_claim_ingest_paths(upsert, project_path=project_path)]
        if project_md is not None:
            to_ingest.append(project_md)
        if session_md is not None:
            to_ingest.append(session_md)
        _ingest_paths(to_ingest)

    return DigestResult(
        saved_path=str(saved.resolve()),
        content_hash=digest_hash,
        idempotent=idempotent,
        claims_created=created,
        claims_revised=revised,
        claims_dropped=dropped,
        linked_sources=linked_stems[:8],
        open_questions=[],
        summary=summary,
        claim_slugs=slugs,
    )


@dataclass
class _DumpUnit:
    body: str
    title: str | None
    source_path: Path | None
    digest_hash: str
    saved: Path
    idempotent: bool
    early: DigestResult | None = None


def digest_many(
    *,
    text: str | None = None,
    title: str | None = None,
    paths: list[str] | None = None,
    project_path: str | None = None,
    session_id: str | None = None,
    ingest: bool = True,
) -> dict[str, Any]:
    """Batch remember: one claim extract across dumps, one consolidate, batch ingest."""
    if not has_topic_path(project_path):
        raise ValueError("project_path is required to remember notes")

    units: list[_DumpUnit] = []
    body_text = (text or "").strip()
    if body_text:
        units.append(
            _prepare_dump_unit(
                body=body_text,
                title=title,
                source_path=None,
                project_path=project_path,
            )
        )
    for raw in paths or []:
        source_path = Path(raw).expanduser()
        if is_memory_trace_path(source_path):
            raise ValueError("Refusing to digest memory or research traces")
        if not source_path.is_file():
            raise FileNotFoundError(f"Not a file: {source_path}")
        suffix = source_path.suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {suffix}")
        loaded = _load_text(source_path)
        if not loaded.strip():
            continue
        units.append(
            _prepare_dump_unit(
                body=loaded,
                title=title,
                source_path=source_path,
                project_path=project_path,
            )
        )

    if not units:
        raise ValueError("Nothing to remember — provide text or a file path")

    early_results = [u.early for u in units if u.early is not None]
    work = [u for u in units if u.early is None]
    if not work:
        return _aggregate_digest_results(early_results)

    combined_parts = [f"# {u.saved.stem}\n{u.body[:3000]}" for u in work]
    combined = "\n\n---\n\n".join(combined_parts)[:12000]
    neighbors = _neighbor_claims(combined, project_path)
    batch_cap = min(MAX_CLAIMS * len(work), 24)
    extracted = extract_sourced_claims(combined, neighbors=neighbors, limit=batch_cap)

    # Assign each claim to the first dump whose body contains the quote
    by_dump: list[list[SourcedClaim]] = [[] for _ in work]
    for item in extracted:
        assigned = False
        for i, unit in enumerate(work):
            if quote_in_source(item.source_quote, unit.body):
                by_dump[i].append(item)
                assigned = True
                break
        if not assigned:
            by_dump[0].append(item)

    index = _load_index(project_path)
    by_hash: dict[str, Any] = index.setdefault("by_hash", {})
    results: list[DigestResult] = list(early_results)
    all_slugs: list[str] = []
    to_ingest: list[Path] = []
    linked_stems_all: list[str] = []

    for unit, claims in zip(work, by_dump):
        upsert = upsert_sourced_claims(
            claims,
            project_path=project_path,
            session_id=session_id,
            source_path=str(unit.saved.resolve()),
            content_hash=unit.digest_hash,
            neighbors=neighbors,
            ingest=False,
        )
        slugs = [c.slug for c in upsert.all_cards if c.slug]
        all_slugs.extend(slugs)
        linked_stems: list[str] = []
        for c in neighbors:
            stem = Path(c.path).stem if c.path else c.slug
            if stem:
                linked_stems.append(stem)
        linked_stems_all.extend(linked_stems[:8])
        _replace_linked_section(unit.saved, slugs, linked_stems[:8])
        to_ingest.append(unit.saved)
        to_ingest.extend(_collect_claim_ingest_paths(upsert, project_path=project_path))

        created = len(upsert.created)
        revised = len(upsert.revised)
        summary = _digest_summary(
            idempotent=unit.idempotent,
            created=created,
            revised=revised,
            unchanged_count=len(upsert.unchanged),
            extracted=claims,
        )
        by_hash[unit.digest_hash] = {
            "path": str(unit.saved.resolve()),
            "claim_ids": [c.id for c in upsert.all_cards],
            "updated": datetime.now(timezone.utc).isoformat(),
        }
        results.append(
            DigestResult(
                saved_path=str(unit.saved.resolve()),
                content_hash=unit.digest_hash,
                idempotent=unit.idempotent,
                claims_created=created,
                claims_revised=revised,
                claims_dropped=0,
                linked_sources=linked_stems[:8],
                open_questions=[],
                summary=summary,
                claim_slugs=slugs,
            )
        )

    _save_index(project_path, index)

    aggregate_summary = " · ".join(r.summary for r in results if r.summary) or "Remembered"
    card = LearningCard(
        id="digest",
        query=title or (work[0].saved.stem if work else "notes"),
        summary=aggregate_summary,
        open_questions=[],
        confidence=0.55,
        session_id=_safe_session_id(session_id),
        project_path=project_path,
    )
    try:
        project_md = consolidate_project_memory(
            card,
            project_path=project_path,
            session_id=session_id,
            claim_slugs=all_slugs,
            ingest=False,
            polish=False,
        )
        to_ingest.append(project_md)
    except Exception:
        logger.exception("project.md consolidate failed after digest_many")
    sid = _safe_session_id(session_id)
    if sid:
        try:
            session_md = update_agent_session_memory(
                card,
                project_path=project_path,
                session_id=sid,
                claim_slugs=all_slugs,
                ingest=False,
            )
            to_ingest.append(session_md)
        except Exception:
            logger.exception("chat memory.md update failed after digest_many")

    if ingest:
        _ingest_paths(to_ingest)
    else:
        for unit in work:
            try:
                ensure_section_summaries(
                    unit.saved,
                    project_path=project_path or infer_project_from_source(unit.saved),
                )
            except Exception:
                logger.debug("Section summaries skipped for %s", unit.saved, exc_info=True)

    return _aggregate_digest_results(results)


def _prepare_dump_unit(
    *,
    body: str,
    title: str | None,
    source_path: Path | None,
    project_path: str | None,
) -> _DumpUnit:
    digest_hash = content_hash(body)
    index = _load_index(project_path)
    by_hash: dict[str, Any] = index.setdefault("by_hash", {})
    prior = by_hash.get(digest_hash) if isinstance(by_hash.get(digest_hash), dict) else None
    idempotent = False

    if prior and prior.get("path"):
        existing = Path(str(prior["path"]))
        if existing.is_file():
            claim_ids = prior.get("claim_ids") or []
            if claim_ids:
                return _DumpUnit(
                    body=body,
                    title=title,
                    source_path=source_path,
                    digest_hash=digest_hash,
                    saved=existing.resolve(),
                    idempotent=True,
                    early=DigestResult(
                        saved_path=str(existing.resolve()),
                        content_hash=digest_hash,
                        idempotent=True,
                        summary="Already remembered this dump",
                    ),
                )
            saved = existing.resolve()
            idempotent = True
            return _DumpUnit(
                body=body,
                title=title,
                source_path=source_path,
                digest_hash=digest_hash,
                saved=saved,
                idempotent=idempotent,
            )

    saved = _place_dump(
        body=body,
        title=title,
        source_path=source_path,
        project_path=project_path,
        digest_hash=digest_hash,
    )
    return _DumpUnit(
        body=body,
        title=title,
        source_path=source_path,
        digest_hash=digest_hash,
        saved=saved,
        idempotent=False,
    )


def _aggregate_digest_results(results: list[DigestResult]) -> dict[str, Any]:
    if len(results) == 1:
        return results[0].to_dict()
    created = sum(r.claims_created for r in results)
    revised = sum(r.claims_revised for r in results)
    dropped = sum(r.claims_dropped for r in results)
    return {
        "saved_path": results[-1].saved_path if results else None,
        "content_hash": results[-1].content_hash if results else "",
        "idempotent": all(r.idempotent for r in results) if results else False,
        "claims_created": created,
        "claims_revised": revised,
        "claims_dropped": dropped,
        "linked_sources": [s for r in results for s in r.linked_sources],
        "open_questions": [],
        "summary": " · ".join(r.summary for r in results if r.summary),
        "results": [r.to_dict() for r in results],
    }


def _place_dump(
    *,
    body: str,
    title: str | None,
    source_path: Path | None,
    project_path: str | None,
    digest_hash: str,
) -> Path:
    label = title or (source_path.stem if source_path else body[:48])
    slug = _slugify(label) or "note"
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    inbox = _inbox_dir(project_path)

    if source_path and source_path.is_file() and _under_vault(source_path, project_path):
        if not is_memory_trace_path(source_path):
            return source_path.resolve()

    inbox.mkdir(parents=True, exist_ok=True)
    if source_path and source_path.is_file() and source_path.suffix.lower() in SUPPORTED_EXTENSIONS:
        dest = inbox / f"{day}-{slug}{source_path.suffix.lower()}"
        if dest.exists():
            dest = inbox / f"{day}-{slug}-{digest_hash[:8]}{source_path.suffix.lower()}"
        shutil.copy2(source_path, dest)
        return dest.resolve()

    dest = inbox / f"{day}-{slug}.md"
    if dest.exists():
        dest = inbox / f"{day}-{slug}-{digest_hash[:8]}.md"
    _write_inbox_note(
        text=body,
        title=label,
        content_hash_value=digest_hash,
        project_path=project_path,
        dest=dest,
    )
    return dest.resolve()
