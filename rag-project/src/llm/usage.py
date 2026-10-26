"""
Per-stage LLM token and latency accounting.

Every successful call_llm records its tokens and duration to Prometheus. Token counts
come from the provider's usage block when present ("reported"); any count the provider
omits is approximated from text length ("estimated"). Under the $0 budget, "cost" is
free-tier quota consumption: tokens and calls per provider/model, not money.

A caller that wants the calls of one unit of work (one /query, one eval item) wraps it
in track(); the pipeline runs synchronously in one thread, so a ContextVar is enough.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from prometheus_client import Counter, Histogram

LLM_LATENCY_BUCKETS = (0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 30)

llm_tokens_total = Counter(
    "llm_tokens_total",
    "LLM tokens by pipeline stage; source=reported (provider usage) or estimated.",
    ["stage", "provider", "model", "type", "source"],
)

llm_call_duration_seconds = Histogram(
    "llm_call_duration_seconds",
    "Latency of a single successful LLM call, by pipeline stage.",
    ["stage", "provider", "model"],
    buckets=LLM_LATENCY_BUCKETS,
)

_calls: ContextVar[list[dict] | None] = ContextVar("llm_calls", default=None)


def estimate_tokens(text: str) -> int:
    """~4 characters per token for English text; only used when the provider is silent."""
    return max(1, len(text) // 4) if text else 0


def record(
    stage: str,
    provider: str,
    model: str,
    seconds: float,
    reported: dict,
    prompt_text: str,
    completion_text: str,
) -> dict:
    """reported holds whichever of prompt_tokens / completion_tokens the provider gave."""
    call = {
        "stage": stage,
        "provider": provider,
        "model": model,
        "ms": round(seconds * 1000),
    }
    for kind, text in (("prompt", prompt_text), ("completion", completion_text)):
        count = reported.get(f"{kind}_tokens")
        source = "reported" if isinstance(count, int) else "estimated"
        if source == "estimated":
            count = estimate_tokens(text)
        call[f"{kind}_tokens"] = count
        call[f"{kind}_source"] = source
        llm_tokens_total.labels(stage, provider, model, kind, source).inc(count)

    llm_call_duration_seconds.labels(stage, provider, model).observe(seconds)

    calls = _calls.get()
    if calls is not None:
        calls.append(call)
    return call


@contextmanager
def track() -> Iterator[list[dict]]:
    """Collects every call_llm made inside the block, in order."""
    calls: list[dict] = []
    token = _calls.set(calls)
    try:
        yield calls
    finally:
        _calls.reset(token)


def summarize(calls: list[dict]) -> dict:
    """Per-query view for logs and eval records."""
    return {
        "calls": calls,
        "prompt_tokens": sum(c["prompt_tokens"] for c in calls),
        "completion_tokens": sum(c["completion_tokens"] for c in calls),
        "llm_ms": sum(c["ms"] for c in calls),
        "estimated": any(
            c["prompt_source"] == "estimated" or c["completion_source"] == "estimated"
            for c in calls
        ),
    }
