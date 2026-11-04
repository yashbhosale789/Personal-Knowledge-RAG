import logging
import re
import unicodedata
from pathlib import Path

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredMarkdownLoader,
    UnstructuredWordDocumentLoader,
)
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

LOADER_MAP = {
    ".pdf": PyPDFLoader,
    ".txt": TextLoader,
    ".md": UnstructuredMarkdownLoader,
    ".docx": UnstructuredWordDocumentLoader,
}


_LIGATURE = re.compile("[\ufb00-\ufb06]")
# A capital kerned away from its word ("V elvera", "F eatures": 31% of c2 chunks, 15.1).
# Not A/I (words) or X (a car trim), nor after a letter, digit, "-" or "&" ("3D", "R&D", "USB-C").
# shortcut: still joins a real lone letter before a word ("R and", "grade B or", "RA W capture",
# ~3 in c2); upgrade to a vocabulary check if a corpus has many.
_SPLIT_CAPITAL = re.compile(r"(?<![\w&-])([B-HJ-WYZ]) (?=[a-z]{2})")


def clean_text(text: str) -> str:
    """Undo PDF extraction artifacts that break keyword matching; nothing else changes."""
    text = _LIGATURE.sub(lambda m: unicodedata.normalize("NFKC", m.group()), text)
    text = text.replace("\uffff", "\u2022")  # c2 bullets extract as U+FFFF; c1's are "•"
    return _SPLIT_CAPITAL.sub(r"\1", text)


def load_documents(file_path: Path) -> list[Document]:
    """
    Load a single file into a list of Documents.

    Each loader may return multiple documents - PDF's return one per page,
    text files typically return one for the whole file.
    """

    suffix = file_path.suffix.lower()
    loader_cls = LOADER_MAP.get(suffix)

    if not loader_cls:
        logger.warning(f"Unsupported file type : {file_path.name}. Skipping file.")
        return []

    try:
        loader = loader_cls(str(file_path))
        docs = loader.load()

        for doc in docs:
            doc.page_content = clean_text(doc.page_content)
            doc.metadata["source"] = str(file_path)
            doc.metadata["filename"] = str(file_path)

        logger.info(f"Loaded {len(docs)} document(s) from {file_path.name}")
        return docs

    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to load {file_path.name} : {e}")
        return []


def load_directory(directory: Path) -> list[Document]:
    """
    Recursively load all supported files from a directory.
    """
    all_docs: list[Document] = []

    files = [
        f
        for f in directory.rglob("*")
        if f.is_file() and f.suffix.lower() in LOADER_MAP
    ]

    if not files:
        logger.warning(f"No supported files found in directory: {directory}")
        return []

    for file_path in files:
        docs = load_documents(file_path)
        all_docs.extend(docs)

    logger.info(f"Total documents loaded: {len(all_docs)} from {len(files)} file(s)")
    return all_docs
