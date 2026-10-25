import pytest
import redis

import config
from src.llm import rate_limiter


class FakeRedis:
    def __init__(self):
        self.counts: dict[str, int] = {}
        self.expiry: dict[str, int] = {}

    def incr(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    def expire(self, key, ttl):
        self.expiry[key] = ttl


class DownRedis:
    def incr(self, key):
        raise redis.ConnectionError("down")


@pytest.fixture
def fake(monkeypatch):
    client = FakeRedis()
    monkeypatch.setattr(rate_limiter, "get_redis_client", lambda: client)
    return client


def test_calls_up_to_the_limit_are_allowed(fake):
    limit = config.RATE_LIMIT_PER_MINUTE["openrouter"]
    results = [rate_limiter.is_rate_limited("k", "openrouter") for _ in range(limit)]
    assert not any(results)


def test_call_over_the_limit_is_blocked(fake):
    limit = config.RATE_LIMIT_PER_MINUTE["openrouter"]
    for _ in range(limit):
        rate_limiter.is_rate_limited("k", "openrouter")
    assert rate_limiter.is_rate_limited("k", "openrouter") is True


def test_limits_are_per_key_and_per_provider(fake):
    limit = config.RATE_LIMIT_PER_MINUTE["openrouter"]
    for _ in range(limit + 1):
        rate_limiter.is_rate_limited("k1", "openrouter")
    assert rate_limiter.is_rate_limited("k2", "openrouter") is False
    assert rate_limiter.is_rate_limited("k1", "groq") is False


def test_ttl_is_set_once_on_the_first_hit(fake):
    rate_limiter.is_rate_limited("k", "groq")
    rate_limiter.is_rate_limited("k", "groq")
    assert list(fake.expiry.values()) == [config.RATE_LIMIT_TTL_SECONDS]


def test_provider_without_a_configured_limit_is_never_limited(fake):
    assert not any(rate_limiter.is_rate_limited("k", "ollama") for _ in range(500))


def test_redis_outage_fails_open(monkeypatch):
    monkeypatch.setattr(rate_limiter, "get_redis_client", lambda: DownRedis())
    assert rate_limiter.is_rate_limited("k", "groq") is False
