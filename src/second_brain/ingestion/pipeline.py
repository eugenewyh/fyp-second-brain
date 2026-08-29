import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from second_brain.config import CHUNK_OVERLAP, CHUNK_SIZE
from second_brain.ingestion.loaders import load_directory, load_file
from second_brain.ingestion.sections import ensure_section_summaries, infer_project_from_source
from second_brain.memory.chroma_store import upsert_documents

logger = logging.getLogger(__name__)


def _source_hash(source_path: str) -> str:
    return hashlib.md5(source_path.encode()).hexdigest()[:12]


def split_documents(documents: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(documents)

    ingested_at = datetime.now(timezone.utc).isoformat()
    for i, chunk in enumerate(chunks):
        source_path = chunk.metadata.get("source_path", "")
        chunk.metadata["chunk_index"] = i
        chunk.metadata["ingested_at"] = ingested_at
        chunk.metadata["source_hash"] = _source_hash(source_path)

    logger.info("Split into %d chunk(s)", len(chunks))
    return chunks


def ingest_directory(directory: Path) -> int:
    documents = load_directory(directory)
    if not documents:
        return 0

    chunks = split_documents(documents)
    count = upsert_documents(chunks)
    logger.info("Ingested %d chunk(s) into Chroma", count)
    return count


def ingest_file(file_path: Path) -> int:
    documents = load_file(file_path)
    if not documents:
        return 0

    try:
        project = infer_project_from_source(file_path)
        ensure_section_summaries(file_path, project_path=project)
    except Exception:
        logger.debug("Section summaries skipped for %s", file_path, exc_info=True)

    chunks = split_documents(documents)
    count = upsert_documents(chunks)
    logger.info("Ingested %d chunk(s) from %s", count, file_path.name)
    return count