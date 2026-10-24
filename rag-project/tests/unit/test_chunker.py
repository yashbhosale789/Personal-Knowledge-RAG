from langchain_core.documents import Document

import config
from src.ingestion.chunker import chunk_documents


def _doc(text: str, source: str) -> Document:
    return Document(page_content=text, metadata={"source": source, "page": 0})


def test_short_document_is_a_single_chunk():
    chunks = chunk_documents([_doc("Tighten the lug nuts.", "a.pdf")])
    assert [c.page_content for c in chunks] == ["Tighten the lug nuts."]


def test_chunks_respect_size_limit():
    text = " ".join(f"word{i}" for i in range(600))
    chunks = chunk_documents([_doc(text, "a.pdf")])
    assert len(chunks) > 1
    assert all(len(c.page_content) <= config.CHUNK_SIZE for c in chunks)


def test_chunk_index_counts_per_source_from_one():
    long_text = " ".join(f"word{i}" for i in range(600))
    chunks = chunk_documents([_doc(long_text, "a.pdf"), _doc("short", "b.pdf")])
    a = [c.metadata["chunk_index"] for c in chunks if c.metadata["source"] == "a.pdf"]
    b = [c.metadata["chunk_index"] for c in chunks if c.metadata["source"] == "b.pdf"]
    assert a == list(range(1, len(a) + 1))
    assert b == [1]


def test_parent_metadata_is_carried_forward():
    chunks = chunk_documents([_doc("hello", "a.pdf")])
    assert chunks[0].metadata["page"] == 0
    assert chunks[0].metadata["source"] == "a.pdf"


def test_empty_input_gives_no_chunks():
    assert chunk_documents([]) == []
