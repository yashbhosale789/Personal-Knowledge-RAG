"""Shared fixtures. Default run: $0, no network, no model downloads."""

import hashlib
import math
import re

import pytest

import config

TEST_API_KEY = "test-key-0123456789-abcdefghij"
EMBED_DIM = config.EMBEDDING_DIAMENSION


def fake_embed(text: str) -> list[float]:
    """Deterministic hashed bag-of-words vector, unit length; similar texts score high."""
    vec = [0.0] * EMBED_DIM
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        idx = int(hashlib.md5(token.encode(), usedforsecurity=False).hexdigest(), 16)
        vec[idx % EMBED_DIM] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class FakeEmbeddingModel:
    """Stands in for SentenceTransformer where code calls model.encode(...)."""

    def encode(self, text, **_):
        import numpy as np

        return np.array(fake_embed(text), dtype="float32")


class FakeReranker:
    """Orders candidates by query-term overlap; no model."""

    def rerank(self, query, candidates, text_key="text"):
        terms = set(query.lower().split())
        scored = [
            {**c, "ce_score": float(len(terms & set(c[text_key].lower().split())))}
            for c in candidates
        ]
        scored.sort(key=lambda c: c["ce_score"], reverse=True)
        for rank, c in enumerate(scored):
            c["ce_rank"] = rank
        return scored[: config.TOP_K]


@pytest.fixture(autouse=True)
def no_langfuse(monkeypatch):
    """No test sends traces: the app loads .env, which may hold real Langfuse keys.
    tests/api/test_tracing.py installs an in-memory client where it needs one."""
    from src import tracing

    monkeypatch.setattr(tracing, "_client", None)
    monkeypatch.setattr(tracing, "_initialised", True)


@pytest.fixture
def api_key(monkeypatch):
    monkeypatch.setenv(config.API_KEY, TEST_API_KEY)
    return TEST_API_KEY


@pytest.fixture
def auth_headers(api_key):
    return {"Authorization": f"Bearer {api_key}"}


@pytest.fixture
def fake_embeddings(monkeypatch):
    """Replaces the real embedder in every module that would load it."""
    from src.embedding import embedder

    monkeypatch.setattr(
        embedder, "embed_texts", lambda texts: [fake_embed(t) for t in texts]
    )
    monkeypatch.setattr(embedder, "embed_query", fake_embed)
    monkeypatch.setattr(embedder, "get_embedding_model", lambda: FakeEmbeddingModel())
    return FakeEmbeddingModel()
