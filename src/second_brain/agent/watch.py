"""Standing Watch instructions: parse, validate, brief, run."""

from __future__ import annotations

import logging
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from second_brain.config import DAILY_REVIEW_HOUR, DOCUMENTS_DIR
from second_brain.memory.learning import (
    extract_executive_summary,
    extract_key_findings,
    extract_open_questions,
    read_project_memory_tail,
)

logger = logging.getLogger(__name__)

INSTRUCTION_NAME = "instruction.md"
BRIEFS_DIRNAME = "briefs"
WATCHES_DIRNAME = "watches"
LEGACY_WATCH_ID = ""

_HEADING = re.compile(r"^##\s+(.+?)\s*$", re.M)
_SLUG = re.compile(r"[^a-z0-9]+")

INSTRUCTION_TEMPLATE = """---
name: {name}
enabled: false
cadence: weekdays
---

# Watch instruction

## Who
[Your role and what you are working on]

## Focus
[Specific topics this Watch should track]

## Include
[What counts as significant — product launches, papers, metrics, …]

## Exclude
[Noise: generic hype, rehashed posts, companies you do not follow]

## Trusted sources
[Publications, arXiv categories, people, repos]

## Cadence
Weekday mornings.

## Steer log
"""


@dataclass
class WatchInstruction:
    project_path: str
    id: str = LEGACY_WATCH_ID
    name: str = ""
    created: str = ""
    enabled: bool = False
    cadence: str = "weekdays"
    hour: int = DAILY_REVIEW_HOUR
    who: str = ""
    focus: str = ""
    include: str = ""
    exclude: str = ""
    trusted_sources: str = ""
    cadence_body: str = ""
    steer_log: str = ""
    raw: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class WatchError(ValueError):
    """User-facing Watch validation / same-day skip."""


def normalize_watch_id(watch_id: str | None) -> str:
    if not watch_id or watch_id == "legacy":
        return LEGACY_WATCH_ID
    return watch_id.strip()


def is_legacy_watch_id(watch_id: str | None) -> bool:
    return normalize_watch_id(watch_id) == LEGACY_WATCH_ID


def topic_name(project_path: str | Path) -> str:
    return Path(project_path).name.replace("-", " ").replace("_", " ").strip() or "Topic"


def slugify_watch_name(name: str, *, max_len: int = 48) -> str:
    s = _SLUG.sub("-", (name or "").lower()).strip("-")
    return (s or "untitled")[:max_len]


def watch_root(project_path: str | Path, watch_id: str | None = None) -> Path:
    base = Path(project_path).expanduser()
    wid = normalize_watch_id(watch_id)
    if is_legacy_watch_id(wid):
        return base
    return base / WATCHES_DIRNAME / wid


def instruction_path(project_path: str | Path, watch_id: str | None = None) -> Path:
    return watch_root(project_path, watch_id) / INSTRUCTION_NAME


def briefs_dir(project_path: str | Path, watch_id: str | None = None) -> Path:
    return watch_root(project_path, watch_id) / BRIEFS_DIRNAME


def brief_path_for(
    project_path: str | Path,
    day: date | None = None,
    *,
    watch_id: str | None = None,
) -> Path:
    d = day or datetime.now().astimezone().date()
    return briefs_dir(project_path, watch_id) / f"{d.isoformat()}.md"


def today_brief_exists(
    project_path: str | Path,
    day: date | None = None,
    *,
    watch_id: str | None = None,
) -> bool:
    path = brief_path_for(project_path, day, watch_id=watch_id)
    return path.is_file() and path.stat().st_size > 20


def _file_created_iso(path: Path) -> str:
    try:
        ts = path.stat().st_mtime
    except OSError:
        return ""
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


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


def _sections(body: str) -> dict[str, str]:
    matches = list(_HEADING.finditer(body))
    out: dict[str, str] = {}
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        key = m.group(1).strip().lower()
        out[key] = body[start:end].strip()
    return out


