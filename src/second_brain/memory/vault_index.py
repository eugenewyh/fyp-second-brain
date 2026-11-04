"""Heal an empty Chroma index when vault files still exist on disk."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from second_brain.config import DOCUMENTS_DIR, SUPPORTED_EXTENSIONS
from second_brain.ingestion.pipeline import ingest_directory
from second_brain.memory.chroma_store import collection_count

logger = logging.getLogger(__name__)

_heal_lock = threading.Lock()


def vault_has_ingestible_files(root: Path | None = None) -> bool:
    base = Path(root) if root is not None else Path(DOCUMENTS_DIR)
    if not base.is_dir():
        return False
    for path in base.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            return True
    return False


def ensure_vault_indexed(root: Path | None = None) -> int:
    """Return collection size, re-ingesting the vault when the index is empty."""
    count = collection_count()
    if count > 0:
        return count
    base = Path(root) if root is not None else Path(DOCUMENTS_DIR)
    if not vault_has_ingestible_files(base):
        return 0
    with _heal_lock:
        count = collection_count()
        if count > 0:
            return count
        logger.warning(
            "Search index empty but vault files exist under %s — re-indexing",
            base,
        )
        ingest_directory(base)
        return collection_count()
