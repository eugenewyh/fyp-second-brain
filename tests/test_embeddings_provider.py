"""Embedding provider + fingerprint helpers."""

from __future__ import annotations


def test_embedding_provider_defaults(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "fastembed")
    monkeypatch.delenv("EMBEDDING_MODEL", raising=False)
    from second_brain.memory import embeddings as emb

    # Reload module-level resolution uses env
    assert emb.embedding_provider() == "fastembed"
    assert "bge" in emb.embedding_model_name().lower() or "BAAI" in emb.embedding_model_name()


def test_fingerprint_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "fastembed")
    monkeypatch.setenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    from second_brain.memory import embeddings as emb

    monkeypatch.setattr(emb, "CHROMA_PATH", tmp_path)
    monkeypatch.setattr(emb, "FINGERPRINT_PATH", tmp_path / "embedding_fingerprint.json")

    written = emb.write_fingerprint(dims=384)
    assert written["provider"] == "fastembed"
    assert written["dims"] == 384
    assert emb.fingerprint_matches()
    assert emb.read_fingerprint()["model"] == "BAAI/bge-small-en-v1.5"


def test_bundled_nvidia_api_key(monkeypatch):
    from second_brain.memory import llm as llm_mod

    monkeypatch.setenv("LLM_PROVIDER", "nvidia")
    monkeypatch.setenv("NVIDIA_API_KEY", "")
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setattr(llm_mod, "bundled_nvidia_api_key", lambda: "nvapi-bundled")
    assert llm_mod._api_key() == "nvapi-bundled"
    assert llm_mod.using_bundled_nvidia() is True
    assert llm_mod.llm_is_configured() is True

    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-user")
    assert llm_mod._api_key() == "nvapi-user"
    assert llm_mod.using_bundled_nvidia() is False


def test_llm_fast_role(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("LLM_MODEL", "openai/gpt-oss-120b")
    monkeypatch.setenv("LLM_FAST_MODEL", "qwen/qwen3-32b")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    from second_brain.memory import llm as llm_mod

    assert llm_mod._model_for_role("main") == "openai/gpt-oss-120b"
    assert llm_mod._model_for_role("fast") == "qwen/qwen3-32b"
    monkeypatch.delenv("LLM_FAST_MODEL", raising=False)
    assert llm_mod._model_for_role("fast") == "openai/gpt-oss-120b"
