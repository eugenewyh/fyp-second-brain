"""Cloud Watch API — Better Auth sessions + BYOK + per-user watches."""

from __future__ import annotations

import json
import os
import secrets
import urllib.error
import urllib.request
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from store import Store, WatchRow, encrypt_secret
from worker import run_due

DATA_DIR = Path(os.getenv("CLOUD_WATCH_DATA", "/data"))
DB_PATH = DATA_DIR / "cloud-watch.db"
CRON_TOKEN = (os.getenv("CLOUD_WATCH_CRON_TOKEN") or os.getenv("CLOUD_WATCH_TOKEN") or "").strip()
MASTER_SECRET = (os.getenv("CLOUD_WATCH_SECRET") or CRON_TOKEN or "").strip()
AUTH_URL = (os.getenv("AUTH_URL") or "").strip().rstrip("/")
AUTH_INTERNAL_SECRET = (os.getenv("AUTH_INTERNAL_SECRET") or "").strip()

app = FastAPI(title="Nous Cloud Watch", version="1.1.0")
store = Store(DB_PATH)


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing Bearer token")
    return authorization.split(" ", 1)[1].strip()


def _resolve_auth_user(token: str) -> tuple[str, str]:
    """Return (user_id, email) via Nous auth /internal/session."""
    if not AUTH_URL:
        raise HTTPException(503, "AUTH_URL not configured on Cloud Watch")
    if not AUTH_INTERNAL_SECRET:
        raise HTTPException(503, "AUTH_INTERNAL_SECRET not configured on Cloud Watch")
    req = urllib.request.Request(
        f"{AUTH_URL}/internal/session",
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Internal-Secret": AUTH_INTERNAL_SECRET,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            data = json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise HTTPException(401, "Invalid or expired session") from e
        raise HTTPException(502, "Auth service unavailable") from e
    except urllib.error.URLError as e:
        raise HTTPException(502, "Can't reach auth service") from e
    user_id = str(data.get("userId") or "").strip()
    email = str(data.get("email") or "").strip()
    if not user_id:
        raise HTTPException(401, "Invalid or expired session")
    return user_id, email


def require_user(authorization: str | None = Header(default=None)) -> str:
    token = _bearer(authorization)
    user_id, email = _resolve_auth_user(token)
    store.ensure_user(user_id, email)
    return user_id


def require_cron(authorization: str | None = Header(default=None)) -> None:
    if not CRON_TOKEN:
        raise HTTPException(503, "CLOUD_WATCH_CRON_TOKEN not configured on server")
    got = _bearer(authorization)
    if not secrets.compare_digest(got, CRON_TOKEN):
        raise HTTPException(401, "Invalid cron token")


class LlmBody(BaseModel):
    llm_provider: str = "groq"
    llm_api_key: str = ""
    llm_model: str = ""


class WatchUpsert(BaseModel):
    topic: str
    name: str = ""
    focus: str = ""
    include: str = ""
    exclude: str = ""
    trusted_sources: str = ""
    enabled: bool = False
    cadence: str = "weekdays"
    hour: int = Field(default=9, ge=0, le=23)
    timezone: str = "Asia/Singapore"
    last_brief_excerpt: str = ""
    project_tail: str = ""


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "cloud-watch",
        "version": "1.1.0",
        "multi_user": True,
        "auth": bool(AUTH_URL),
    }


@app.get("/v1/me")
def me(user_id: str = Depends(require_user)):
    user = store.get_user(user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    return user.to_public()


@app.put("/v1/me/llm")
def put_llm(body: LlmBody, user_id: str = Depends(require_user)):
    if not MASTER_SECRET:
        raise HTTPException(503, "CLOUD_WATCH_SECRET not configured on server")
    key = (body.llm_api_key or "").strip()
    enc = None
    if key:
        try:
            enc = encrypt_secret(key, MASTER_SECRET)
        except ValueError as e:
            raise HTTPException(503, str(e)) from e
    user = store.update_user_llm(
        user_id,
        llm_provider=(body.llm_provider or "groq").strip().lower() or "groq",
        llm_api_key_enc=enc,
        llm_model=(body.llm_model or "").strip(),
    )
    return user.to_public()


@app.put("/v1/watches/{watch_id}")
def put_watch(watch_id: str, body: WatchUpsert, user_id: str = Depends(require_user)):
    wid = (watch_id or "").strip()
    if not wid or wid == "legacy":
        raise HTTPException(400, "Named watch_id required")
    topic = (body.topic or "").strip()
    if not topic:
        raise HTTPException(400, "topic required")
    row = store.upsert_watch(
        WatchRow(
            user_id=user_id,
            watch_id=wid,
            topic=topic,
            name=(body.name or "").strip(),
            focus=(body.focus or "").strip(),
            include=(body.include or "").strip(),
            exclude=(body.exclude or "").strip(),
            trusted_sources=(body.trusted_sources or "").strip(),
            enabled=bool(body.enabled),
            cadence=(body.cadence or "weekdays").strip().lower() or "weekdays",
            hour=int(body.hour),
            timezone=(body.timezone or "Asia/Singapore").strip() or "Asia/Singapore",
            last_brief_excerpt=(body.last_brief_excerpt or "").strip(),
            project_tail=(body.project_tail or "").strip(),
        )
    )
    return row.to_dict()


@app.get("/v1/briefs/pending")
def pending_briefs(user_id: str = Depends(require_user)):
    return {"briefs": [b.to_dict() for b in store.list_pending(user_id)]}


@app.post("/v1/briefs/{brief_id}/ack")
def ack_brief(brief_id: int, user_id: str = Depends(require_user)):
    ok = store.ack_brief(user_id, brief_id)
    if not ok:
        raise HTTPException(404, "Brief not found")
    return {"ok": True}


@app.post("/internal/run-due", dependencies=[Depends(require_cron)])
def internal_run_due():
    if not MASTER_SECRET:
        raise HTTPException(503, "CLOUD_WATCH_SECRET not configured")
    results = run_due(store, master_secret=MASTER_SECRET)
    return {"results": results}
