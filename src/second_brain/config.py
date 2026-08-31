import os
from pathlib import Path

from dotenv import load_dotenv

# Source tree root (dev checkout). Release uses NOUS_BUNDLE_ROOT / NOUS_DATA_DIR.
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _path_from_env(name: str, default: Path) -> Path:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    return Path(raw).expanduser().resolve()


BUNDLE_ROOT = _path_from_env("NOUS_BUNDLE_ROOT", PROJECT_ROOT)
DATA_ROOT = _path_from_env("NOUS_DATA_DIR", PROJECT_ROOT)


def bundle_root() -> Path:
    return BUNDLE_ROOT


def data_root() -> Path:
    return DATA_ROOT


def load_env_files() -> None:
    """Operator defaults (build) then user Settings .env (writable data dir)."""
    operator = BUNDLE_ROOT / "operator.env"
    if operator.is_file():
        load_dotenv(operator, override=False)
    user_env = DATA_ROOT / ".env"
    if user_env.is_file():
        load_dotenv(user_env, override=True)
    if DATA_ROOT == PROJECT_ROOT:
        dev_env = PROJECT_ROOT / ".env"
        if dev_env.is_file():
            load_dotenv(dev_env, override=True)


def ensure_data_dirs() -> None:
    (DATA_ROOT / "data" / "documents").mkdir(parents=True, exist_ok=True)
    (DATA_ROOT / "data" / "chroma").mkdir(parents=True, exist_ok=True)


load_env_files()
ensure_data_dirs()


def _env_int(name: str, default: int) -> int:
    """Parse int env vars; empty/invalid values fall back to default (Settings UI can blank them)."""
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return int(str(raw).strip())
    except ValueError:
        return default


LLM_PROVIDER = os.getenv("LLM_PROVIDER", "nvidia").strip().lower()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
# Embeddings: fastembed (bundled, default) | ollama | openai_compatible
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "fastembed").strip().lower()
_DEFAULT_EMBED_MODEL = (
    "BAAI/bge-small-en-v1.5"
    if EMBEDDING_PROVIDER in {"", "fastembed", "fast", "local", "bundled"}
    else "nomic-embed-text"
    if EMBEDDING_PROVIDER == "ollama"
    else "text-embedding-3-small"
)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", _DEFAULT_EMBED_MODEL)
LLM_MODEL = os.getenv(
    "LLM_MODEL",
    "nvidia/nemotron-3-super-120b-a12b"
    if LLM_PROVIDER == "nvidia"
    else "openai/gpt-oss-120b"
    if LLM_PROVIDER == "groq"
    else "qwen3:8b",
)
# Optional cheaper/faster model for Ask + verifier (Factory/Hermes light tier)
LLM_FAST_MODEL = os.getenv("LLM_FAST_MODEL", "").strip()
# Used when primary model hits rate limits (429)
GROQ_FALLBACK_MODEL = os.getenv("GROQ_FALLBACK_MODEL", "qwen/qwen3-32b")
_DEFAULT_LLM_FALLBACK = (
    "nvidia/nemotron-3-nano-30b-a3b"
    if LLM_PROVIDER == "nvidia"
    else GROQ_FALLBACK_MODEL
)
LLM_FALLBACK_MODEL = os.getenv("LLM_FALLBACK_MODEL", _DEFAULT_LLM_FALLBACK)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NOUS_NVIDIA_API_KEY = os.getenv("NOUS_NVIDIA_API_KEY", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
GROQ_MAX_TOKENS = _env_int("GROQ_MAX_TOKENS", 4096)
LLM_MAX_TOKENS = _env_int("LLM_MAX_TOKENS", GROQ_MAX_TOKENS)
_DEFAULT_CHROMA = DATA_ROOT / "data" / "chroma"
CHROMA_PATH = Path(os.getenv("CHROMA_PATH", str(_DEFAULT_CHROMA)))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "personal_knowledge")
DOCUMENTS_DIR = DATA_ROOT / "data" / "documents"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
RETRIEVAL_TOP_K = _env_int("RETRIEVAL_TOP_K", 5)
RETRIEVAL_TOP_K_PER_QUERY = _env_int("RETRIEVAL_TOP_K_PER_QUERY", 5)
# Deep Ask: comprehensive explain-from-memory (source-pinned, claim-first)
DEEP_ASK_MEMORY_CHARS = _env_int("DEEP_ASK_MEMORY_CHARS", 12000)
DEEP_ASK_TOP_K = _env_int("DEEP_ASK_TOP_K", 12)
DEEP_ASK_CHUNK_EXCERPT = _env_int("DEEP_ASK_CHUNK_EXCERPT", 800)
DEEP_ASK_CLAIM_LIMIT = _env_int("DEEP_ASK_CLAIM_LIMIT", 40)
DEEP_ASK_MAP_REDUCE_CHARS = _env_int("DEEP_ASK_MAP_REDUCE_CHARS", 9000)
DEEP_ASK_MAP_REDUCE_SECTIONS = _env_int("DEEP_ASK_MAP_REDUCE_SECTIONS", 5)
DEEP_ASK_RERANK = os.getenv("DEEP_ASK_RERANK", "true").lower() == "true"
DEEP_ASK_STUDY_CACHE = os.getenv("DEEP_ASK_STUDY_CACHE", "true").lower() == "true"
MAX_REVISIONS = _env_int("MAX_REVISIONS", 1)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true"
ENABLE_ARXIV = os.getenv("ENABLE_ARXIV", "true").lower() == "true"
# Optional Notion connector (MCP-shaped adapter). Off by default; read env at call time in mcp_client.
ENABLE_MCP = os.getenv("ENABLE_MCP", "false").lower() == "true"
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
WEB_SEARCH_MAX_RESULTS = _env_int("WEB_SEARCH_MAX_RESULTS", 5)
ARXIV_MAX_RESULTS = _env_int("ARXIV_MAX_RESULTS", 3)
HYBRID_FALLBACK_THRESHOLD = _env_int("HYBRID_FALLBACK_THRESHOLD", 2)
RETRIEVAL_HYBRID = os.getenv("RETRIEVAL_HYBRID", "true").lower() == "true"
HYBRID_RRF_K = _env_int("HYBRID_RRF_K", 60)

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}

