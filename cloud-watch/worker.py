"""Run due Cloud Watches per user with that user's BYOK."""

from __future__ import annotations

import logging
import os
import threading
from datetime import date as date_cls
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from store import Store, WatchRow, decrypt_secret

logger = logging.getLogger(__name__)

_LLM_LOCK = threading.Lock()


def _now_in(tz_name: str) -> datetime:
    try:
        tz = ZoneInfo(tz_name or "Asia/Singapore")
    except Exception:
        tz = ZoneInfo("Asia/Singapore")
    return datetime.now(tz)


def is_due(watch: WatchRow, *, now: datetime | None = None) -> bool:
    if not watch.enabled:
        return False
    local = now or _now_in(watch.timezone)
    cadence = (watch.cadence or "weekdays").strip().lower()
    if cadence in {"weekdays", "weekday"} and local.weekday() >= 5:
        return False
    hour = max(0, min(23, int(watch.hour if watch.hour is not None else 9)))
    return local.hour >= hour


def _apply_user_llm(user, master_secret: str) -> dict[str, str]:
    """Set process env for this user's provider/key; return previous values to restore."""
    prev = {
        "LLM_PROVIDER": os.environ.get("LLM_PROVIDER"),
        "LLM_API_KEY": os.environ.get("LLM_API_KEY"),
        "NVIDIA_API_KEY": os.environ.get("NVIDIA_API_KEY"),
        "GROQ_API_KEY": os.environ.get("GROQ_API_KEY"),
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
        "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY"),
        "XAI_API_KEY": os.environ.get("XAI_API_KEY"),
        "CUSTOM_API_KEY": os.environ.get("CUSTOM_API_KEY"),
        "LLM_MODEL": os.environ.get("LLM_MODEL"),
    }
    key = decrypt_secret(user.llm_api_key_enc, master_secret) if user.llm_api_key_enc else ""
    if not key:
        raise RuntimeError("User has no API key configured (BYOK)")
    provider = (user.llm_provider or "nvidia").strip().lower() or "nvidia"
    os.environ["LLM_PROVIDER"] = provider
    os.environ["LLM_API_KEY"] = key
    if provider == "nvidia":
        os.environ["NVIDIA_API_KEY"] = key
    elif provider == "groq":
        os.environ["GROQ_API_KEY"] = key
    elif provider == "openai":
        os.environ["OPENAI_API_KEY"] = key
    elif provider == "openrouter":
        os.environ["OPENROUTER_API_KEY"] = key
    elif provider == "xai":
        os.environ["XAI_API_KEY"] = key
    elif provider == "openai_compatible":
        os.environ["CUSTOM_API_KEY"] = key
    if (user.llm_model or "").strip():
        os.environ["LLM_MODEL"] = user.llm_model.strip()
    return prev


def _restore_env(prev: dict[str, str | None]) -> None:
    for k, v in prev.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def run_one_watch(
    store: Store,
    watch: WatchRow,
    *,
    master_secret: str,
    day: str | None = None,
) -> dict[str, Any]:
    local = _now_in(watch.timezone)
    d = day or local.date().isoformat()
    if store.brief_exists(watch.user_id, watch.watch_id, d):
        return {
            "watch_id": watch.watch_id,
            "user_id": watch.user_id,
            "status": "skipped",
            "reason": "brief_exists",
            "day": d,
        }

    user = store.get_user(watch.user_id)
    if user is None:
        return {
            "watch_id": watch.watch_id,
            "user_id": watch.user_id,
            "status": "error",
            "message": "user_missing",
            "day": d,
        }

    from second_brain.agent.harness import HarnessError, resolve_run_spec, run_harness
    from second_brain.agent.watch import (
        briefs_are_similar,
        build_watch_goal_from_parts,
        format_watch_brief,
        retrieval_is_thin,
    )

    goal = build_watch_goal_from_parts(
        focus=watch.focus,
        include=watch.include,
        exclude=watch.exclude,
        trusted_sources=watch.trusted_sources,
        last_brief=watch.last_brief_excerpt,
        project_tail=watch.project_tail,
    )

    with _LLM_LOCK:
        prev = _apply_user_llm(user, master_secret)
        try:
            spec = resolve_run_spec(
                kind="watch",
                instruction=goal,
                project_path=None,
                retrieval_scope="hybrid",
                claim_origin="watch",
            )
            try:
                final = run_harness(spec)
            except HarnessError as exc:
                logger.warning("Cloud Watch %s/%s failed: %s", watch.user_id, watch.watch_id, exc)
                return {
                    "watch_id": watch.watch_id,
                    "user_id": watch.user_id,
                    "status": "error",
                    "message": str(exc),
                    "day": d,
                }
        finally:
            _restore_env(prev)

    report = str(final.get("report") or "")
    stats = final.get("retrieval_stats") or {}
    last = (watch.last_brief_excerpt or "").strip()
    slow = retrieval_is_thin(stats) or (last and briefs_are_similar(report, last))
    md = format_watch_brief(
        report=report,
        stats=stats,
        sources=list(final.get("memory_sources") or []),
        day=date_cls.fromisoformat(d),
        slow_day=bool(slow),
    )
    brief = store.insert_brief(
        user_id=watch.user_id,
        watch_id=watch.watch_id,
        topic=watch.topic,
        day=d,
        markdown=md,
    )
    store.upsert_watch(
        WatchRow(
            **{
                **watch.to_dict(),
                "last_brief_excerpt": md.strip()[:900],
            }
        )
    )
    return {
        "watch_id": watch.watch_id,
        "user_id": watch.user_id,
        "status": "ok",
        "day": d,
        "brief_id": brief.id,
        "slow_day": bool(slow),
    }


def run_due(store: Store, *, master_secret: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for watch in store.list_enabled():
        if not is_due(watch):
            results.append(
                {
                    "watch_id": watch.watch_id,
                    "user_id": watch.user_id,
                    "status": "skipped",
                    "reason": "not_due",
                }
            )
            continue
        try:
            results.append(run_one_watch(store, watch, master_secret=master_secret))
        except Exception as exc:
            logger.exception("Watch run failed")
            results.append(
                {
                    "watch_id": watch.watch_id,
                    "user_id": watch.user_id,
                    "status": "error",
                    "message": str(exc)[:300],
                }
            )
    return results
