"""Sidecar cloud-watch sync helpers (mocked HTTP) — multi-user session token."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from second_brain.agent.cloud_watch_sync import (  # noqa: E402
    _friendly_http_error,
    cloud_watch_configured,
    login,
    pull_pending_briefs,
    sync_watch_to_cloud,
)


def test_not_configured(monkeypatch):
    monkeypatch.delenv("CLOUD_WATCH_URL", raising=False)
    monkeypatch.delenv("CLOUD_WATCH_USER_TOKEN", raising=False)
    monkeypatch.delenv("CLOUD_WATCH_TOKEN", raising=False)
    assert cloud_watch_configured() is False


def test_friendly_http_error_extracts_fastapi_detail():
    assert (
        _friendly_http_error(401, '{"detail":"Invalid email or password"}')
        == "Invalid email or password"
    )
    assert _friendly_http_error(401, "not-json") == "Invalid email or password"


def test_login_surfaces_clean_auth_error(monkeypatch):
    import urllib.error as urllib_error

    monkeypatch.setenv("CLOUD_WATCH_URL", "http://example.test")

    class Err(urllib_error.HTTPError):
        def __init__(self):
            super().__init__(
                "http://example.test/v1/auth/login",
                401,
                "Unauthorized",
                hdrs=None,
                fp=None,
            )

        def read(self):
            return b'{"detail":"Invalid email or password"}'

    with patch("urllib.request.urlopen", side_effect=Err()):
        try:
            login("a@b.com", "wrong-password")
            assert False, "expected RuntimeError"
        except RuntimeError as e:
            assert str(e) == "Invalid email or password"


def test_sync_watch_to_cloud(monkeypatch):
    monkeypatch.setenv("CLOUD_WATCH_URL", "http://example.test")
    monkeypatch.setenv("CLOUD_WATCH_USER_TOKEN", "user-session")

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"watch_id": "papers", "enabled": True}).encode()

    with patch("urllib.request.urlopen", return_value=FakeResp()):
        out = sync_watch_to_cloud(
            {
                "watch_id": "papers",
                "topic": "Coffee",
                "focus": "Espresso",
                "include": "Papers",
                "enabled": True,
            }
        )
    assert out["watch_id"] == "papers"


def test_push_local_llm_to_cloud(monkeypatch):
    from second_brain.agent.cloud_watch_sync import push_local_llm_to_cloud

    monkeypatch.setenv("CLOUD_WATCH_URL", "http://example.test")
    monkeypatch.setenv("CLOUD_WATCH_USER_TOKEN", "user-session")
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_local_key")
    monkeypatch.setenv("LLM_MODEL", "openai/gpt-oss-120b")

    bodies: list[dict] = []

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"email": "a@b.com", "has_api_key": True}).encode()

    def fake_urlopen(req, timeout=30.0):
        import json as _json

        bodies.append(_json.loads(req.data.decode()))
        return FakeResp()

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        out = push_local_llm_to_cloud()
    assert out["has_api_key"] is True
    assert bodies[0]["llm_api_key"] == "gsk_local_key"
    assert bodies[0]["llm_provider"] == "groq"


def test_push_local_llm_requires_models_key(monkeypatch):
    from second_brain.agent.cloud_watch_sync import push_local_llm_to_cloud

    monkeypatch.setenv("CLOUD_WATCH_URL", "http://example.test")
    monkeypatch.setenv("CLOUD_WATCH_USER_TOKEN", "user-session")
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    try:
        push_local_llm_to_cloud()
        assert False, "expected RuntimeError"
    except RuntimeError as e:
        assert "Models" in str(e)


def test_pull_writes_and_acks(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CLOUD_WATCH_URL", "http://example.test")
    monkeypatch.setenv("CLOUD_WATCH_USER_TOKEN", "user-session")
    calls: list[str] = []

    class FakeResp:
        def __init__(self, body: dict):
            self._body = body

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps(self._body).encode()

    def fake_urlopen(req, timeout=30.0):
        url = req.full_url if hasattr(req, "full_url") else str(req.get_full_url())
        calls.append(url)
        if "/pending" in url:
            return FakeResp(
                {
                    "briefs": [
                        {
                            "id": 1,
                            "user_id": "u1",
                            "watch_id": "papers",
                            "topic": "Coffee",
                            "day": "2026-08-26",
                            "markdown": "# Morning Brief\n\nHi.\n",
                            "pending": True,
                        }
                    ]
                }
            )
        return FakeResp({"ok": True})

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        result = pull_pending_briefs(documents_dir=tmp_path)

    assert result["count"] == 1
    path = tmp_path / "Coffee" / "watches" / "papers" / "briefs" / "2026-08-26.md"
    assert path.is_file()
    assert any("/ack" in c for c in calls)
