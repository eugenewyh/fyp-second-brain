import logging
import os
import re
import time
from typing import Any, Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_ollama import ChatOllama

logger = logging.getLogger(__name__)

# Free-tier friendly defaults on Groq
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
DEFAULT_GROQ_FALLBACK = "qwen/qwen3-32b"

LlmRole = Literal["main", "fast"]

# Named OpenAI-compatible presets (base URL only; key via LLM_API_KEY / provider key)
PROVIDER_BASE_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "xai": "https://api.x.ai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}

# Aliases → canonical provider id
PROVIDER_ALIASES: dict[str, str] = {
    "openai_compatible": "openai_compatible",
    "openai-compatible": "openai_compatible",
    "compatible": "openai_compatible",
    "custom": "openai_compatible",
    "grok": "xai",
    "x-ai": "xai",
}


def _provider() -> str:
    raw = os.getenv("LLM_PROVIDER", "groq").strip().lower()
    return PROVIDER_ALIASES.get(raw, raw)


def _primary_model() -> str:
    provider = _provider()
    if provider == "groq":
        default = DEFAULT_GROQ_MODEL
    elif provider == "ollama":
        default = "qwen3:8b"
    elif provider == "xai":
        default = "grok-3-mini"
    elif provider == "openrouter":
        default = "openai/gpt-4o-mini"
    else:
        default = "gpt-4o-mini"
    return os.getenv("LLM_MODEL", default).strip() or default


def _fast_model() -> str | None:
    """Optional light-tier model (Ask / verifier). Empty → use main."""
    return os.getenv("LLM_FAST_MODEL", "").strip() or None


def _model_for_role(role: LlmRole) -> str:
    if role == "fast":
        fast = _fast_model()
        if fast:
            return fast
    return _primary_model()


def _api_key() -> str:
    """BYOK: provider-specific key first, then shared LLM_API_KEY."""
    provider = _provider()
    generic = os.getenv("LLM_API_KEY", "").strip()
    if provider == "groq":
        return os.getenv("GROQ_API_KEY", "").strip() or generic
    if provider == "openai":
        return os.getenv("OPENAI_API_KEY", "").strip() or generic
    if provider == "xai":
        return (
            os.getenv("XAI_API_KEY", "").strip()
            or os.getenv("GROK_API_KEY", "").strip()
            or generic
        )
    if provider == "openrouter":
        return os.getenv("OPENROUTER_API_KEY", "").strip() or generic
    if provider == "openai_compatible":
        return os.getenv("CUSTOM_API_KEY", "").strip() or generic
    return generic


def _base_url() -> str | None:
    provider = _provider()
    if provider == "openai_compatible":
        custom = os.getenv("CUSTOM_BASE_URL", "").strip() or os.getenv(
            "LLM_BASE_URL", ""
        ).strip()
        return custom.rstrip("/") or None
    explicit = os.getenv("LLM_BASE_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    return PROVIDER_BASE_URLS.get(provider)


def _max_tokens() -> int:
    return int(os.getenv("LLM_MAX_TOKENS") or os.getenv("GROQ_MAX_TOKENS", "4096"))


def _fallback_model() -> str | None:
    """Optional secondary model when primary is rate-limited."""
    provider = _provider()
    primary = _primary_model()
    fb = (
        os.getenv("LLM_FALLBACK_MODEL", "").strip()
        or os.getenv("GROQ_FALLBACK_MODEL", "").strip()
    )
    if provider == "groq" and not fb:
        fb = DEFAULT_GROQ_FALLBACK
    if not fb or fb == primary:
        return None
    # Only use automatic fallback for cloud providers with keys
    if provider == "ollama":
        return None
    return fb


def _chat_openai_compatible(
    *,
    model_name: str,
    temperature: float,
    api_key: str,
    base_url: str | None,
) -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    kwargs: dict[str, Any] = {
        "model": model_name,
        "temperature": temperature,
        "max_tokens": _max_tokens(),
        "api_key": api_key,
    }
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


def get_llm(
    temperature: float = 0.2,
    model: str | None = None,
    *,
    role: LlmRole = "main",
) -> BaseChatModel:
    """Return the configured chat model (BYOK multi-provider).

    role=main → LLM_MODEL (planner / synthesizer)
    role=fast → LLM_FAST_MODEL if set, else main (Ask / verifier)
    """
    provider = _provider()
    model_name = (model or _model_for_role(role)).strip()
    max_tokens = _max_tokens()

    if provider == "groq":
        api_key = _api_key()
        if not api_key:
            raise ValueError(
                "API key is not set. Add GROQ_API_KEY or LLM_API_KEY in Settings."
            )
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key,
        )

    if provider == "ollama":
        return ChatOllama(
            model=model_name,
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=temperature,
        )

    if provider in {"openai", "xai", "openrouter", "openai_compatible"}:
        api_key = _api_key()
        if not api_key:
            raise ValueError(
                f"API key is not set for provider {provider!r}. "
                "Set LLM_API_KEY (or provider-specific key) in Settings."
            )
        base = _base_url()
        if provider == "openai_compatible" and not base:
            raise ValueError(
                "LLM_BASE_URL is required for openai_compatible provider "
                "(e.g. https://api.openai.com/v1)."
            )
        return _chat_openai_compatible(
            model_name=model_name,
            temperature=temperature,
            api_key=api_key,
            base_url=base,
        )

    raise ValueError(
        f"Unknown LLM_PROVIDER: {provider!r}. "
        "Use groq, ollama, openai, xai, openrouter, or openai_compatible."
    )


