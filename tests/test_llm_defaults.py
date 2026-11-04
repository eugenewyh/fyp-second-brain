from __future__ import annotations

import pytest

from second_brain.config import MAX_GOAL_PASSES
from second_brain.memory import llm as llm_mod


def test_max_goal_passes_defaults_to_one():
    assert MAX_GOAL_PASSES == 1


def test_nvidia_fast_role_defaults_to_fallback(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LLM_PROVIDER", "nvidia")
    monkeypatch.delenv("LLM_FAST_MODEL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    assert llm_mod._model_for_role("fast") == llm_mod.DEFAULT_NVIDIA_FALLBACK
    assert llm_mod._model_for_role("main") == llm_mod.DEFAULT_NVIDIA_MODEL
    assert llm_mod.DEFAULT_NVIDIA_FALLBACK == "nvidia/nemotron-3-super-120b-a12b"


def test_explicit_fast_model_wins(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LLM_PROVIDER", "nvidia")
    monkeypatch.setenv("LLM_FAST_MODEL", "custom/fast")
    assert llm_mod._model_for_role("fast") == "custom/fast"


def test_stream_llm_yields_chunk_text(monkeypatch: pytest.MonkeyPatch):
    class _FakeLLM:
        def stream(self, _messages):
            yield type("C", (), {"content": "Hel"})()
            yield type("C", (), {"content": "lo"})()

    monkeypatch.setenv("LLM_PROVIDER", "nvidia")
    monkeypatch.setattr(llm_mod, "get_llm", lambda **_k: _FakeLLM())
    assert "".join(llm_mod.stream_llm([], role="fast")) == "Hello"


def test_fast_max_tokens_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("LLM_FAST_MAX_TOKENS", raising=False)
    monkeypatch.delenv("LLM_MAX_TOKENS", raising=False)
    monkeypatch.delenv("GROQ_MAX_TOKENS", raising=False)
    assert llm_mod._max_tokens(role="fast") == 1024
    assert llm_mod._max_tokens(role="main") == 4096
    monkeypatch.setenv("LLM_FAST_MAX_TOKENS", "512")
    assert llm_mod._max_tokens(role="fast") == 512
    assert llm_mod._max_tokens(role="main") == 4096
