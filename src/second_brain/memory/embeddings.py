"""Embedding backends for vault search (Chroma).

Default is bundled local fastembed (Khoj-style) so users do not need Ollama.
Ollama and OpenAI-compatible cloud embeddings remain optional.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Protocol

from second_brain.config import (
    CHROMA_PATH,
    EMBEDDING_MODEL,
    EMBEDDING_PROVIDER,
    OLLAMA_BASE_URL,
    data_root,
)

logger = logging.getLogger(__name__)

FINGERPRINT_PATH = CHROMA_PATH / "embedding_fingerprint.json"

# Sensible defaults per provider when EMBEDDING_MODEL is blank / legacy
_DEFAULT_MODELS = {
    "fastembed": "BAAI/bge-small-en-v1.5",
    "ollama": "nomic-embed-text",
    "openai_compatible": "text-embedding-3-small",
}


class EmbeddingsProtocol(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


_embeddings_lock = threading.Lock()
# (provider, model, instance) — rebuild when provider/model changes
_embeddings_cache: tuple[str, str, EmbeddingsProtocol] | None = None


def fastembed_cache_dir() -> Path:
    """Durable on-disk cache. Temp dirs drop incomplete downloads and break vault search."""
    raw = (os.getenv("FASTEMBED_CACHE_PATH") or "").strip()
    if raw:
        path = Path(raw).expanduser().resolve()
    else:
        path = (data_root() / "fastembed_cache").resolve()
        os.environ["FASTEMBED_CACHE_PATH"] = str(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def purge_incomplete_fastembed_downloads(cache: Path | None = None) -> int:
    """Remove zero-byte / .incomplete HuggingFace blobs so the next load re-fetches."""
    root = cache or fastembed_cache_dir()
    removed = 0
    if not root.is_dir():
        return 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        name = path.name
        stale = name.endswith(".incomplete") or (
            name.endswith(".onnx") and path.stat().st_size == 0
        )
        if stale:
            try:
                path.unlink()
                removed += 1
            except OSError as e:
                logger.warning("Could not remove incomplete embed file %s: %s", path, e)
    return removed


def _friendly_embed_error(exc: BaseException) -> str:
    raw = str(exc).strip() or exc.__class__.__name__
    lower = raw.lower()
    if (
        "no_suchfile" in lower
        or "model_optimized.onnx" in lower
        or ".incomplete" in lower
        or ("load model" in lower and "failed" in lower)
    ):
        return (
            "Local search model is missing or incomplete. "
            "Nous will re-download it — tap Retry, or check your network once."
        )
    if len(raw) > 220:
        return raw[:217] + "…"
    return raw


def reset_embeddings_cache() -> None:
    global _embeddings_cache
    with _embeddings_lock:
        _embeddings_cache = None


class _FastEmbedWrapper:
    """Thin wrapper so callers share embed_documents / embed_query."""

    def __init__(self, model_name: str):
        from fastembed import TextEmbedding

        fastembed_cache_dir()
        purge_incomplete_fastembed_downloads()
        try:
            self._model = TextEmbedding(model_name=model_name)
        except Exception as first:
            # Corrupt partial download — wipe incompletes once and retry.
            purge_incomplete_fastembed_downloads()
            logger.warning("fastembed load failed (%s); retrying after cache cleanup", first)
            try:
                self._model = TextEmbedding(model_name=model_name)
            except Exception as second:
                raise RuntimeError(_friendly_embed_error(second)) from second

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [vec.tolist() if hasattr(vec, "tolist") else list(vec) for vec in self._model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        vec = next(self._model.embed([text]))
        return vec.tolist() if hasattr(vec, "tolist") else list(vec)


def embedding_provider() -> str:
    raw = (os.getenv("EMBEDDING_PROVIDER") or EMBEDDING_PROVIDER or "fastembed").strip().lower()
    aliases = {
        "fast": "fastembed",
        "local": "fastembed",
        "bundled": "fastembed",
        "openai": "openai_compatible",
        "openrouter": "openai_compatible",
        "cloud": "openai_compatible",
    }
    return aliases.get(raw, raw)


def embedding_model_name() -> str:
    configured = (os.getenv("EMBEDDING_MODEL") or EMBEDDING_MODEL or "").strip()
    provider = embedding_provider()
    default = _DEFAULT_MODELS.get(provider, "BAAI/bge-small-en-v1.5")
    # Legacy default was nomic; if switching to fastembed without updating model, remap
    if provider == "fastembed" and configured in {"", "nomic-embed-text", "nomic-embed-text:latest"}:
        return default
    if provider == "openai_compatible" and configured in {"", "nomic-embed-text", "nomic-embed-text:latest"}:
        return default
    return configured or default


def _openai_embed_credentials() -> tuple[str, str | None]:
    key = (
        os.getenv("EMBEDDING_API_KEY", "").strip()
        or os.getenv("OPENAI_API_KEY", "").strip()
        or os.getenv("OPENROUTER_API_KEY", "").strip()
        or os.getenv("LLM_API_KEY", "").strip()
        or os.getenv("CUSTOM_API_KEY", "").strip()
    )
    base = (
        os.getenv("EMBEDDING_BASE_URL", "").strip()
        or os.getenv("LLM_BASE_URL", "").strip()
        or os.getenv("CUSTOM_BASE_URL", "").strip()
        or None
    )
    provider = (os.getenv("LLM_PROVIDER") or "").strip().lower()
    if not base and provider == "openrouter":
        base = "https://openrouter.ai/api/v1"
    if not base and provider == "openai":
        base = "https://api.openai.com/v1"
    return key, base.rstrip("/") if base else None


def _build_embeddings(provider: str, model: str) -> EmbeddingsProtocol:
    if provider == "fastembed":
        return _FastEmbedWrapper(model)

    if provider == "ollama":
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(
            model=model,
            base_url=os.getenv("OLLAMA_BASE_URL", OLLAMA_BASE_URL),
        )

    if provider in {"openai_compatible", "openai", "openrouter"}:
        from langchain_openai import OpenAIEmbeddings

        api_key, base_url = _openai_embed_credentials()
        if not api_key:
            raise ValueError(
                "Cloud embeddings need an API key "
                "(EMBEDDING_API_KEY, OPENAI_API_KEY, OPENROUTER_API_KEY, or LLM_API_KEY)."
            )
        kwargs: dict[str, Any] = {"model": model, "api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        return OpenAIEmbeddings(**kwargs)

    raise ValueError(
        f"Unknown EMBEDDING_PROVIDER: {provider!r}. "
        "Use fastembed, ollama, or openai_compatible."
    )


def get_embeddings() -> EmbeddingsProtocol:
    """Return a process-wide embeddings backend keyed by (provider, model)."""
    global _embeddings_cache
    provider = embedding_provider()
    model = embedding_model_name()
    with _embeddings_lock:
        cached = _embeddings_cache
        if cached is not None and cached[0] == provider and cached[1] == model:
            return cached[2]
        emb = _build_embeddings(provider, model)
        _embeddings_cache = (provider, model, emb)
        return emb


def current_fingerprint(*, dims: int | None = None) -> dict[str, Any]:
    fp: dict[str, Any] = {
        "provider": embedding_provider(),
        "model": embedding_model_name(),
    }
    if dims is not None:
        fp["dims"] = dims
    return fp


def read_fingerprint() -> dict[str, Any] | None:
    if not FINGERPRINT_PATH.is_file():
        return None
    try:
        data = json.loads(FINGERPRINT_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def write_fingerprint(dims: int | None = None) -> dict[str, Any]:
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    stored = read_fingerprint() or {}
    fp = current_fingerprint(dims=dims if dims is not None else stored.get("dims"))
    if dims is not None:
        fp["dims"] = dims
    FINGERPRINT_PATH.write_text(json.dumps(fp, indent=2) + "\n", encoding="utf-8")
    return fp


def fingerprint_matches(stored: dict[str, Any] | None = None) -> bool:
    stored = stored if stored is not None else read_fingerprint()
    if not stored:
        return False
    cur = current_fingerprint()
    return (
        str(stored.get("provider", "")).lower() == cur["provider"]
        and str(stored.get("model", "")) == cur["model"]
    )


def probe_embeddings() -> dict[str, Any]:
    """Health probe for status API. Never raises."""
    provider = embedding_provider()
    model = embedding_model_name()
    stored = read_fingerprint()
    result: dict[str, Any] = {
        "embeddings_provider": provider,
        "embeddings_model": model,
        "embeddings_ok": False,
        "embeddings_error": "",
        "embedding_dims": None,
        "reindex_required": False,
        "fingerprint": stored,
    }
    try:
        emb = get_embeddings()
        vec = emb.embed_query("nous embedding health check")
        dims = len(vec)
        result["embedding_dims"] = dims
        result["embeddings_ok"] = dims > 0
        if not stored or not fingerprint_matches(stored):
            # Empty collection: mismatch is informational until first ingest writes fingerprint
            from second_brain.memory.chroma_store import collection_count

            count = collection_count()
            if count > 0 and (not stored or not fingerprint_matches(stored)):
                result["reindex_required"] = True
                if stored and stored.get("dims") and int(stored["dims"]) != dims:
                    result["embeddings_error"] = (
                        f"Embedding model changed ({stored.get('provider')}/{stored.get('model')} "
                        f"→ {provider}/{model}). Re-ingest the vault."
                    )
                elif not stored:
                    result["embeddings_error"] = (
                        "Vault was indexed without a fingerprint for the current embedding backend. "
                        "Re-ingest to align search vectors."
                    )
                else:
                    result["embeddings_error"] = (
                        f"Embedding backend mismatch. Re-ingest with {provider}/{model}."
                    )
        # Detect corrupt HNSW (peek may still work; query fails)
        if result["embeddings_ok"]:
            try:
                from second_brain.memory.chroma_store import (
                    collection_count,
                    get_collection,
                    is_hnsw_corruption_error,
                )

                if collection_count() > 0:
                    get_collection().query(
                        query_embeddings=[vec],
                        n_results=1,
                        include=["documents"],
                    )
            except Exception as qe:
                from second_brain.memory.chroma_store import is_hnsw_corruption_error

                if is_hnsw_corruption_error(qe):
                    result["reindex_required"] = True
                    result["embeddings_ok"] = False
                    result["embeddings_error"] = (
                        "Knowledge index is corrupted (Chroma HNSW). "
                        "Reset and re-ingest the vault (Ingest with reset)."
                    )
                else:
                    logger.warning("Index probe query failed: %s", qe)
    except Exception as e:
        result["embeddings_ok"] = False
        result["embeddings_error"] = _friendly_embed_error(e)
        logger.warning("Embedding probe failed: %s", e)
    return result


def repair_embeddings() -> dict[str, Any]:
    """Clear bad cache entries and reload the embedding backend."""
    if embedding_provider() == "fastembed":
        fastembed_cache_dir()
        purged = purge_incomplete_fastembed_downloads()
    else:
        purged = 0
    reset_embeddings_cache()
    probe = probe_embeddings()
    probe["purged_incomplete"] = purged
    return probe
