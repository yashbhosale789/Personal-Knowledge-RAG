import asyncio

import pytest
import requests

from api.core import retry
from api.core.exceptions import ProviderError
from api.core.metrics import provider_requests_total


@pytest.fixture(autouse=True)
def no_rate_limit_and_no_sleep(monkeypatch):
    monkeypatch.setattr(retry, "is_rate_limited", lambda key, provider: False)

    async def instant(_):
        return None

    monkeypatch.setattr(retry.asyncio, "sleep", instant)


class Provider:
    """Fake LLM call: behaviour per provider name, records attempts."""

    def __init__(self, behaviour: dict):
        self.behaviour = behaviour
        self.calls: list[str] = []

    def __call__(self, provider: str):
        self.calls.append(provider)
        outcome = self.behaviour.get(provider, "ok")
        if isinstance(outcome, Exception):
            raise outcome
        return f"answer-from-{provider}"


def _http_error(status: int) -> requests.exceptions.HTTPError:
    response = requests.Response()
    response.status_code = status
    return requests.exceptions.HTTPError(response=response)


def run(coro):
    return asyncio.run(coro)


def counter(provider: str, outcome: str) -> float:
    return provider_requests_total.labels(
        provider=provider, outcome=outcome
    )._value.get()


def test_preferred_provider_is_used_when_healthy():
    fn = Provider({})
    result, used = run(
        retry.call_with_fallback(fn, preferred_provider="gemini", max_retries=0)
    )
    assert (result, used) == ("answer-from-gemini", "gemini")
    assert fn.calls == ["gemini"]


def test_default_order_when_no_preference():
    fn = Provider({})
    _, used = run(retry.call_with_fallback(fn, max_retries=0))
    assert used == retry.PROVIDER_FALLBACK_ORDER[0]


def test_falls_back_to_next_provider_on_failure():
    fn = Provider({"groq": RuntimeError("boom")})
    result, used = run(
        retry.call_with_fallback(fn, preferred_provider="groq", max_retries=0)
    )
    assert used == "openrouter"
    assert result == "answer-from-openrouter"
    assert fn.calls == ["groq", "openrouter"]


def test_transient_failure_is_retried_on_the_same_provider():
    attempts = {"n": 0}

    def flaky(provider):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise RuntimeError("blip")
        return "ok"

    result, used = run(
        retry.call_with_fallback(flaky, preferred_provider="groq", max_retries=1)
    )
    assert (result, used, attempts["n"]) == ("ok", "groq", 2)


def test_rate_limit_429_skips_retries_and_falls_back():
    fn = Provider({"groq": _http_error(429)})
    _, used = run(
        retry.call_with_fallback(fn, preferred_provider="groq", max_retries=3)
    )
    assert fn.calls.count("groq") == 1
    assert used == "openrouter"


def test_all_providers_failing_raises_provider_error():
    boom = RuntimeError("boom")
    fn = Provider({p: boom for p in retry.PROVIDER_FALLBACK_ORDER})
    with pytest.raises(ProviderError) as exc:
        run(retry.call_with_fallback(fn, max_retries=0))
    assert exc.value.status_code == 502
    assert exc.value.provider == "all"
    assert sorted(fn.calls) == sorted(retry.PROVIDER_FALLBACK_ORDER)


def test_unknown_provider_is_rejected_without_calling_anything():
    fn = Provider({})
    with pytest.raises(ProviderError, match="Unknown provider"):
        run(retry.call_with_fallback(fn, preferred_provider="nonsense"))
    assert fn.calls == []


def test_ollama_is_explicit_only_and_never_falls_back():
    fn = Provider({"ollama": RuntimeError("down")})
    with pytest.raises(ProviderError):
        run(retry.call_with_fallback(fn, preferred_provider="ollama", max_retries=0))
    assert fn.calls == ["ollama"]


def test_rate_limited_provider_is_skipped(monkeypatch):
    monkeypatch.setattr(
        retry, "is_rate_limited", lambda key, provider: provider == "groq"
    )
    fn = Provider({})
    _, used = run(
        retry.call_with_fallback(
            fn, preferred_provider="groq", max_retries=0, api_key_hash="h"
        )
    )
    assert used == "openrouter"
    assert "groq" not in fn.calls


def test_outcome_metrics_are_recorded():
    before_ok = counter("gemini", "success")
    before_bad = counter("groq", "exhausted")
    fn = Provider({"groq": RuntimeError("boom")})
    run(retry.call_with_fallback(fn, preferred_provider="groq", max_retries=0))
    run(
        retry.call_with_fallback(
            Provider({}), preferred_provider="gemini", max_retries=0
        )
    )
    assert counter("groq", "exhausted") == before_bad + 1
    assert counter("gemini", "success") == before_ok + 1
