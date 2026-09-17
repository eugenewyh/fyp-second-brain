from __future__ import annotations

from urllib.parse import urlparse

import pytest
from langchain_openai import ChatOpenAI

from second_brain.local_engine import LocalEngineNotReady, engine_state
from second_brain.local_engine.engine import _reset
from second_brain.local_engine.runtimes import stub
from second_brain.memory.llm import get_llm, llm_is_configured


@pytest.fixture(autouse=True)
def _isolate_local_engine(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCAL_ENGINE_HOME", str(tmp_path / "home"))
    stub.reset()
    _reset()
    yield
    stub.reset()
    _reset()


def _local_stub(monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_ENGINE_RUNTIME", "stub")
    monkeypatch.setenv("LLM_PROVIDER", "local")
    monkeypatch.setenv("LLM_MODEL", "stub/tiny-moe")


def test_get_llm_local_not_ready(monkeypatch):
    _local_stub(monkeypatch)

    with pytest.raises(LocalEngineNotReady):
        get_llm()
    assert llm_is_configured() is False


def test_get_llm_local_ready_uses_engine_endpoint(monkeypatch):
    from second_brain.local_engine import ensure_ready

    _local_stub(monkeypatch)
    ensure_ready()
    stub.settle()

    llm = get_llm()
    assert isinstance(llm, ChatOpenAI)
    assert llm.model_name == "stub/tiny-moe"
    base = getattr(llm, "openai_api_base", None) or getattr(llm, "base_url", None)
    assert urlparse(str(base)).hostname == "127.0.0.1"
    assert llm_is_configured() is True


def test_get_llm_local_model_mismatch(monkeypatch):
    from second_brain.local_engine import Ready, ensure_ready

    _local_stub(monkeypatch)
    ensure_ready()
    stub.settle()
    assert isinstance(engine_state(), Ready)

    with pytest.raises(ValueError, match="other-id") as excinfo:
        get_llm(model="other-id")
    assert not isinstance(excinfo.value, LocalEngineNotReady)
