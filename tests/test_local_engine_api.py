from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from second_brain.local_engine.engine import _reset
from second_brain.local_engine.runtimes import stub

STUB_MODEL = {
    "id": "stub/tiny-moe",
    "display_name": "Stub Tiny MoE",
    "disk_bytes": 1024,
    "context_window": 2048,
    "active_params_b": 0.1,
    "total_params_b": 1.0,
}


@pytest.fixture(autouse=True)
def _isolate_local_engine(tmp_path: Path):
    saved = dict(os.environ)
    os.environ["LOCAL_ENGINE_HOME"] = str(tmp_path / "home")
    stub.reset()
    _reset()
    yield
    stub.reset()
    _reset()
    os.environ.clear()
    os.environ.update(saved)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr("sidecar.server.start_scheduler", lambda **_kwargs: None)
    monkeypatch.setattr("sidecar.server.ENV_PATH", tmp_path / ".env")
    from sidecar.server import app

    with TestClient(app) as c:
        yield c


def _local_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOCAL_ENGINE_RUNTIME", "stub")
    monkeypatch.setenv("LLM_MODEL", "stub/tiny-moe")
    monkeypatch.setenv("LLM_PROVIDER", "local")


def _assert_no_endpoint(payload: object) -> None:
    raw = json.dumps(payload)
    assert '"base_url"' not in raw
    assert '"token"' not in raw
    assert '"pid"' not in raw


def test_get_local_engine_before_ensure_is_not_installed(client: TestClient, monkeypatch):
    _local_stub(monkeypatch)

    res = client.get("/api/local-engine")
    assert res.status_code == 200
    body = res.json()
    assert body == {
        "kind": "not_installed",
        "model": STUB_MODEL,
        "download_bytes": 1024,
    }
    _assert_no_endpoint(body)


def test_ensure_then_settle_is_ready_without_endpoint(client: TestClient, monkeypatch):
    _local_stub(monkeypatch)

    ensured = client.post("/api/local-engine/ensure")
    assert ensured.status_code == 200
    assert ensured.json()["kind"] == "acquiring"
    _assert_no_endpoint(ensured.json())

    stub.settle()
    res = client.get("/api/local-engine")
    assert res.status_code == 200
    body = res.json()
    assert body["kind"] == "ready"
    assert body["model"] == STUB_MODEL
    assert body["model"]["id"] == "stub/tiny-moe"
    assert set(body) == {"kind", "model", "started_at"}
    assert isinstance(body["started_at"], (int, float))
    _assert_no_endpoint(body)


def test_settings_local_not_ready(client: TestClient, monkeypatch):
    _local_stub(monkeypatch)

    res = client.get("/api/settings")
    assert res.status_code == 200
    body = res.json()
    assert body["llm_configured"] is False
    assert body["connected_providers"]["local"] is False
    assert "LOCAL_ENGINE_RUNTIME" not in body["values"]
    assert body["local_engine"]["kind"] == "not_installed"
    _assert_no_endpoint(body)


def test_settings_local_ready_after_settle(client: TestClient, monkeypatch):
    _local_stub(monkeypatch)

    client.post("/api/local-engine/ensure")
    stub.settle()

    res = client.get("/api/settings")
    assert res.status_code == 200
    body = res.json()
    assert body["llm_configured"] is True
    assert body["connected_providers"]["local"] is True
    assert "LOCAL_ENGINE_RUNTIME" not in body["values"]
    assert body["local_engine"]["kind"] == "ready"
    assert body["local_engine"]["model"]["id"] == "stub/tiny-moe"
    _assert_no_endpoint(body)


def test_put_settings_persists_public_key_hides_runtime(client: TestClient, monkeypatch):
    _local_stub(monkeypatch)

    put = client.put(
        "/api/settings",
        json={
            "values": {
                "LLM_MAX_TOKENS": "2048",
                "LOCAL_ENGINE_RUNTIME": "edge0",
            }
        },
    )
    assert put.status_code == 200, put.text
    updated = put.json()["updated"]
    assert "LLM_MAX_TOKENS" in updated
    assert "LOCAL_ENGINE_RUNTIME" not in updated
    assert "LOCAL_ENGINE_RUNTIME" not in put.json()["values"]
    assert put.json()["values"]["LLM_MAX_TOKENS"] == "2048"

    res = client.get("/api/settings")
    assert res.status_code == 200
    values = res.json()["values"]
    assert values["LLM_MAX_TOKENS"] == "2048"
    assert "LOCAL_ENGINE_RUNTIME" not in values
    assert os.environ.get("LOCAL_ENGINE_RUNTIME") == "stub"