def _truthy(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def parse_instruction(
    text: str,
    *,
    project_path: str,
    watch_id: str | None = None,
    created: str = "",
) -> WatchInstruction:
    meta, body = _split_frontmatter(text)
    secs = _sections(body)
    hour = DAILY_REVIEW_HOUR
    try:
        hour = int(meta.get("hour") or DAILY_REVIEW_HOUR)
    except ValueError:
        hour = DAILY_REVIEW_HOUR
    focus = (
        secs.get("focus", "")
        or secs.get("who / focus", "")
        or secs.get("who/focus", "")
    )
    wid = normalize_watch_id(watch_id)
    default_name = topic_name(project_path)
    name = (meta.get("name") or "").strip() or default_name
    return WatchInstruction(
        project_path=str(Path(project_path).expanduser()),
        id=wid,
        name=name,
        created=created,
        enabled=_truthy(meta.get("enabled") or "false"),
        cadence=(meta.get("cadence") or "weekdays").strip().lower(),
        hour=max(0, min(23, hour)),
        who=secs.get("who", ""),
        focus=focus,
        include=secs.get("include", ""),
        exclude=secs.get("exclude", ""),
        trusted_sources=secs.get("trusted sources", "") or secs.get("trusted", ""),
        cadence_body=secs.get("cadence", ""),
        steer_log=secs.get("steer log", ""),
        raw=text,
    )


def load_watch(
    project_path: str | Path,
    watch_id: str | None = None,
) -> WatchInstruction | None:
    path = instruction_path(project_path, watch_id)
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    return parse_instruction(
        text,
        project_path=str(Path(project_path).expanduser()),
        watch_id=watch_id,
        created=_file_created_iso(path),
    )


def instruction_template(*, hour: int | None = None, name: str = "Untitled") -> str:
    # `hour` is accepted for old callers; new files do not store it. Scheduler uses DAILY_REVIEW_HOUR.
    _ = hour
    return INSTRUCTION_TEMPLATE.format(name=(name or "Untitled").strip() or "Untitled")


def ensure_instruction(project_path: str | Path, *, overwrite: bool = False) -> Path:
    """Create the legacy `{topic}/instruction.md` if missing. New Watch must not call this."""
    path = instruction_path(project_path, LEGACY_WATCH_ID)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        return path
    path.write_text(instruction_template(name=topic_name(project_path)), encoding="utf-8")
    return path


def unique_watch_slug(project_path: str | Path, name: str) -> str:
    base = slugify_watch_name(name)
    root = Path(project_path).expanduser() / WATCHES_DIRNAME
    slug = base
    n = 2
    while (root / slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


def create_watch(
    project_path: str | Path,
    *,
    name: str = "Untitled",
    focus: str | None = None,
    include: str | None = None,
    enabled: bool = False,
    cadence: str | None = None,
    hour: int | None = None,
) -> WatchInstruction:
    """Create a named Watch under `{topic}/watches/{slug}/`. Never writes legacy instruction.md."""
    path = Path(project_path).expanduser()
    if not path.is_dir():
        raise WatchError(f"Not a topic folder: {path}")
    label = (name or "").strip() or "Untitled"
    slug = unique_watch_slug(path, label)
    dest = instruction_path(path, slug)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(instruction_template(name=label), encoding="utf-8")
    inc = (include or "").strip() or default_include(path)
    return update_watch(
        path,
        watch_id=slug,
        name=label,
        focus=focus,
        include=inc,
        enabled=enabled,
        cadence=cadence,
        hour=hour,
    )


def promote_legacy_watch(
    project_path: str | Path,
    *,
    name: str | None = None,
) -> WatchInstruction:
    """Move `{topic}/instruction.md` into `{topic}/watches/{slug}/`. Does not create a second legacy file."""
    path = Path(project_path).expanduser()
    if not path.is_dir():
        raise WatchError(f"Not a topic folder: {path}")
    watch = load_watch(path, LEGACY_WATCH_ID)
    src = instruction_path(path, LEGACY_WATCH_ID)
    if watch is None or not src.is_file():
        raise WatchError("Watch not found.")
    label = (name or watch.name or topic_name(path)).strip() or "Untitled"
    slug = unique_watch_slug(path, label)
    dest_root = path / WATCHES_DIRNAME / slug
    dest_root.mkdir(parents=True, exist_ok=True)
    (dest_root / INSTRUCTION_NAME).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    src_briefs = briefs_dir(path, LEGACY_WATCH_ID)
    dest_briefs = briefs_dir(path, slug)
    if src_briefs.is_dir() and not dest_briefs.exists():
        shutil.move(str(src_briefs), str(dest_briefs))
    src.unlink(missing_ok=True)
    promoted = load_watch(path, slug)
    if promoted is None:
        raise WatchError("Watch upgrade failed.")
    if (name or "").strip() and promoted.name != label:
        return update_watch(path, watch_id=slug, name=label)
    return promoted


def move_watch(
    project_path: str | Path,
    dest_project_path: str | Path,
    *,
    watch_id: str | None = None,
) -> WatchInstruction:
    """Re-home a Watch onto another topic folder. Named watches move; legacy is copied as named."""
    src = Path(project_path).expanduser()
    dest = Path(dest_project_path).expanduser()
    if not src.is_dir():
        raise WatchError(f"Not a topic folder: {src}")
    if not dest.is_dir():
        raise WatchError(f"Not a topic folder: {dest}")
    wid = normalize_watch_id(watch_id)
    if src.resolve() == dest.resolve():
        watch = load_watch(src, wid)
        if watch is None:
            raise WatchError("Watch not found.")
        return watch
    watch = load_watch(src, wid)
    if watch is None:
        raise WatchError("Watch not found.")
    slug = unique_watch_slug(dest, watch.name or wid or "Untitled")
    dest_root = dest / WATCHES_DIRNAME / slug
    dest_root.parent.mkdir(parents=True, exist_ok=True)
    if is_legacy_watch_id(wid):
        dest_root.mkdir(parents=True, exist_ok=True)
        (dest_root / INSTRUCTION_NAME).write_text(
            instruction_path(src, wid).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    else:
        src_root = watch_root(src, wid)
        if dest_root.exists():
            raise WatchError("A Watch with that name already exists on the destination topic.")
        shutil.move(str(src_root), str(dest_root))
    moved = load_watch(dest, slug)
    if moved is None:
        raise WatchError("Watch move failed.")
    return moved


def delete_watch(
    project_path: str | Path,
    *,
    watch_id: str | None = None,
) -> None:
    """Remove a Watch. Named folders are deleted; legacy only drops instruction.md."""
    path = Path(project_path).expanduser()
    wid = normalize_watch_id(watch_id)
    if load_watch(path, wid) is None:
        raise WatchError("Watch not found.")
    if is_legacy_watch_id(wid):
        instruction_path(path, wid).unlink(missing_ok=True)
        return
    root = watch_root(path, wid)
    if root.is_dir():
        shutil.rmtree(root)


def list_watches_in_topic(project_path: str | Path) -> list[WatchInstruction]:
    topic = Path(project_path).expanduser()
    if not topic.is_dir():
        return []
    out: list[WatchInstruction] = []
    legacy = load_watch(topic, LEGACY_WATCH_ID)
    if legacy:
        out.append(legacy)
    named_root = topic / WATCHES_DIRNAME
    if named_root.is_dir():
        for child in sorted(named_root.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            w = load_watch(topic, child.name)
            if w:
                out.append(w)
    return out


def list_watches(documents_dir: Path | None = None) -> list[WatchInstruction]:
    root = Path(documents_dir or DOCUMENTS_DIR)
    if not root.is_dir():
        return []
    skip = {"research", "memory"}
    out: list[WatchInstruction] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name.startswith(".") or child.name.lower() in skip:
            continue
        out.extend(list_watches_in_topic(child))
    return out


def list_briefs(
    project_path: str | Path,
    *,
    watch_id: str | None = None,
    limit: int = 30,
) -> list[dict[str, str]]:
    directory = briefs_dir(project_path, watch_id)
    if not directory.is_dir():
        return []
    rows: list[dict[str, str]] = []
    for path in sorted(directory.glob("*.md"), reverse=True)[:limit]:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        rows.append(
            {
                "path": str(path.resolve()),
                "day": path.stem,
                "excerpt": text.strip()[:400],
            }
        )
    return rows


def _placeholder(text: str) -> bool:
    t = (text or "").strip()
    if len(t) < 8:
        return True
    if t.startswith("[") and t.endswith("]"):
        return True
    return False


def validate_watch(watch: WatchInstruction) -> None:
    if _placeholder(watch.focus):
        raise WatchError("Watch needs a Focus section before it can run.")
    if _placeholder(watch.include) and _placeholder(watch.trusted_sources):
        raise WatchError("Watch needs Include or Trusted sources before it can run.")


def _set_frontmatter_value(text: str, key: str, value: str) -> str:
    if not text.startswith("---"):
        return f"---\n{key}: {value}\n---\n\n{text.lstrip()}"
    parts = text.split("---", 2)
    if len(parts) < 3:
        return text
    lines = parts[1].strip("\n").splitlines()
    found = False
    out: list[str] = []
    for line in lines:
        if line.strip().startswith(f"{key}:"):
            out.append(f"{key}: {value}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"{key}: {value}")
    return "---\n" + "\n".join(out) + "\n---" + parts[2]


def _replace_section(text: str, heading: str, new_body: str) -> str:
    heading_re = re.compile(
        rf"(^##\s+{re.escape(heading)}\s*$\n)(.*?)(?=^##\s|\Z)",
        re.M | re.S | re.I,
    )
    block = new_body.strip() + "\n\n"
    if heading_re.search(text):
        return heading_re.sub(lambda m: m.group(1) + block, text, count=1)
    return text.rstrip() + f"\n\n## {heading}\n\n{new_body.strip()}\n"


def watch_is_complete(watch: WatchInstruction) -> bool:
    try:
        validate_watch(watch)
        return True
    except WatchError:
        return False


def filled_text(text: str) -> str:
    return "" if _placeholder(text) else (text or "").strip()


def suggested_focus(project_path: str | Path, watch: WatchInstruction | None) -> str:
    if watch and not _placeholder(watch.focus):
        return watch.focus.strip()
    try:
        from second_brain.memory.claims import LIVE_STATUSES, list_claims

        claims = [c for c in list_claims(str(project_path), status=None) if c.status in LIVE_STATUSES]
        if claims and (claims[0].claim or "").strip():
            return claims[0].claim.strip()[:220]
    except Exception:
        logger.debug("Watch focus suggestion skipped", exc_info=True)
    return f"New developments related to {topic_name(project_path)}"


def default_include(project_path: str | Path) -> str:
    return f"Significant papers, product changes, and eval results related to {topic_name(project_path)}."


def update_watch(
    project_path: str | Path,
    *,
    watch_id: str | None = None,
    name: str | None = None,
    focus: str | None = None,
    include: str | None = None,
    exclude: str | None = None,
    trusted_sources: str | None = None,
    enabled: bool | None = None,
    cadence: str | None = None,
    hour: int | None = None,
) -> WatchInstruction:
    """Write fields into this Watch's instruction.md without clobbering Steer log."""
    wid = normalize_watch_id(watch_id)
    if is_legacy_watch_id(wid):
        path = instruction_path(project_path, LEGACY_WATCH_ID)
        if not path.is_file():
            raise WatchError("Watch not found.")
    else:
        path = instruction_path(project_path, wid)
        if not path.is_file():
            raise WatchError("Watch not found.")
    text = path.read_text(encoding="utf-8")
    if enabled is not None:
        text = _set_frontmatter_value(text, "enabled", "true" if enabled else "false")
    if name is not None and name.strip():
        text = _set_frontmatter_value(text, "name", name.strip())
    if focus is not None:
        text = _replace_section(text, "Focus", focus)
    if include is not None:
        text = _replace_section(text, "Include", include)
    if exclude is not None:
        text = _replace_section(text, "Exclude", exclude)
    if trusted_sources is not None:
        text = _replace_section(text, "Trusted sources", trusted_sources)
    if cadence is not None:
        text = _set_frontmatter_value(text, "cadence", (cadence or "weekdays").strip().lower())
    if hour is not None:
        text = _set_frontmatter_value(text, "hour", str(max(0, min(23, int(hour)))))
    path.write_text(text, encoding="utf-8")
    watch = parse_instruction(
        text,
        project_path=str(Path(project_path).expanduser()),
        watch_id=wid,
        created=_file_created_iso(path),
    )
    # Active + incomplete cannot schedule or Run — auto-pause so UI stays honest.
    if watch.enabled and not watch_is_complete(watch):
        text = _set_frontmatter_value(text, "enabled", "false")
        path.write_text(text, encoding="utf-8")
        watch = parse_instruction(
            text,
            project_path=str(Path(project_path).expanduser()),
            watch_id=wid,
            created=watch.created,
        )
    return watch


def last_brief_excerpt(
    project_path: str | Path,
    *,
    limit: int = 900,
    watch_id: str | None = None,
) -> str:
    directory = briefs_dir(project_path, watch_id)
    if not directory.is_dir():
        return ""
    files = sorted(directory.glob("*.md"), reverse=True)
    if not files:
        return ""
    try:
        text = files[0].read_text(encoding="utf-8")
    except OSError:
        return ""
    return text.strip()[:limit]


def _project_tail(project_path: str | None) -> str:
    try:
        return read_project_memory_tail(project_path, max_lines=16)
    except Exception:
        return ""


def build_watch_goal(watch: WatchInstruction) -> str:
    last = last_brief_excerpt(watch.project_path, watch_id=watch.id)
    tail = _project_tail(watch.project_path)
    return build_watch_goal_from_parts(
        focus=watch.focus,
        include=watch.include,
        exclude=watch.exclude,
        trusted_sources=watch.trusted_sources,
        who=watch.who,
        last_brief=last,
        project_tail=tail,
    )


def build_watch_goal_from_parts(
    *,
    focus: str,
    include: str = "",
    exclude: str = "",
    trusted_sources: str = "",
    who: str = "",
    last_brief: str = "",
    project_tail: str = "",
) -> str:
    """Build a Watch goal from plain fields (local disk or cloud sync)."""
    parts = [
        "Produce a morning intelligence brief of significant new developments from the last 24 hours.",
        "Do not rehash the last brief. If nothing significant happened, say so.",
        f"Focus:\n{(focus or '').strip()}",
    ]
    if not _placeholder(include):
        parts.append(f"Include:\n{include.strip()}")
    if not _placeholder(exclude):
        parts.append(f"Exclude:\n{exclude.strip()}")
    if not _placeholder(trusted_sources):
        parts.append(f"Trusted sources:\n{trusted_sources.strip()}")
    if not _placeholder(who):
        parts.append(f"Who I am:\n{who.strip()}")
    if (last_brief or "").strip():
        parts.append(f"Last brief (do not repeat):\n{last_brief.strip()}")
    if (project_tail or "").strip():
        parts.append(f"What I already believe (project.md):\n{project_tail.strip()}")
    return "\n\n".join(parts)


def retrieval_is_thin(stats: dict[str, Any] | None) -> bool:
    if not stats:
        return True
    total = sum(int(v) for v in stats.values() if isinstance(v, (int, float)))
    return total < 3


def briefs_are_similar(a: str, b: str, *, threshold: float = 0.55) -> bool:
    from second_brain.memory.claims import claim_similarity

    return claim_similarity(a, b) >= threshold


def format_watch_brief(
    *,
    report: str,
    stats: dict[str, Any] | None = None,
    sources: list[str] | None = None,
    day: date | None = None,
    slow_day: bool = False,
) -> str:
    d = day or datetime.now().astimezone().date()
    now = datetime.now().astimezone().strftime("%H:%M")
    summary = extract_executive_summary(report or "")
    findings = extract_key_findings(report or "", limit=7)
    gaps = extract_open_questions(report or "")
    srcs = [s for s in (sources or []) if s][:8]
    if slow_day or (not findings and not summary):
        body = (
            f"# Morning Brief — {d.isoformat()}\n"
            f"Generated: {now}\n\n"
            "## The one thing\n\n"
            "Slow day — nothing significant beyond what you already know.\n"
        )
        return body

    one = findings[0] if findings else summary
    happened = findings[:7]
    lines = [
        f"# Morning Brief — {d.isoformat()}",
        f"Generated: {now}",
        "",
        "## The one thing",
        "",
        one,
        "",
        "## What happened",
        "",
    ]
    for item in happened:
        lines.append(f"- {item}")
    if gaps:
        lines.extend(["", "## What to do", ""])
        for g in gaps[:3]:
            lines.append(f"- {g}")
    if srcs:
        lines.extend(["", "## Reading list", ""])
        for s in srcs:
            lines.append(f"- {Path(s).name}")
    lines.append("")
    return "\n".join(lines)


def write_brief(
    project_path: str | Path,
    markdown: str,
    *,
    day: date | None = None,
    watch_id: str | None = None,
) -> Path:
    path = brief_path_for(project_path, day, watch_id=watch_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return path


def append_steer(
    project_path: str | Path,
    note: str,
    *,
    watch_id: str | None = None,
) -> Path:
    wid = normalize_watch_id(watch_id)
    if is_legacy_watch_id(wid):
        path = instruction_path(project_path, LEGACY_WATCH_ID)
        if not path.is_file():
            raise WatchError("Watch not found.")
    else:
        path = instruction_path(project_path, wid)
        if not path.is_file():
            raise WatchError("Watch not found.")
    text = path.read_text(encoding="utf-8")
    stamp = datetime.now().astimezone().date().isoformat()
    line = f"- {stamp}: {note.strip()}"
    if re.search(r"(?im)^##\s+Steer log\s*$", text):
        text = text.rstrip() + "\n" + line + "\n"
    else:
        text = text.rstrip() + "\n\n## Steer log\n\n" + line + "\n"
    path.write_text(text, encoding="utf-8")
    return path


def prepare_watch_run(
    project_path: str | Path,
    *,
    watch_id: str | None = None,
    force: bool = False,
    require_enabled: bool = False,
) -> tuple[WatchInstruction, str]:
    watch = load_watch(project_path, watch_id)
    if watch is None:
        raise WatchError("No instruction.md in this topic. Write a Watch instruction first.")
    if require_enabled and not watch.enabled:
        raise WatchError("Watch is paused (enabled: false).")
    validate_watch(watch)
    if not force and today_brief_exists(watch.project_path, watch_id=watch.id):
        raise WatchError("Today's brief already exists for this topic.")
    return watch, build_watch_goal(watch)


def finalize_watch_run(
    watch: WatchInstruction,
    final: dict[str, Any],
    *,
    day: date | None = None,
) -> dict[str, Any]:
    report = str(final.get("report") or "")
    stats = final.get("retrieval_stats") or {}
    last = last_brief_excerpt(watch.project_path, watch_id=watch.id)
    slow = retrieval_is_thin(stats) or (last and briefs_are_similar(report, last))
    md = format_watch_brief(
        report=report,
        stats=stats,
        sources=list(final.get("memory_sources") or [])
        or ([final["report_path"]] if final.get("report_path") else []),
        day=day,
        slow_day=bool(slow),
    )
    path = write_brief(watch.project_path, md, day=day, watch_id=watch.id)
    return {
        "brief_path": str(path.resolve()),
        "slow_day": bool(slow),
        "report_path": final.get("report_path"),
        "claim_count": final.get("claim_count") or 0,
        "goal": final.get("query") or final.get("goal"),
        "watch_id": watch.id,
    }


def run_watch(
    project_path: str | Path,
    *,
    watch_id: str | None = None,
    force: bool = False,
    require_enabled: bool = False,
    session_id: str | None = None,
    run_research_fn=None,
    max_passes: int | None = None,
) -> dict[str, Any]:
    """Blocking Watch: same goal loop as Run now, plus a deterministic brief."""
    watch, goal = prepare_watch_run(
        project_path,
        watch_id=watch_id,
        force=force,
        require_enabled=require_enabled,
    )
    from second_brain.agent.harness import HarnessError, resolve_run_spec, run_harness

    spec = resolve_run_spec(
        kind="watch",
        instruction=goal,
        project_path=watch.project_path,
        session_id=session_id,
        retrieval_scope="hybrid",
        max_passes=max_passes,
        claim_origin="watch",
    )
    if run_research_fn is not None:
        final = run_research_fn(
            spec.instruction,
            retrieval_scope=spec.retrieval_scope,
            project_path=spec.project_path,
            persist_memory=spec.persist_memory,
            session_id=spec.session_id,
            claim_origin=spec.claim_origin,
        )
        final = dict(final) if final is not None else {}
    else:
        try:
            final = run_harness(spec)
        except HarnessError as exc:
            raise WatchError(str(exc)) from exc
    extra = finalize_watch_run(watch, final)
    return {**final, **extra}


def stream_watch(
    project_path: str | Path,
    *,
    watch_id: str | None = None,
    force: bool = False,
    require_enabled: bool = False,
    session_id: str | None = None,
    max_passes: int | None = None,
) -> Iterator[tuple[str, Any]]:
    watch, goal = prepare_watch_run(
        project_path,
        watch_id=watch_id,
        force=force,
        require_enabled=require_enabled,
    )
    from second_brain.agent.harness import resolve_run_spec, run_harness_stream

    spec = resolve_run_spec(
        kind="watch",
        instruction=goal,
        project_path=watch.project_path,
        session_id=session_id,
        retrieval_scope="hybrid",
        max_passes=max_passes,
        claim_origin="watch",
    )
    final: dict[str, Any] | None = None
    for kind, payload in run_harness_stream(spec):
        if kind == "complete" and isinstance(payload, dict):
            final = dict(payload)
            extra = finalize_watch_run(watch, final)
            merged = {**final, **extra}
            yield ("watch_brief", extra)
            yield ("complete", merged)
            continue
        yield (kind, payload)
    if final is None:
        yield ("error", {"message": "Watch ended without a result"})
