"""Client helpers: Cloud Watch via Better Auth session Bearer (no sidecar .env token)."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from second_brain.config import DOCUMENTS_DIR

logger = logging.getLogger(__name__)

_DEFAULT_CLOUD_WATCH_URL = (os.getenv("NOUS_CLOUD_WATCH_DEFAULT_URL") or "").strip()

# Per-request session token from desktop (Authorization header), not .env
_session_token: ContextVar[str] = ContextVar("cloud_watch_session_token", default="")

# When True, local daily review skips watch goals — cloud cron runs them instead.
_cloud_watches_delegated = False


def set_session_token(token: str | None) -> None:
    _session_token.set((token or "").strip())


def get_session_token() -> str:
    return (_session_token.get() or "").strip()


def set_cloud_watches_delegated(delegated: bool) -> None:
    global _cloud_watches_delegated
    _cloud_watches_delegated = bool(delegated)


def cloud_watches_delegated() -> bool:
    return _cloud_watches_delegated


def cloud_watch_service_url() -> str:
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
    """Return (base_url, session_token). Token comes from the current request context."""
    return cloud_watch_service_url(), get_session_token()


def _friendly_http_error(code: int, raw: str) -> str:
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
        return "Session expired — sign in again under Settings → Account"
    if code == 400:
        return "Could not complete that request"
    if code >= 500:
        return "Cloud Scheduled Research is temporarily unavailable"
    return "Could not reach Cloud Scheduled Research"


def cloud_watch_service_available() -> bool:
    return bool(cloud_watch_service_url())


def cloud_watch_configured() -> bool:
    """Hosted Cloud Scheduled Research URL set and a Better Auth session token present."""
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
    if not use_token:
        raise RuntimeError("Sign in under Settings → Account for Cloud Scheduled Research")
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {use_token}",
    }
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
        raise RuntimeError("Can't reach Cloud Scheduled Research right now.") from e


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
    from second_brain.memory.llm import _api_key, _primary_model, _provider

    provider = (_provider() or "groq").strip().lower() or "groq"
    key = (_api_key() or "").strip()
    model = (_primary_model() or "").strip()
    return provider, key, model


def push_local_llm_to_cloud() -> dict[str, Any]:
    if not cloud_watch_configured():
        raise RuntimeError("Sign in under Settings → Account first.")
    provider, key, model = local_llm_credentials()
    if not key:
        raise RuntimeError(
            "No LLM API key in Settings → Models. Add one there — Cloud Scheduled Research uses the same key."
        )
    return put_llm(llm_provider=provider, llm_api_key=key, llm_model=model)


def me() -> dict[str, Any]:
    return _request("GET", "/v1/me")


def build_cloud_sync_payload(project_path: str | Path, watch_id: str | None) -> dict[str, Any]:
    """Build the PUT /v1/watches payload from a local watch folder."""
    from second_brain.agent.watch import last_brief_excerpt, load_watch
    from second_brain.memory.learning import read_project_memory_tail

    path = Path(project_path).expanduser()
    watch = load_watch(path, watch_id)
    if watch is None:
        raise RuntimeError("Watch not found.")
    return {
        "watch_id": watch.id,
        "topic": path.name,
        "name": watch.name or path.name,
        "focus": watch.focus or "",
        "include": watch.include or "",
        "exclude": watch.exclude or "",
        "trusted_sources": watch.trusted_sources or "",
        "enabled": bool(watch.enabled),
        "cadence": watch.cadence or "weekdays",
        "hour": int(watch.hour or 9),
        "timezone": "Asia/Singapore",
        "last_brief_excerpt": last_brief_excerpt(path, watch_id=watch.id, limit=900),
        "project_tail": read_project_memory_tail(str(path), max_lines=16),
    }


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


def sync_all_watches_to_cloud(*, documents_dir: Path | None = None) -> dict[str, Any]:
    """Push every active named watch to Cloud Watch."""
    from second_brain.agent.watch import list_watches, validate_watch

    if not cloud_watch_configured():
        return {"ok": False, "skipped": True, "reason": "not_configured", "synced": [], "errors": []}

    synced: list[str] = []
    errors: list[str] = []
    for watch in list_watches(documents_dir):
        if not watch.enabled or not watch.id or watch.id in {"legacy", "draft"}:
            continue
        try:
            validate_watch(watch)
        except Exception as e:
            errors.append(f"{watch.id}: {e}"[:200])
            continue
        try:
            payload = build_cloud_sync_payload(watch.project_path, watch.id)
            sync_watch_to_cloud(payload)
            synced.append(watch.id)
        except Exception as e:
            logger.warning("Cloud Watch sync failed for %s: %s", watch.id, e)
            errors.append(f"{watch.id}: {e}"[:200])
    return {"ok": True, "synced": synced, "count": len(synced), "errors": errors}


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
