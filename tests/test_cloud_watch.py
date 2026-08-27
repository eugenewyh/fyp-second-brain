"""Tests for Cloud Watch store (Better Auth user_id + BYOK, no local passwords)."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cloud-watch"))
sys.path.insert(0, str(ROOT / "src"))

from store import (  # noqa: E402
    Store,
    WatchRow,
    decrypt_secret,
    encrypt_secret,
)
from worker import is_due  # noqa: E402


def test_secret_roundtrip():
    enc = encrypt_secret("gsk_test", "master-secret")
    assert decrypt_secret(enc, "master-secret") == "gsk_test"


def test_user_llm_watch_pending(tmp_path: Path):
    store = Store(tmp_path / "t.db")
    user = store.ensure_user("auth-user-1", "a@example.com")
    assert user.email == "a@example.com"

    store.update_user_llm(
        user.user_id,
        llm_provider="groq",
        llm_api_key_enc=encrypt_secret("gsk_x", "master"),
        llm_model="llama",
    )
    again = store.get_user(user.user_id)
    assert again is not None
    assert again.to_public()["has_api_key"] is True

    store.upsert_watch(
        WatchRow(
            user_id=user.user_id,
            watch_id="papers",
            topic="Coffee",
            name="Papers",
            focus="Espresso papers.",
            include="arXiv.",
            enabled=True,
        )
    )
    w = store.get_watch(user.user_id, "papers")
    assert w is not None and w.enabled

    store.insert_brief(
        user_id=user.user_id,
        watch_id="papers",
        topic="Coffee",
        day="2026-08-26",
        markdown="# Morning Brief\n\nHello.\n",
    )
    pending = store.list_pending(user.user_id)
    assert len(pending) == 1
    assert store.ack_brief(user.user_id, pending[0].id)
    assert store.list_pending(user.user_id) == []


def test_is_due_weekdays():
    watch = WatchRow(
        user_id="u1",
        watch_id="x",
        topic="T",
        enabled=True,
        hour=9,
        timezone="Asia/Singapore",
        cadence="weekdays",
    )
    tue_10 = datetime(2026, 8, 25, 10, 0, tzinfo=ZoneInfo("Asia/Singapore"))
    assert is_due(watch, now=tue_10) is True
    sat_10 = datetime(2026, 8, 22, 10, 0, tzinfo=ZoneInfo("Asia/Singapore"))
    assert is_due(watch, now=sat_10) is False


def test_build_watch_goal_from_parts():
    from second_brain.agent.watch import build_watch_goal_from_parts

    goal = build_watch_goal_from_parts(
        focus="Citation metrics.",
        include="arXiv papers.",
        last_brief="Yesterday.",
    )
    assert "Citation metrics" in goal
    assert "Yesterday" in goal
