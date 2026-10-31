import pytest

from src.retrieval.bm25_retriever import BM25Retriever

CHUNKS = [
    {"text": "jack the car under the jacking point", "metadata": {"filename": "a.pdf"}},
    {"text": "tighten lug nuts in a star pattern", "metadata": {"filename": "a.pdf"}},
    {"text": "check tyre pressure monthly", "metadata": {"filename": "b.pdf"}},
]


@pytest.fixture
def retriever():
    return BM25Retriever(chunks=CHUNKS)


def test_best_keyword_match_ranks_first(retriever):
    results = retriever.retrieve("lug nuts star", top_k=3)
    assert results[0]["text"] == CHUNKS[1]["text"]
    assert results[0]["rank"] == 0


def test_result_shape_and_top_k(retriever):
    results = retriever.retrieve("tyre", top_k=2)
    assert len(results) == 2
    assert set(results[0]) == {"text", "metadata", "score", "rank"}
    assert [r["rank"] for r in results] == [0, 1]


def test_scores_are_descending(retriever):
    scores = [r["score"] for r in retriever.retrieve("tyre pressure monthly", top_k=3)]
    assert scores == sorted(scores, reverse=True)


def test_lookup_is_case_insensitive(retriever):
    assert retriever.retrieve("LUG NUTS", top_k=1)[0]["text"] == CHUNKS[1]["text"]


def test_empty_index_returns_nothing_instead_of_crashing():
    # e.g. the last document was deleted; BM25Okapi([]) would divide by zero
    assert BM25Retriever(chunks=[]).retrieve("anything") == []


def test_default_builds_from_the_vector_store(monkeypatch):
    monkeypatch.setattr("src.vectorstore.store.all_chunks", lambda: CHUNKS)
    assert BM25Retriever().retrieve("tyre", top_k=1)[0]["text"] == CHUNKS[2]["text"]
