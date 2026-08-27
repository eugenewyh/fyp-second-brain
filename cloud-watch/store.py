"""SQLite store — BYOK per auth user_id + watches/briefs (no local passwords)."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def encrypt_secret(plaintext: str, master: str) -> str:
    """Fernet-like seal using stdlib only (HMAC + XOR keystream)."""
    if not plaintext:
        return ""
    if not master:
        raise ValueError("CLOUD_WATCH_SECRET required to store API keys")
    nonce = secrets.token_bytes(16)
    key = hashlib.sha256(master.encode("utf-8") + nonce).digest()
    data = plaintext.encode("utf-8")
    stream = b""
    counter = 0
    while len(stream) < len(data):
        stream += hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
        counter += 1
    cipher = bytes(a ^ b for a, b in zip(data, stream[: len(data)]))
    tag = hmac.new(key, cipher, hashlib.sha256).digest()[:16]
    return nonce.hex() + "$" + tag.hex() + "$" + cipher.hex()


def decrypt_secret(blob: str, master: str) -> str:
    if not blob:
        return ""
    if not master:
        raise ValueError("CLOUD_WATCH_SECRET required")
    parts = blob.split("$")
    if len(parts) != 3:
        raise ValueError("Invalid encrypted secret")
    nonce = bytes.fromhex(parts[0])
    tag = bytes.fromhex(parts[1])
    cipher = bytes.fromhex(parts[2])
    key = hashlib.sha256(master.encode("utf-8") + nonce).digest()
    expect = hmac.new(key, cipher, hashlib.sha256).digest()[:16]
    if not hmac.compare_digest(tag, expect):
        raise ValueError("Invalid encrypted secret")
    stream = b""
    counter = 0
    while len(stream) < len(cipher):
        stream += hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
        counter += 1
    data = bytes(a ^ b for a, b in zip(cipher, stream[: len(cipher)]))
    return data.decode("utf-8")


@dataclass
class UserLlmRow:
    user_id: str
    email: str = ""
    llm_provider: str = "groq"
    llm_api_key_enc: str = ""
    llm_model: str = ""
    created: str = ""

    def to_public(self) -> dict[str, Any]:
        return {
            "id": self.user_id,
            "email": self.email,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "has_api_key": bool(self.llm_api_key_enc),
            "created": self.created,
        }


@dataclass
class WatchRow:
    user_id: str
    watch_id: str
    topic: str
    name: str = ""
    focus: str = ""
    include: str = ""
    exclude: str = ""
    trusted_sources: str = ""
    enabled: bool = False
    cadence: str = "weekdays"
    hour: int = 9
    timezone: str = "Asia/Singapore"
    last_brief_excerpt: str = ""
    project_tail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BriefRow:
    id: int
    user_id: str
    watch_id: str
    topic: str
    day: str
    markdown: str
    pending: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Store:
    def __init__(self, db_path: Path | str) -> None:
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS user_llm (
                    user_id TEXT PRIMARY KEY,
                    email TEXT NOT NULL DEFAULT '',
                    llm_provider TEXT NOT NULL DEFAULT 'groq',
                    llm_api_key_enc TEXT NOT NULL DEFAULT '',
                    llm_model TEXT NOT NULL DEFAULT '',
                    created TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS watches (
                    user_id TEXT NOT NULL,
                    watch_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    name TEXT NOT NULL DEFAULT '',
                    focus TEXT NOT NULL DEFAULT '',
                    include TEXT NOT NULL DEFAULT '',
                    exclude TEXT NOT NULL DEFAULT '',
                    trusted_sources TEXT NOT NULL DEFAULT '',
                    enabled INTEGER NOT NULL DEFAULT 0,
                    cadence TEXT NOT NULL DEFAULT 'weekdays',
                    hour INTEGER NOT NULL DEFAULT 9,
                    timezone TEXT NOT NULL DEFAULT 'Asia/Singapore',
                    last_brief_excerpt TEXT NOT NULL DEFAULT '',
                    project_tail TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (user_id, watch_id)
                );
                CREATE TABLE IF NOT EXISTS briefs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    watch_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    day TEXT NOT NULL,
                    markdown TEXT NOT NULL,
                    pending INTEGER NOT NULL DEFAULT 1,
                    UNIQUE(user_id, watch_id, day)
                );
                """
            )
            # Migrate from legacy password users table if present
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
            )
            if cur.fetchone():
                conn.execute(
                    """
                    INSERT OR IGNORE INTO user_llm (user_id, email, llm_provider, llm_api_key_enc, llm_model, created)
                    SELECT id, email, llm_provider, llm_api_key_enc, llm_model, created FROM users
                    """
                )

    def ensure_user(self, user_id: str, email: str = "") -> UserLlmRow:
        existing = self.get_user(user_id)
        if existing:
            if email and email != existing.email:
                with self._connect() as conn:
                    conn.execute(
                        "UPDATE user_llm SET email = ? WHERE user_id = ?",
                        (email.strip().lower(), user_id),
                    )
                return self.get_user(user_id) or existing
            return existing
        row = UserLlmRow(user_id=user_id, email=email.strip().lower(), created=_now())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO user_llm (user_id, email, llm_provider, llm_api_key_enc, llm_model, created)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (row.user_id, row.email, row.llm_provider, "", "", row.created),
            )
        return row

    def get_user(self, user_id: str) -> UserLlmRow | None:
        with self._connect() as conn:
            cur = conn.execute("SELECT * FROM user_llm WHERE user_id = ?", (user_id,))
            r = cur.fetchone()
        return self._user_from_row(r) if r else None

    def update_user_llm(
        self,
        user_id: str,
        *,
        email: str | None = None,
        llm_provider: str | None = None,
        llm_api_key_enc: str | None = None,
        llm_model: str | None = None,
    ) -> UserLlmRow:
        user = self.ensure_user(user_id, email or "")
        provider = llm_provider if llm_provider is not None else user.llm_provider
        key_enc = llm_api_key_enc if llm_api_key_enc is not None else user.llm_api_key_enc
        model = llm_model if llm_model is not None else user.llm_model
        em = email.strip().lower() if email is not None else user.email
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE user_llm SET email = ?, llm_provider = ?, llm_api_key_enc = ?, llm_model = ?
                WHERE user_id = ?
                """,
                (em, provider, key_enc, model, user_id),
            )
        out = self.get_user(user_id)
        assert out is not None
        return out

    def upsert_watch(self, row: WatchRow) -> WatchRow:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO watches (
                    user_id, watch_id, topic, name, focus, include, exclude, trusted_sources,
                    enabled, cadence, hour, timezone, last_brief_excerpt, project_tail
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, watch_id) DO UPDATE SET
                    topic=excluded.topic,
                    name=excluded.name,
                    focus=excluded.focus,
                    include=excluded.include,
                    exclude=excluded.exclude,
                    trusted_sources=excluded.trusted_sources,
                    enabled=excluded.enabled,
                    cadence=excluded.cadence,
                    hour=excluded.hour,
                    timezone=excluded.timezone,
                    last_brief_excerpt=excluded.last_brief_excerpt,
                    project_tail=excluded.project_tail
                """,
                (
                    row.user_id,
                    row.watch_id,
                    row.topic,
                    row.name,
                    row.focus,
                    row.include,
                    row.exclude,
                    row.trusted_sources,
                    1 if row.enabled else 0,
                    row.cadence,
                    int(row.hour),
                    row.timezone,
                    row.last_brief_excerpt,
                    row.project_tail,
                ),
            )
        return self.get_watch(row.user_id, row.watch_id) or row

    def get_watch(self, user_id: str, watch_id: str) -> WatchRow | None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM watches WHERE user_id = ? AND watch_id = ?",
                (user_id, watch_id),
            )
            r = cur.fetchone()
        return self._watch_from_row(r) if r else None

    def list_enabled(self) -> list[WatchRow]:
        with self._connect() as conn:
            cur = conn.execute("SELECT * FROM watches WHERE enabled = 1")
            rows = cur.fetchall()
        return [self._watch_from_row(r) for r in rows]

    def brief_exists(self, user_id: str, watch_id: str, day: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT 1 FROM briefs WHERE user_id = ? AND watch_id = ? AND day = ?",
                (user_id, watch_id, day),
            )
            return cur.fetchone() is not None

    def insert_brief(
        self,
        *,
        user_id: str,
        watch_id: str,
        topic: str,
        day: str,
        markdown: str,
    ) -> BriefRow:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO briefs (user_id, watch_id, topic, day, markdown, pending)
                VALUES (?, ?, ?, ?, ?, 1)
                ON CONFLICT(user_id, watch_id, day) DO UPDATE SET
                    markdown=excluded.markdown,
                    pending=1,
                    topic=excluded.topic
                """,
                (user_id, watch_id, topic, day, markdown),
            )
            cur = conn.execute(
                "SELECT * FROM briefs WHERE user_id = ? AND watch_id = ? AND day = ?",
                (user_id, watch_id, day),
            )
            r = cur.fetchone()
        assert r is not None
        return self._brief_from_row(r)

    def list_pending(self, user_id: str) -> list[BriefRow]:
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT * FROM briefs WHERE user_id = ? AND pending = 1
                ORDER BY day DESC, id DESC
                """,
                (user_id,),
            )
            rows = cur.fetchall()
        return [self._brief_from_row(r) for r in rows]

    def ack_brief(self, user_id: str, brief_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE briefs SET pending = 0 WHERE id = ? AND user_id = ?",
                (brief_id, user_id),
            )
            return cur.rowcount > 0

    @staticmethod
    def _user_from_row(r: sqlite3.Row) -> UserLlmRow:
        return UserLlmRow(
            user_id=r["user_id"],
            email=r["email"] or "",
            llm_provider=r["llm_provider"] or "groq",
            llm_api_key_enc=r["llm_api_key_enc"] or "",
            llm_model=r["llm_model"] or "",
            created=r["created"] or "",
        )

    @staticmethod
    def _watch_from_row(r: sqlite3.Row) -> WatchRow:
        return WatchRow(
            user_id=r["user_id"],
            watch_id=r["watch_id"],
            topic=r["topic"],
            name=r["name"] or "",
            focus=r["focus"] or "",
            include=r["include"] or "",
            exclude=r["exclude"] or "",
            trusted_sources=r["trusted_sources"] or "",
            enabled=bool(r["enabled"]),
            cadence=r["cadence"] or "weekdays",
            hour=int(r["hour"] or 9),
            timezone=r["timezone"] or "Asia/Singapore",
            last_brief_excerpt=r["last_brief_excerpt"] or "",
            project_tail=r["project_tail"] or "",
        )

    @staticmethod
    def _brief_from_row(r: sqlite3.Row) -> BriefRow:
        return BriefRow(
            id=int(r["id"]),
            user_id=r["user_id"],
            watch_id=r["watch_id"],
            topic=r["topic"],
            day=r["day"],
            markdown=r["markdown"] or "",
            pending=bool(r["pending"]),
        )
