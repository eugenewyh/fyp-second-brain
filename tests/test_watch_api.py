"""HTTP coverage for Watch create/update/move/delete (no LLM)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("sidecar.server.start_scheduler", lambda **_kwargs: None)
    from sidecar.server import app

    with TestClient(app) as c:
        yield c


def test_health_exposes_watches_api(client: TestClient):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["watches_api"] == 3
    assert body["act_api"] == 1


def test_agent_defaults_exposes_harness_budget(client: TestClient):
    res = client.get("/api/agent/defaults")
    assert res.status_code == 200
    body = res.json()
    assert 1 <= int(body["max_goal_passes"]) <= 4
    assert 1 <= int(body["watch_max_passes"]) <= 4
    assert "enable_web_search" in body
    assert "auto_memory" in body


def test_watch_create_update_move_delete(client: TestClient, tmp_path: Path):
    src = tmp_path / "Alpha"
    dest = tmp_path / "Beta"
    src.mkdir()
    dest.mkdir()

    created = client.post(
        "/api/watches",
        json={
            "project_path": str(src),
            "name": "Papers",
            "focus": "Citation metrics for grounded-but-incomplete RAG answers.",
            "include": "New citation metrics, arXiv papers, eval datasets.",
            "enabled": False,
        },
    )
    assert created.status_code == 200, created.text
    watch = created.json()
    watch_id = watch["watch_id"]
    assert watch_id
    assert watch["name"] == "Papers"
    assert (src / "watches" / watch_id / "instruction.md").is_file()
    assert not (src / "instruction.md").exists()

    posted = client.post(
        "/api/watches/update",
        json={
            "project_path": str(src),
            "watch_id": watch_id,
            "name": "Morning papers",
            "enabled": True,
        },
    )
    assert posted.status_code == 200, posted.text
    assert posted.json()["name"] == "Morning papers"
    assert posted.json()["enabled"] is True

    patched = client.patch(
        "/api/watches",
        json={
            "project_path": str(src),
            "watch_id": watch_id,
            "enabled": False,
        },
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["enabled"] is False

    moved = client.post(
        "/api/watches/move",
        json={
            "project_path": str(src),
            "dest_project_path": str(dest),
            "watch_id": watch_id,
        },
    )
    assert moved.status_code == 200, moved.text
    dest_id = moved.json()["watch_id"]
    assert Path(moved.json()["project_path"]).resolve() == dest.resolve()
    assert (dest / "watches" / dest_id / "instruction.md").is_file()
    assert not (src / "watches" / watch_id).exists()

    deleted = client.post(
        "/api/watches/delete",
        json={"project_path": str(dest), "watch_id": dest_id},
    )
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["ok"] is True
    assert not (dest / "watches" / watch_id).exists()


def test_create_focus_only_defaults_include_and_can_enable(client: TestClient, tmp_path: Path):
    topic = tmp_path / "Alpha"
    topic.mkdir()
    created = client.post(
        "/api/watches",
        json={
            "project_path": str(topic),
            "name": "Chat watch",
            "focus": "New papers on grounded-but-incomplete RAG citation metrics.",
            "enabled": True,
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["complete"] is True
    assert body["enabled"] is True
    include = (body.get("include") or "").strip()
    assert include
    assert not include.startswith("[")
    assert "Alpha" in include or "papers" in include.lower()

    patched = client.post(
        "/api/watches/update",
        json={
            "project_path": str(topic),
            "watch_id": body["watch_id"],
            "exclude": "Generic hype posts.",
            "trusted_sources": "arxiv.org",
        },
    )
    assert patched.status_code == 200, patched.text
    assert "hype" in (patched.json().get("exclude") or "").lower()
    assert "arxiv" in (patched.json().get("trusted_sources") or "").lower()


def test_create_incomplete_auto_disables(client: TestClient, tmp_path: Path):
    topic = tmp_path / "Beta"
    topic.mkdir()
    created = client.post(
        "/api/watches",
        json={
            "project_path": str(topic),
            "name": "Empty focus",
            "focus": "[placeholder]",
            "include": "[also placeholder]",
            "enabled": True,
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["complete"] is False
    assert body["enabled"] is False


def test_get_watch_by_id_and_query_shim(client: TestClient, tmp_path: Path):
    topic = tmp_path / "Alpha"
    topic.mkdir()
    created = client.post(
        "/api/watches",
        json={
            "project_path": str(topic),
            "name": "Papers",
            "focus": "Citation metrics for grounded-but-incomplete RAG answers.",
            "include": "New citation metrics, arXiv papers, eval datasets.",
        },
    )
    assert created.status_code == 200, created.text
    watch_id = created.json()["watch_id"]
    by_path = client.get(
        f"/api/watches/{watch_id}",
        params={"project_path": str(topic)},
    )
    assert by_path.status_code == 200, by_path.text
    assert by_path.json()["watch_id"] == watch_id
    shim = client.get(
        "/api/watches",
        params={"project_path": str(topic), "watch_id": watch_id},
    )
    assert shim.status_code == 200, shim.text
    assert shim.json()["watch_id"] == watch_id


def test_promote_legacy_http(client: TestClient, tmp_path: Path):
    topic = tmp_path / "Inbox"
    topic.mkdir()
    (topic / "instruction.md").write_text(
        """---
enabled: false
cadence: weekdays
---

# Watch

## Focus
Citation metrics for grounded-but-incomplete RAG answers.

## Include
New citation metrics, arXiv papers, eval datasets.
""",
        encoding="utf-8",
    )
    res = client.post(
        "/api/watches/promote",
        json={"project_path": str(topic), "name": "Inbox brief"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["watch_id"]
    assert body["name"] == "Inbox brief"
    assert not (topic / "instruction.md").exists()
    assert (topic / "watches" / body["watch_id"] / "instruction.md").is_file()