# Agent layer (Hermes-like memory + goal loops around LangGraph)
AUTO_MEMORY = os.getenv("AUTO_MEMORY", "true").lower() == "true"
AUTO_RECALL = os.getenv("AUTO_RECALL", "true").lower() == "true"
MAX_GOAL_PASSES = max(1, min(4, _env_int("MAX_GOAL_PASSES", 2)))
WATCH_MAX_PASSES = max(1, min(4, _env_int("WATCH_MAX_PASSES", 1)))
MIN_GOAL_CONFIDENCE = float(os.getenv("MIN_GOAL_CONFIDENCE", "0.65") or "0.65")
AGENT_MODE_DEFAULT = os.getenv("AGENT_MODE_DEFAULT", "goal").strip().lower()
PLAN_REVIEW_DEFAULT = os.getenv("PLAN_REVIEW_DEFAULT", "true").lower() == "true"

# Daily autonomous review (in-app scheduler)
DAILY_REVIEW_ENABLED = os.getenv("DAILY_REVIEW_ENABLED", "true").lower() == "true"
DAILY_REVIEW_HOUR = max(0, min(23, _env_int("DAILY_REVIEW_HOUR", 9)))
DAILY_REVIEW_MAX_GOALS = max(1, min(5, _env_int("DAILY_REVIEW_MAX_GOALS", 2)))
# Auto catch-up only after the scheduled hour (avoids surprise LLM spend on early launches)
DAILY_REVIEW_CATCH_UP = os.getenv("DAILY_REVIEW_CATCH_UP", "true").lower() == "true"
DIGEST_STATE_PATH = Path(
    os.getenv("DIGEST_STATE_PATH", str(DATA_ROOT / "data" / "digest_state.json"))
)

# Ablation: when false, verifier still runs once but never loops back to analyst
ENABLE_SELF_CRITIQUE = os.getenv("ENABLE_SELF_CRITIQUE", "true").lower() == "true"

ENV_FILE_PATH = DATA_ROOT / ".env"
