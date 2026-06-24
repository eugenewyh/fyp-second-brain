import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2:3b")
CHROMA_PATH = Path(os.getenv("CHROMA_PATH", PROJECT_ROOT / "data" / "chroma"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "personal_knowledge")
DOCUMENTS_DIR = PROJECT_ROOT / "data" / "documents"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))
RETRIEVAL_TOP_K_PER_QUERY = int(os.getenv("RETRIEVAL_TOP_K_PER_QUERY", "5"))
MAX_REVISIONS = int(os.getenv("MAX_REVISIONS", "2"))

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true"
ENABLE_ARXIV = os.getenv("ENABLE_ARXIV", "true").lower() == "true"
WEB_SEARCH_MAX_RESULTS = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "5"))
ARXIV_MAX_RESULTS = int(os.getenv("ARXIV_MAX_RESULTS", "3"))
HYBRID_FALLBACK_THRESHOLD = int(os.getenv("HYBRID_FALLBACK_THRESHOLD", "2"))

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}