def _is_rate_limit_error(err: BaseException) -> bool:
    text = str(err).lower()
    name = type(err).__name__.lower()
    return (
        "rate_limit" in text
        or "rate limit" in text
        or "429" in text
        or "ratelimit" in name
        or "tokens per minute" in text
        or "tokens per day" in text
        or "request limit" in text
        or "temporarily overloaded" in text
        or "service unavailable" in text
        or " 502" in text
        or " 503" in text
        or "'code': 502" in text
        or '"code": 502' in text
    )


def _retry_wait_seconds(err: BaseException, attempt: int) -> float:
    """Parse 'try again in Xs' or use exponential backoff."""
    text = str(err)
    match = re.search(r"try again in ([\d.]+)\s*s", text, re.I)
    if match:
        return min(float(match.group(1)) + 1.0, 90.0)
    return min(15.0 * (2**attempt), 90.0)


def _invoke_with_retries(
    llm: BaseChatModel,
    messages: list[BaseMessage] | list[Any],
    *,
    model_label: str,
    max_retries: int,
) -> Any:
    last_err: BaseException | None = None
    for attempt in range(max_retries):
        try:
            return llm.invoke(messages)
        except Exception as e:
            last_err = e
            if _is_rate_limit_error(e) and attempt < max_retries - 1:
                wait = _retry_wait_seconds(e, attempt)
                logger.warning(
                    "LLM rate limited on %s (attempt %s/%s). Waiting %.1fs…",
                    model_label,
                    attempt + 1,
                    max_retries,
                    wait,
                )
                time.sleep(wait)
                continue
            raise
    assert last_err is not None
    raise last_err


def invoke_llm(
    messages: list[BaseMessage] | list[Any],
    temperature: float = 0.2,
    max_retries: int = 4,
    *,
    role: LlmRole = "main",
) -> Any:
    """Invoke the configured LLM with retries; fall back on rate-limit when configured."""
    primary = _model_for_role(role)
    llm = get_llm(temperature=temperature, model=primary, role=role)

    try:
        return _invoke_with_retries(
            llm, messages, model_label=primary, max_retries=max_retries
        )
    except Exception as e:
        if not _is_rate_limit_error(e):
            raise

        fallback = _fallback_model()
        if not fallback:
            raise RuntimeError(
                "AI rate limit reached. Wait 30–60 seconds between research runs, "
                "or switch model/provider in Settings."
            ) from e

        logger.warning(
            "Primary model %s rate-limited after retries — falling back to %s",
            primary,
            fallback,
        )
        try:
            fb_llm = get_llm(temperature=temperature, model=fallback, role=role)
            return _invoke_with_retries(
                fb_llm, messages, model_label=fallback, max_retries=max_retries
            )
        except Exception as e2:
            if _is_rate_limit_error(e2):
                raise RuntimeError(
                    "AI rate limit reached on both primary and fallback models "
                    f"({primary} → {fallback}). Wait before the next research run."
                ) from e2
            raise


def llm_is_configured() -> bool:
    """True if the current provider has enough config to run (for /api/settings status)."""
    provider = _provider()
    if provider == "ollama":
        return True
    return bool(_api_key())
