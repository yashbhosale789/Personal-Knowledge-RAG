"""The one ingest path (Phase 15.0, F-03): used by POST /ingest and scripts/ingest.py."""

import logging
from pathlib import Path

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class IngestRejected(Exception):
    """The document was refused (no text, or flagged by the injection scanner).
    The message is safe to show to the API caller."""


def ingest_file(
    path: Path | str, *, notify: bool = True, max_chars: int | None = None
) -> list[Document]:
    """
    Scan, replace and index one file: injection scan -> delete_by_source -> chunk ->
    add_chunks -> index_changed(). Returns the chunks stored. Raises IngestRejected
    for a refused document; anything else propagates.

    notify=False is for batch callers, which must call index_changed() once at the
    end (one cache clear per run, not per file: an unreachable Redis costs seconds).
    max_chars caps the extracted text (uploads); the check runs before anything is deleted.
    """
    from src.ingestion import loader
    from src.ingestion.chunker import chunk_documents
    from src.pipeline.injection_scanner import scan_for_injection
    from src.vectorstore.store import add_chunks, delete_by_source

    # One canonical `source` string, whichever caller and spelling (F-03).
    resolved_path = Path(path).resolve()
    docs = loader.load_documents(resolved_path)

    if not docs:
        raise IngestRejected(
            "No content could be extracted from this document. It may be corrupted or empty."
        )

    full_text = "\n".join(doc.page_content for doc in docs)
    if max_chars is not None and len(full_text) > max_chars:
        raise IngestRejected(
            f"Document too long: {len(full_text):,} characters of text; the limit is {max_chars:,}."
        )

    scan_result = scan_for_injection(full_text)

    if scan_result["flagged"]:
        logger.warning(
            f"Ingest blocked after {resolved_path} - injection patterns detected: {scan_result['categories']}"
        )
        raise IngestRejected(
            f"Document rejected: possible prompt injection detected ({','.join(scan_result['categories'])})"
        )

    delete_by_source(str(resolved_path))
    chunks = chunk_documents(docs)
    add_chunks(chunks)
    if notify:
        index_changed()
    return chunks


def index_changed() -> None:
    """Call after every write to Chroma: drop cached answers and the BM25 index."""
    from src.llm import semantic_cache
    from src.pipeline.advanced_rag import reset_bm25

    try:
        cleared_count = semantic_cache.clear_cache()
        logger.info(f"Cleared {cleared_count} cache entries after index change.")

    except Exception as e:  # noqa: BLE001
        logger.warning(f"Cache clear failed after index change (non-fatal): {e}")

    reset_bm25()
