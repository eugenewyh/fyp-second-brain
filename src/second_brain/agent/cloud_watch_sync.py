"""Client helpers: multi-user Cloud Watch (session token + BYOK via cloud)."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from second_brain.config import DOCUMENTS_DIR

logger = logging.getLogger(__name__)

# Baked-in hosted endpoint for shipped builds. Override with CLOUD_WATCH_URL in .env
# (never shown in the Settings UI). Empty = Cloud Watch / app sign-in disabled.
_DEFAULT_CLOUD_WATCH_URL = (os.getenv("NOUS_CLOUD_WATCH_DEFAULT_URL") or "").strip()


def cloud_watch_service_url() -> str:
    # Re-read .env so operator URL changes apply without a full process restart.
    try:
        from second_brain.config import PROJECT_ROOT

        env_path = PROJECT_ROOT / ".env"
        if env_path.is_file():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("CLOUD_WATCH_URL="):
                    raw = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if raw:
                        os.environ["CLOUD_WATCH_URL"] = raw
                        return raw.rstrip("/")
                    break
    except Exception:
        logger.debug("Cloud Watch URL dotenv refresh skipped", exc_info=True)
    return (os.getenv("CLOUD_WATCH_URL") or _DEFAULT_CLOUD_WATCH_URL or "").strip().rstrip("/")


def cloud_watch_config() -> tuple[str, str]:
    """Return (base_url, user_session_token)."""
    url = cloud_watch_service_url()
    token = (os.getenv("CLOUD_WATCH_USER_TOKEN") or "").strip()
    if not token:
        token = (os.getenv("CLOUD_WATCH_TOKEN") or "").strip()
    return url, token


def _friendly_http_error(code: int, raw: str) -> str:
    """Turn FastAPI/JSON error bodies into short UI-safe messages."""
    detail: str | None = None
    text = (raw or "").strip()
    if text:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            d = payload.get("detail")
            if isinstance(d, str) and d.strip():
                detail = d.strip()
            elif isinstance(d, list) and d:
                parts: list[str] = []
                for item in d:
                    if isinstance(item, dict) and item.get("msg"):
                        parts.append(str(item["msg"]))
                if parts:
                    detail = "; ".join(parts)

    if detail:
        return detail
    if code == 401:
        return "Invalid email or password"
    if code == 400:
        return "Could not complete that request"
    if code == 409:
        return "An account with this email already exists"
    if code >= 500:
        return "Cloud Watch is temporarily unavailable"
    return "Could not reach Cloud Watch"


def cloud_watch_service_available() -> bool:
    return bool(cloud_watch_service_url())


def cloud_watch_configured() -> bool:
    """Signed in to the hosted Cloud Watch service."""
    url, token = cloud_watch_config()
    return bool(url and token)


def _request(
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    token: str | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    url, default_token = cloud_watch_config()
    use_token = (token if token is not None else default_token).strip()
    if not url:
        raise RuntimeError("CLOUD_WATCH_URL is not set")
    if not use_token and path not in ("/v1/auth/register", "/v1/auth/login"):
        raise RuntimeError("Cloud Watch is not signed in")
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if use_token:
        headers["Authorization"] = f"Bearer {use_token}"
    req = urllib.request.Request(
        f"{url}{path}",
        data=data,
        method=method,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(_friendly_http_error(e.code, raw)) from e
    except urllib.error.URLError as e:
        raise RuntimeError("Can't reach Cloud Watch right now.") from e


def register(email: str, password: str) -> dict[str, Any]:
    if not cloud_watch_service_available():
        raise RuntimeError("Cloud Watch service URL is not configured on this build")
    return _request(
        "POST",
        "/v1/auth/register",
        body={"email": email, "password": password},
        token="",
    )


def login(email: str, password: str) -> dict[str, Any]:
    if not cloud_watch_service_available():
        raise RuntimeError("Cloud Watch service URL is not configured on this build")
    return _request(
        "POST",
        "/v1/auth/login",
        body={"email": email, "password": password},
        token="",
    )


def put_llm(
    *,
    llm_provider: str,
    llm_api_key: str,
    llm_model: str = "",
) -> dict[str, Any]:
    return _request(
        "PUT",
        "/v1/me/llm",
        body={
            "llm_provider": llm_provider,
            "llm_api_key": llm_api_key,
            "llm_model": llm_model,
        },
    )


def local_llm_credentials() -> tuple[str, str, str]:
    """Provider / API key / model from the same env Research and Ask use."""
    from second_brain.memory.llm import _api_key, _primary_model, _provider

    provider = (_provider() or "groq").strip().lower() or "groq"
    key = (_api_key() or "").strip()
    model = (_primary_model() or "").strip()
    return provider, key, model


def push_local_llm_to_cloud() -> dict[str, Any]:
    """Upload the Mac's Models key to Cloud Watch (encrypted BYOK on the server)."""
    if not cloud_watch_configured():
        raise RuntimeError("Sign in to Cloud Watch first.")
    provider, key, model = local_llm_credentials()
    if not key:
        raise RuntimeError(
            "No LLM API key in Settings → Models. Add one there — Cloud Watch uses the same key."
        )
    return put_llm(llm_provider=provider, llm_api_key=key, llm_model=model)


def me() -> dict[str, Any]:
    return _request("GET", "/v1/me")


def sync_watch_to_cloud(payload: dict[str, Any]) -> dict[str, Any]:
    watch_id = (payload.get("watch_id") or "").strip()
    if not watch_id or watch_id == "legacy":
        raise RuntimeError("Named watch_id required for Cloud Watch sync")
    body = {
        "topic": payload.get("topic") or "",
        "name": payload.get("name") or "",
        "focus": payload.get("focus") or "",
        "include": payload.get("include") or "",
        "exclude": payload.get("exclude") or "",
        "trusted_sources": payload.get("trusted_sources") or "",
        "enabled": bool(payload.get("enabled")),
        "cadence": payload.get("cadence") or "weekdays",
        "hour": int(payload.get("hour") or 9),
        "timezone": payload.get("timezone") or "Asia/Singapore",
        "last_brief_excerpt": (payload.get("last_brief_excerpt") or "")[:900],
        "project_tail": (payload.get("project_tail") or "")[:2000],
    }
    return _request("PUT", f"/v1/watches/{watch_id}", body=body)


def pull_pending_briefs(*, documents_dir: Path | None = None) -> dict[str, Any]:
    root = Path(documents_dir or DOCUMENTS_DIR)
    data = _request("GET", "/v1/briefs/pending")
    briefs = data.get("briefs") or []
    written: list[dict[str, str]] = []
    errors: list[str] = []
    for b in briefs:
        try:
            watch_id = str(b.get("watch_id") or "").strip()
            topic = str(b.get("topic") or "").strip()
            day = str(b.get("day") or "").strip()
            markdown = str(b.get("markdown") or "")
            brief_id = b.get("id")
            if not watch_id or not topic or not day or brief_id is None:
                continue
            dest_dir = root / topic / "watches" / watch_id / "briefs"
            dest_dir.mkdir(parents=True, exist_ok=True)
            path = dest_dir / f"{day}.md"
            path.write_text(markdown if markdown.endswith("\n") else markdown + "\n", encoding="utf-8")
            _request("POST", f"/v1/briefs/{int(brief_id)}/ack", body={})
            written.append({"path": str(path.resolve()), "watch_id": watch_id, "day": day})
        except Exception as e:
            logger.warning("Cloud Watch pull failed for brief: %s", e)
            errors.append(str(e)[:200])
    return {"written": written, "count": len(written), "errors": errors}
