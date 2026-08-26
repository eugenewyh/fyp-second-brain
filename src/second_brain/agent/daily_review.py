"""Daily autonomous review — plan goals from local vault changes + open questions."""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

from second_brain.config import (
    DAILY_REVIEW_ENABLED,
    DAILY_REVIEW_MAX_GOALS,
    DIGEST_STATE_PATH,
    DOCUMENTS_DIR,
    SUPPORTED_EXTENSIONS,
)
from second_brain.memory.digest import (
    collect_open_questions,
    list_learning_cards,
    write_daily_digest,
)

logger = logging.getLogger(__name__)

ReviewStatus = Literal[
    "idle",
    "running",
    "completed",
    "partial",
    "skipped",
    "failed",
]

_review_lock = threading.Lock()

# Paths relative to DOCUMENTS_DIR that the daily review should ignore
_SKIP_DIR_PARTS = {
    "memory/digests",
    "memory/learnings",  # cards are consumed as open-questions, not re-reviewed as docs
}


@dataclass
class ReviewGoal:
    goal: str
    kind: Literal["vault_changes", "open_question", "consolidate", "watch"]
    source: str = ""
    watch_id: str = ""


@dataclass
class ReviewPlan:
    goals: list[ReviewGoal] = field(default_factory=list)
    new_files: list[str] = field(default_factory=list)
    open_questions: list[dict[str, str]] = field(default_factory=list)
    skip_reason: str | None = None
    watch_error: str | None = None


def _default_state() -> dict[str, Any]:
    return {
        "last_run_date": None,
        "last_run_status": "idle",
        "last_run_started_at": None,
        "last_run_finished_at": None,
        "last_run_reason": None,
        "goals_run": [],
        "new_files": [],
        "digest_path": None,
        "skipped_reason": None,
        "error": None,
        "last_watch_error": None,
        "next_eligible_date": None,
    }


def load_review_state(path: Path | None = None) -> dict[str, Any]:
    state_path = path or DIGEST_STATE_PATH
    if not state_path.is_file():
        return _default_state()
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return _default_state()
        merged = _default_state()
        merged.update({k: v for k, v in data.items() if k in merged or k.startswith("last_")})
        return merged
    except (OSError, json.JSONDecodeError):
        logger.exception("Failed to read digest state from %s", state_path)
        return _default_state()


def save_review_state(state: dict[str, Any], path: Path | None = None) -> None:
    state_path = path or DIGEST_STATE_PATH
    state_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(state_path)


def is_review_running() -> bool:
    return _review_lock.locked()


def _should_skip_path(path: Path, root: Path) -> bool:
    try:
        rel = path.resolve().relative_to(root.resolve())
    except ValueError:
        return True
    parts = rel.as_posix()
    for skip in _SKIP_DIR_PARTS:
        if parts == skip or parts.startswith(skip + "/"):
            return True
    # Also skip digests directory by name anywhere
    if "digests" in rel.parts:
        return True
    if "briefs" in rel.parts or "memory" in rel.parts or "watches" in rel.parts:
        return True
    if rel.name.lower() == "instruction.md":
        return True
    return False


def find_changed_files(
    *,
    since: datetime | None,
    documents_dir: Path | None = None,
    limit: int = 40,
) -> list[Path]:
    """Find vault files modified after `since` (or all recent if since is None)."""
    root = documents_dir or DOCUMENTS_DIR
    if not root.is_dir():
        return []

    cutoff = since
    if cutoff is None:
        # First run: only look at last 7 days so we don't dump the entire vault
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    # Compare naive/aware safely via timestamp
    cutoff_ts = cutoff.timestamp() if cutoff.tzinfo else cutoff.replace(tzinfo=timezone.utc).timestamp()

    found: list[tuple[float, Path]] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        if _should_skip_path(path, root):
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime >= cutoff_ts:
            found.append((mtime, path))

    found.sort(key=lambda t: t[0], reverse=True)
    return [p for _, p in found[:limit]]


