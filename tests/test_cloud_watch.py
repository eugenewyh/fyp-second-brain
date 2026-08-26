"""Tests for multi-user Cloud Watch store (no LLM)."""

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
    hash_password,
    verify_password,
)
from worker import is_due  # noqa: E402


def test_password_and_secret_roundtrip():
    h = hash_password("secretpass")
    assert verify_password("secretpass", h)
    assert not verify_password("wrong", h)
    enc = encrypt_secret("gsk_test", "master-secret")
    assert decrypt_secret(enc, "master-secret") == "gsk_test"


def test_register_session_watch_pending(tmp_path: Path):
    store = Store(tmp_path / "t.db")
    user = store.create_user("a@example.com", "password12")
    token = store.create_session(user.id)
    assert store.user_id_for_token(token) == user.id

    store.upsert_watch(
        WatchRow(
            user_id=user.id,
            watch_id="papers",
            topic="Coffee",
            name="Papers",
            focus="Espresso papers.",
            include="arXiv.",
            enabled=True,
        )
    )
    w = store.get_watch(user.id, "papers")
    assert w is not None and w.enabled

    store.insert_brief(
        user_id=user.id,
        watch_id="papers",
        topic="Coffee",
        day="2026-08-26",
        markdown="# Morning Brief\n\nHello.\n",
    )
    pending = store.list_pending(user.id)
    assert len(pending) == 1
    assert store.ack_brief(user.id, pending[0].id)
    assert store.list_pending(user.id) == []


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
