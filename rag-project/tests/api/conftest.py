import pytest
from fastapi.testclient import TestClient

from api.core import retry
from api.main import app
from api.routers import health
from api.routers import query as query_router


def pipeline_result(**over) -> dict:
    result = {
        "answer": "Use the lug wrench [SOURCE 1].",
        "sources": ["manual.pdf"],
        "chunks_used": 3,
        "query": "q",
        "rewritten_query": "lug wrench",
        "sufficiency": {"sufficient": True, "reason": "has it", "tier": "llm_judge"},
        "citation_check": {
            "grounded": True,
            "unsupported_claims": [],
            "reason": "ok",
            "tier": "llm_judge",
        },
        "confidence": "high",
        "outcome": "answer",
    }
    result.update(over)
    return result


class Recorder:
    """Records what the endpoint handed to the faked pipeline and cache."""

    def __init__(self):
        self.pipeline_calls: list[dict] = []
        self.cache_writes: list[tuple] = []
        self.embeddings: list[str] = []
        self.result = pipeline_result()
        self.cached = None
        self.error: Exception | None = None

    def embed(self, query: str) -> bytes:
        self.embeddings.append(query)
        return f"emb:{query}".encode()


@pytest.fixture
def fakes(monkeypatch):
    rec = Recorder()

    def fake_pipeline(query, provider, return_contexts):
        rec.pipeline_calls.append(
            {"query": query, "provider": provider, "return_contexts": return_contexts}
        )
        if rec.error:
            raise rec.error
        return rec.result

    monkeypatch.setattr(query_router, "_run_pipeline", fake_pipeline)
    monkeypatch.setattr(query_router, "cache_embedding", lambda q: rec.embed(q))
    monkeypatch.setattr(
        query_router, "find_cached_answer", lambda q, provider, emb: rec.cached
    )
    monkeypatch.setattr(
        query_router, "store_cache_entry", lambda *args: rec.cache_writes.append(args)
    )
    monkeypatch.setattr(retry, "is_rate_limited", lambda key, provider: False)
    return rec


@pytest.fixture
def ready():
    health.set_pipeline_ready(True)
    yield
    health.set_pipeline_ready(False)


@pytest.fixture
def client(api_key):
    # No `with`: skips the lifespan, which would load real models.
    return TestClient(app)
