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

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}