import uuid

import config
from src.llm.rate_limiter import is_rate_limited


def _key() -> str:
    return f"test-{uuid.uuid4().hex}"


def test_limit_is_enforced_against_real_redis(client):
    key = _key()
    limit = config.RATE_LIMIT_PER_MINUTE["openrouter"]
    allowed = [is_rate_limited(key, "openrouter") for _ in range(limit)]
    assert not any(allowed)
    assert is_rate_limited(key, "openrouter") is True


def test_counters_are_isolated_per_key(client):
    a, b = _key(), _key()
    limit = config.RATE_LIMIT_PER_MINUTE["openrouter"]
    for _ in range(limit + 1):
        is_rate_limited(a, "openrouter")
    assert is_rate_limited(b, "openrouter") is False


def test_counter_key_gets_a_ttl(client):
    key = _key()
    is_rate_limited(key, "groq")
    (redis_key,) = list(client.scan_iter(match=f"ratelimit:{key}:groq:*"))
    assert 0 < client.ttl(redis_key) <= config.RATE_LIMIT_TTL_SECONDS
    client.delete(redis_key)