def plan_daily_review(
    *,
    project_path: str | None = None,
    max_goals: int | None = None,
    documents_dir: Path | None = None,
    state: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> ReviewPlan:
    """
    Build review goals from:
    1. New/changed vault files since last successful run
    2. Open questions from recent learning cards
    """
    max_g = max_goals if max_goals is not None else DAILY_REVIEW_MAX_GOALS
    max_g = max(1, min(5, max_g))
    state = state if state is not None else load_review_state()
    now = now or datetime.now(timezone.utc)
    root = Path(project_path).expanduser() if project_path else (documents_dir or DOCUMENTS_DIR)

    goals: list[ReviewGoal] = []
    now_local = now.astimezone() if now.tzinfo else now
    weekend = now_local.weekday() >= 5
    watch_error: str | None = None

    # Standing Watches first — all eligible, not capped by max_goals
    try:
        from second_brain.agent.watch import (
            WatchError,
            build_watch_goal,
            list_watches,
            list_watches_in_topic,
            today_brief_exists,
            validate_watch,
        )

        candidates = list_watches_in_topic(root) if project_path else list_watches(root)

        for watch in candidates:
            if not watch.enabled:
                continue
            cadence = (watch.cadence or "weekdays").strip().lower()
            if cadence in {"weekdays", "weekday"} and weekend:
                continue
            try:
                validate_watch(watch)
            except WatchError:
                continue
            if today_brief_exists(watch.project_path, watch_id=watch.id):
                continue
            goals.append(
                ReviewGoal(
                    goal=build_watch_goal(watch),
                    kind="watch",
                    source=watch.project_path,
                    watch_id=watch.id,
                )
            )
    except Exception as exc:
        watch_error = f"{type(exc).__name__}: {exc}"[:400]
        logger.warning("Watch planning skipped: %s", watch_error, exc_info=True)

    def _room_for_other() -> bool:
        return sum(1 for g in goals if g.kind != "watch") < max_g

    since: datetime | None = None
    last_date = state.get("last_run_date")
    if last_date:
        try:
            # Start of the day after last run (local calendar date stored as ISO)
            d = date.fromisoformat(str(last_date))
            since = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
        except ValueError:
            since = None

    # When project_path is set, scan that folder; otherwise the main vault
    changed = find_changed_files(since=since, documents_dir=root)
    # Exclude today's auto-generated research reports from "new files" noise
    # (they will appear as learning cards / digest material instead)
    changed = [
        p for p in changed if p.parent.name != "research"
    ]

    open_qs = collect_open_questions(project_path=project_path, lookback_days=14, limit=8)

    new_file_strs = [str(p.resolve()) for p in changed]

    if changed and _room_for_other():
        names = [p.stem.replace("-", " ").replace("_", " ") for p in changed[:6]]
        name_list = ", ".join(names)
        goals.append(
            ReviewGoal(
                goal=(
                    "Review newly added or updated notes in my personal vault and "
                    f"synthesize what matters from: {name_list}. "
                    "Focus on key ideas, connections to prior knowledge, and open questions."
                ),
                kind="vault_changes",
                source=";".join(p.name for p in changed[:8]),
            )
        )

    for item in open_qs:
        if not _room_for_other():
            break
        q = (item.get("question") or "").strip()
        if not q:
            continue
        # Skip if this question was already the focus of a very recent learning card
        goals.append(
            ReviewGoal(
                goal=(
                    f"Follow up on this open question from prior research, "
                    f"using my local notes as the primary source: {q}"
                ),
                kind="open_question",
                source=item.get("learning_path") or item.get("from_query") or "",
            )
        )

    if not goals:
        # Soft consolidate if we have older learnings but nothing new
        recent = list_learning_cards(project_path=project_path, limit=5)
        if recent and _room_for_other():
            topics = ", ".join((c.get("query") or "")[:60] for c in recent[:3] if c.get("query"))
            if topics:
                goals.append(
                    ReviewGoal(
                        goal=(
                            "Consolidate what I already know from recent research and "
                            f"surface the most important takeaways across: {topics}. "
                            "Highlight contradictions, durable insights, and remaining gaps."
                        ),
                        kind="consolidate",
                        source="recent_learnings",
                    )
                )

    others = [g for g in goals if g.kind != "watch"][:max_g]
    watches = [g for g in goals if g.kind == "watch"]
    goals = watches + others
    if not goals:
        return ReviewPlan(
            goals=[],
            new_files=new_file_strs,
            open_questions=open_qs,
            skip_reason="nothing_to_review",
            watch_error=watch_error,
        )
    return ReviewPlan(
        goals=goals,
        new_files=new_file_strs,
        open_questions=open_qs,
        skip_reason=None,
        watch_error=watch_error,
    )


def run_daily_review(
    *,
    project_path: str | None = None,
    max_goals: int | None = None,
    retrieval_scope: str = "local",
    reason: str = "scheduled",
    force: bool = False,
    state_path: Path | None = None,
    run_research_fn=None,
) -> dict[str, Any]:
    """
    Execute today's autonomous review (blocking).

    Uses local-first retrieval by default. Skips if already ran today unless force=True.
    Returns a status dict suitable for the API / state file.
    """
    if not DAILY_REVIEW_ENABLED and not force:
        result = {
            **load_review_state(state_path),
            "last_run_status": "skipped",
            "skipped_reason": "disabled",
            "last_run_reason": reason,
        }
        return result

    if not _review_lock.acquire(blocking=False):
        return {
            **load_review_state(state_path),
            "last_run_status": "skipped",
            "skipped_reason": "already_running",
            "last_run_reason": reason,
        }

    try:
        state = load_review_state(state_path)
        today = datetime.now(timezone.utc).date().isoformat()
        if (
            not force
            and state.get("last_run_date") == today
            and state.get("last_run_status") in {"completed", "partial", "skipped"}
            and state.get("skipped_reason") != "busy"
        ):
            return {
                **state,
                "skipped_reason": "already_ran_today",
                "last_run_reason": reason,
            }

        started = datetime.now(timezone.utc).isoformat()
        state.update(
            {
                "last_run_status": "running",
                "last_run_started_at": started,
                "last_run_finished_at": None,
                "last_run_reason": reason,
                "goals_run": [],
                "new_files": [],
                "digest_path": None,
                "skipped_reason": None,
                "error": None,
            }
        )
        save_review_state(state, state_path)

        try:
            from second_brain.memory.claims import (
                expire_watch_claims,
                expire_watch_claims_in_vault,
            )
            from second_brain.memory.learning import has_topic_path

            if has_topic_path(project_path):
                expire_watch_claims(project_path, ingest=False)
            else:
                expire_watch_claims_in_vault(ingest=False)
        except Exception:
            logger.debug("Watch claim expiry skipped", exc_info=True)

        plan = plan_daily_review(
            project_path=project_path,
            max_goals=max_goals,
            state=state,
        )
        state["new_files"] = plan.new_files
        state["last_watch_error"] = plan.watch_error

        today_date = datetime.now(timezone.utc).date()
        if plan.skip_reason or not plan.goals:
            # Still write an empty-ish digest so the UI has a "checked in" signal
            digest_path = write_daily_digest(
                digest_date=today_date,
                cards=[],
                goals_run=[],
                new_files=plan.new_files,
                project_path=project_path,
                ingest=False,
            )
            state.update(
                {
                    "last_run_date": today,
                    "last_run_status": "skipped",
                    "skipped_reason": plan.skip_reason or "nothing_to_review",
                    "last_run_finished_at": datetime.now(timezone.utc).isoformat(),
                    "digest_path": str(digest_path.resolve()),
                    "next_eligible_date": (today_date + timedelta(days=1)).isoformat(),
                }
            )
            save_review_state(state, state_path)
            return state

        # Lazy import so unit tests can inject a stub
        if run_research_fn is None:
            from second_brain.graph import run_research as run_research_fn  # type: ignore

        goals_run: list[dict[str, Any]] = []
        errors: list[str] = []

        for g in plan.goals:
            logger.info("Daily review goal (%s): %s", g.kind, g.goal[:120])
            try:
                if g.kind == "watch":
                    from second_brain.agent.watch import run_watch

                    # Same harness as Watch Run now — do not inject single-pass run_research.
                    final = run_watch(
                        g.source or (project_path or ""),
                        watch_id=g.watch_id or None,
                        require_enabled=True,
                    )
                else:
                    final = run_research_fn(
                        g.goal,
                        retrieval_scope=retrieval_scope,
                        project_path=project_path,
                        persist_memory=True,
                    )
                final = dict(final) if final is not None else {}
                goals_run.append(
                    {
                        "goal": g.goal,
                        "kind": g.kind,
                        "source": g.source,
                        "confidence": float(final.get("confidence") or 0.0),
                        "open_questions": list(final.get("open_questions") or []),
                        "learning_path": final.get("learning_path"),
                        "report_path": final.get("report_path"),
                        "query": final.get("query") or g.goal,
                    }
                )
            except Exception as exc:
                logger.exception("Daily review goal failed")
                errors.append(str(exc)[:300])
                goals_run.append(
                    {
                        "goal": g.goal,
                        "kind": g.kind,
                        "source": g.source,
                        "confidence": 0.0,
                        "error": str(exc)[:300],
                    }
                )

        # Collect learning cards produced today + write digest
        cards = list_learning_cards(project_path=project_path, since=today_date, limit=20)
        digest_path = write_daily_digest(
            digest_date=today_date,
            cards=cards,
            goals_run=goals_run,
            new_files=plan.new_files,
            project_path=project_path,
            ingest=True,
        )

        succeeded = [g for g in goals_run if not g.get("error")]
        if not succeeded:
            status: ReviewStatus = "failed"
        elif errors:
            status = "partial"
        else:
            status = "completed"

        state.update(
            {
                "last_run_date": today,
                "last_run_status": status,
                "last_run_finished_at": datetime.now(timezone.utc).isoformat(),
                "goals_run": goals_run,
                "digest_path": str(digest_path.resolve()),
                "error": "; ".join(errors) if errors else None,
                "skipped_reason": None,
                "next_eligible_date": (today_date + timedelta(days=1)).isoformat(),
            }
        )
        save_review_state(state, state_path)
        logger.info(
            "Daily review %s (%d goals, digest=%s)",
            status,
            len(goals_run),
            digest_path,
        )
        return state
    except Exception as exc:
        logger.exception("Daily review crashed")
        state = load_review_state(state_path)
        state.update(
            {
                "last_run_status": "failed",
                "last_run_finished_at": datetime.now(timezone.utc).isoformat(),
                "error": str(exc)[:500],
                "last_run_reason": reason,
            }
        )
        save_review_state(state, state_path)
        return state
    finally:
        _review_lock.release()


def review_status_payload(state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Public status shape for GET /api/review/status."""
    state = state if state is not None else load_review_state()
    running = is_review_running() or state.get("last_run_status") == "running"
    return {
        "enabled": DAILY_REVIEW_ENABLED,
        "running": running,
        "last_run_date": state.get("last_run_date"),
        "last_run_status": state.get("last_run_status") or "idle",
        "last_run_started_at": state.get("last_run_started_at"),
        "last_run_finished_at": state.get("last_run_finished_at"),
        "last_run_reason": state.get("last_run_reason"),
        "goals_run": state.get("goals_run") or [],
        "new_files": state.get("new_files") or [],
        "digest_path": state.get("digest_path"),
        "skipped_reason": state.get("skipped_reason"),
        "error": state.get("error"),
        "last_watch_error": state.get("last_watch_error") or None,
        "next_eligible_date": state.get("next_eligible_date"),
    }


def plan_to_dict(plan: ReviewPlan) -> dict[str, Any]:
    return {
        "goals": [asdict(g) for g in plan.goals],
        "new_files": plan.new_files,
        "open_questions": plan.open_questions,
        "skip_reason": plan.skip_reason,
        "watch_error": plan.watch_error,
    }
