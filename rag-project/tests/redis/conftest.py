"""Redis-backed tests. They run against a real redis-stack (CI `services:` container or a local
`docker run -p 6379:6379 redis/redis-stack`), and are skipped when none is reachable."""

import os
import uuid

import pytest
import redis

from src.llm import redis_client


def _reachable() -> bool:
    try:
        client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=6379,
            socket_connect_timeout=1,
        )
        return bool(client.ping())
    except redis.RedisError:
        return False


def pytest_collection_modifyitems(items):
    for item in items:
        if "tests/redis" in item.nodeid.replace("\\", "/"):
            item.add_marker(pytest.mark.redis)


@pytest.fixture(scope="session")
def redis_up():
    if _reachable():
        return
    message = "no redis-stack reachable on REDIS_HOST:6379"
    if os.getenv("CI"):
        pytest.fail(message + " (the CI services container is not up)")
    pytest.skip(message)


@pytest.fixture
def client(redis_up, monkeypatch):
    # Fresh client per test so earlier tests' connection state cannot leak.
    monkeypatch.setattr(redis_client, "_client", None)
    monkeypatch.setattr(redis_client, "_binary_client", None)
    return redis_client.get_redis_client()


@pytest.fixture
def isolated_cache(client, fake_embeddings, monkeypatch):
    """Own index + key prefix, so the test never touches a developer's real cache."""
    from src.llm import semantic_cache as sc

    suffix = uuid.uuid4().hex[:8]
    index, prefix = f"test_idx_{suffix}", f"testcache:{suffix}:"
    monkeypatch.setattr(sc, "CACHE_INDEX_NAME", index)
    monkeypatch.setattr(sc, "CACHE_KEY_PREFIX", prefix)
    monkeypatch.setattr(sc, "get_embedding_model", lambda: fake_embeddings)
    sc.create_cache_index()
    yield sc
    try:
        client.ft(index).dropindex(delete_documents=True)
    except redis.RedisError:
        pass
