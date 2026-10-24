"""Smoke test with the real embedder and reranker. Downloads models on first run.

Run manually or on a schedule:  python -m pytest -m slow
"""

import math

import pytest

pytestmark = pytest.mark.slow


def test_embedder_returns_normalised_vectors_of_the_configured_dimension():
    import config
    from src.embedding.embedder import embed_query, embed_texts

    docs = embed_texts(["Tighten the lug nuts in a star pattern."])
    query = embed_query("how do I tighten lug nuts")
    assert len(docs[0]) == len(query) == config.EMBEDDING_DIAMENSION
    assert math.isclose(sum(v * v for v in docs[0]), 1.0, rel_tol=1e-3)


def test_embedder_places_related_text_closer_than_unrelated_text():
    from src.embedding.embedder import embed_query, embed_texts

    related, unrelated = embed_texts(
        [
            "Use the lug wrench to tighten the lug nuts.",
            "The capital of France is Paris.",
        ]
    )
    query = embed_query("how do I tighten lug nuts")

    def dot(a, b):
        return sum(x * y for x, y in zip(a, b))

    assert dot(query, related) > dot(query, unrelated)


def test_reranker_puts_the_relevant_passage_first():
    from src.retrieval.reranker import CrossEncoderReranker

    candidates = [
        {"text": "The capital of France is Paris."},
        {"text": "Use the lug wrench to tighten the lug nuts in a star pattern."},
    ]
    ranked = CrossEncoderReranker().rerank("how do I tighten lug nuts", candidates)
    assert "lug wrench" in ranked[0]["text"]
    assert ranked[0]["ce_score"] > ranked[1]["ce_score"]
    assert [r["ce_rank"] for r in ranked] == [0, 1]
