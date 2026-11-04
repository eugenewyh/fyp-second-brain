"""Embedding provider + fingerprint helpers."""

from __future__ import annotations

import os


def test_embedding_provider_defaults(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "fastembed")
    monkeypatch.delenv("EMBEDDING_MODEL", raising=False)
    from second_brain.memory import embeddings as emb

    # Reload module-level resolution uses env
    assert emb.embedding_provider() == "fastembed"
    assert "bge" in emb.embedding_model_name().lower() or "BAAI" in emb.embedding_model_name()


def test_get_embeddings_singleton(monkeypatch):
    from second_brain.memory import embeddings as emb

    monkeypatch.setenv("EMBEDDING_PROVIDER", "fastembed")
    monkeypatch.setenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    sentinel = object()
    monkeypatch.setattr(emb, "_embeddings_cache", None)
    monkeypatch.setattr(emb, "_build_embeddings", lambda *_a, **_k: sentinel)
    a = emb.get_embeddings()
    b = emb.get_embeddings()
    assert a is b is sentinel


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


def test_fastembed_cache_defaults_to_data_root(tmp_path, monkeypatch):
    from second_brain.memory import embeddings as emb

    monkeypatch.delenv("FASTEMBED_CACHE_PATH", raising=False)
    monkeypatch.setattr(emb, "data_root", lambda: tmp_path)
    cache = emb.fastembed_cache_dir()
    assert cache == (tmp_path / "fastembed_cache").resolve()
    assert cache.is_dir()
    assert os.environ["FASTEMBED_CACHE_PATH"] == str(cache)


def test_purge_incomplete_fastembed_downloads(tmp_path):
    from second_brain.memory import embeddings as emb

    bad = tmp_path / "blob.incomplete"
    bad.write_bytes(b"")
    empty_onnx = tmp_path / "model.onnx"
    empty_onnx.write_bytes(b"")
    good = tmp_path / "ok.bin"
    good.write_bytes(b"data")
    assert emb.purge_incomplete_fastembed_downloads(tmp_path) == 2
    assert not bad.exists()
    assert not empty_onnx.exists()
    assert good.exists()


def test_friendly_embed_error_maps_missing_onnx():
    from second_brain.memory import embeddings as emb

    msg = emb._friendly_embed_error(
        RuntimeError(
            "[ONNXRuntimeError] : 3 : NO_SUCHFILE : Load model from /tmp/model_optimized.onnx failed"
        )
    )
    assert "incomplete" in msg.lower()


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
