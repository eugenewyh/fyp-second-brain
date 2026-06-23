import logging
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document

from second_brain.config import SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)


def load_file(file_path: Path) -> list[Document]:
    suffix = file_path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        logger.warning("Skipping unsupported file: %s", file_path.name)
        return []

    if suffix == ".pdf":
        loader = PyPDFLoader(str(file_path))
    else:
        loader = TextLoader(str(file_path), encoding="utf-8")

    docs = loader.load()
    for doc in docs:
        doc.metadata["source"] = file_path.name
        doc.metadata["source_path"] = str(file_path.resolve())

    logger.info("Loaded %d page(s) from %s", len(docs), file_path.name)
    return docs


def load_directory(directory: Path) -> list[Document]:
    if not directory.is_dir():
        raise FileNotFoundError(f"Directory not found: {directory}")

    all_docs: list[Document] = []
    files = sorted(
        f for f in directory.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    if not files:
        logger.warning("No supported documents found in %s", directory)
        return []

    for file_path in files:
        all_docs.extend(load_file(file_path))

    logger.info("Loaded %d document(s) from %d file(s)", len(all_docs), len(files))
    return all_docs