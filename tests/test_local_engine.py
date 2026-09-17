from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import pytest

from second_brain.local_engine import Failed, NotInstalled, Ready, engine_state, ensure_ready
from second_brain.local_engine.engine import _reset
from second_brain.local_engine.health import (
    Malformed,
    Serving,
    WrongModel,
    parse_models_payload,
)
from second_brain.local_engine.runtimes import stub
from second_brain.local_engine.state import Endpoint

MODELS_PAYLOAD = {
    "object": "list",
    "data": [
        {
            "id": "stub/tiny-moe",
            "object": "model",
            "created": 0,
            "owned_by": "stub",
        }
    ],
}


@pytest.fixture(autouse=True)
def _isolate_local_engine():
    stub.reset()
    _reset()
    yield
    stub.reset()
    _reset()


def test_stub_engine_starts_not_installed(monkeypatch):
    monkeypatch.setenv("LOCAL_ENGINE_RUNTIME", "stub")
    monkeypatch.setenv("LLM_PROVIDER", "local")
    monkeypatch.setenv("LLM_MODEL", "stub/tiny-moe")

    assert isinstance(engine_state(), NotInstalled)


def test_stub_ignores_cloud_llm_model(monkeypatch):
    monkeypatch.setenv("LOCAL_ENGINE_RUNTIME", "stub")
    monkeypatch.setenv("LLM_PROVIDER", "nvidia")
    monkeypatch.setenv("LLM_MODEL", "nvidia/nemotron-3-super-120b-a12b")

    state = engine_state()
    assert isinstance(state, NotInstalled)
    assert state.model.id == "stub/tiny-moe"


def test_ensure_ready_settles_to_ready(monkeypatch):
    monkeypatch.setenv("LOCAL_ENGINE_RUNTIME", "stub")
    monkeypatch.setenv("LLM_PROVIDER", "local")
    monkeypatch.setenv("LLM_MODEL", "stub/tiny-moe")

    ensure_ready()
    stub.settle()
    state = engine_state()
    assert isinstance(state, Ready)
    parsed = urlparse(state.endpoint.base_url)
    assert parsed.scheme == "http"
    assert parsed.hostname == "127.0.0.1"
    assert state.model.id == "stub/tiny-moe"


def test_parse_models_payload_recorded_json():
    serving = parse_models_payload(MODELS_PAYLOAD, expect_model="stub/tiny-moe")
    assert isinstance(serving, Serving)
    wrong = parse_models_payload(MODELS_PAYLOAD, expect_model="edge0/moe-120b-a6b-mxfp4")
    assert isinstance(wrong, WrongModel)
    assert wrong.serving_id == "stub/tiny-moe"
    assert isinstance(parse_models_payload("not-a-payload", expect_model="stub/tiny-moe"), Malformed)
    assert isinstance(parse_models_payload(None, expect_model="stub/tiny-moe"), Malformed)
    assert isinstance(parse_models_payload({"object": "list"}, expect_model="stub/tiny-moe"), Malformed)
    assert isinstance(
        parse_models_payload({"object": "list", "data": []}, expect_model="stub/tiny-moe"),
        Malformed,
    )


def test_retry_after_crash_mid_download_resumes(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCAL_ENGINE_RUNTIME", "stub")
    monkeypatch.setenv("LLM_PROVIDER", "local")
    monkeypatch.setenv("LLM_MODEL", "stub/tiny-moe")
    monkeypatch.setenv("LOCAL_ENGINE_HOME", str(tmp_path))

    ensure_ready()
    stub.crash_during(step="weights", at_fraction=0.5)
    assert isinstance(engine_state(), Failed)

    ensure_ready()
    stub.settle()
    assert isinstance(engine_state(), Ready)
    assert stub.bytes_refetched < stub.total_bytes


def test_concurrent_ensure_ready_joins_in_flight(monkeypatch):
    monkeypatch.setenv("LOCAL_ENGINE_RUNTIME", "stub")
    monkeypatch.setenv("LLM_PROVIDER", "local")
    monkeypatch.setenv("LLM_MODEL", "stub/tiny-moe")

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(ensure_ready)
        second = pool.submit(ensure_ready)
        first.result(timeout=2)
        second.result(timeout=2)

    assert stub.worker_starts == 1
    stub.settle()
    assert isinstance(engine_state(), Ready)


def test_endpoint_is_not_constructible_without_health_parse():
    with pytest.raises(TypeError, match="successful health parse"):
        Endpoint("http://127.0.0.1:9/v1", "token")
