import logging

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import CHUNK_MERGE_PAGES, CHUNK_OVERLAP, CHUNK_SIZE

logger = logging.getLogger(__name__)


def _merge_pages(documents: list[Document]) -> list[Document]:
    """One Document per source, pages joined by a blank line; metadata of its first page."""
    merged: dict[str, Document] = {}
    for doc in documents:
        source = doc.metadata.get("source", "unknown")
        if source in merged:
            merged[source].page_content += "\n\n" + doc.page_content
        else:
            merged[source] = Document(
                page_content=doc.page_content, metadata=dict(doc.metadata)
            )
    return list(merged.values())


def chunk_documents(documents: list[Document]) -> list[Document]:
    """
    Split a list of Documents into retrieval-sized chunks.

    Returns a new list of Documents where each item is a chunk,
    carrying forward all metadata from the parent document plus
    a chunk index for ordering/debugging.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,  # character count (not token count)
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    if CHUNK_MERGE_PAGES:  # 15.2 experiment: let chunks cross page breaks
        documents = _merge_pages(documents)
    chunks = splitter.split_documents(documents)

    # Add chunk index per source document for traceability
    source_counters: dict = {}

    for chunk in chunks:
        source = chunk.metadata.get("source", "unknown")
        source_counters[source] = source_counters.get(source, 0) + 1
        chunk.metadata["chunk_index"] = source_counters[source]

    logger.info(f"Created {len(chunks)} chunks from {len(documents)} document(s)")
    return chunks
