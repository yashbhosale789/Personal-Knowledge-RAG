import asyncio
import logging
import random
import time
import requests

from typing import Callable, List, Optional, Any
from api.core.exceptions import ProviderError
from src.llm.rate_limiter import is_rate_limited
from api.core.metrics import (
    provider_call_duration_seconds,
    provider_call_errors_total,
    provider_requests_total,
    provider_retries_total,
)

logger = logging.getLogger(__name__)

PROVIDER_FALLBACK_ORDER = ["groq", "openrouter", "gemini"]
ALL_KNOWN_PROVIDERS = PROVIDER_FALLBACK_ORDER + ["ollama"]


async def call_with_retry(
    fn: Callable,
    provider: str,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 8.0,
) -> Any:
    last_exception = None

    for attempt in range(max_retries + 1):
        attempt_start = time.monotonic()
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: fn(provider)
            )

            provider_call_duration_seconds.labels(provider=provider).observe(
                time.monotonic() - attempt_start
            )

            return result

        except Exception as e:

            provider_call_errors_total.labels(provider=provider).inc()

            last_exception = e

            is_rate_limited = (
                isinstance(e, requests.exceptions.HTTPError)
                and e.response is not None
                and e.response.status_code == 429
            )

            if is_rate_limited:
                logger.warning(
                    f"Provider {provider} rate limited (429) - skipping retries, falling back."
                )
                break

            if attempt == max_retries:
                break

            delay = min(base_delay * (2**attempt), max_delay)
            jitter = delay * random.uniform(-0.2, 0.2)
            sleep_time = max(0, delay + jitter)

            provider_retries_total.labels(provider=provider).inc()
            logger.warning(
                "Attempt %d/%d failed for provider %s: %s. Retrying in %.2fs.",
                attempt + 1,
                max_retries + 1,
                provider,
                str(e),
                sleep_time,
            )
            await asyncio.sleep(sleep_time)

    raise ProviderError(
        message=f"Provider {provider} failed after {max_retries + 1} attempts: {last_exception}",
        provider=provider,
        retries_exhausted=True,
    )


async def call_with_fallback(
    fn: Callable,
    preferred_provider: Optional[str] = None,
    max_retries: int = 3,
    api_key_hash: Optional[str] = None,
) -> tuple[Any, str]:
    if preferred_provider == "ollama":
        # Explicit-only: never auto-selected, never falls back to it.
        result = await call_with_retry(fn, "ollama", max_retries=max_retries)
        provider_requests_total.labels(provider="ollama", outcome="success").inc()
        return result, "ollama"

    providers_to_try: List[str] = []
    if preferred_provider:
        if preferred_provider not in PROVIDER_FALLBACK_ORDER:
            raise ProviderError(
                message=f"Unknown provider '{preferred_provider}'. Choose: {', '.join(ALL_KNOWN_PROVIDERS)}",
                provider=preferred_provider,
                retries_exhausted=False,
            )
        providers_to_try.append(preferred_provider)
        providers_to_try.extend(
            p for p in PROVIDER_FALLBACK_ORDER if p != preferred_provider
        )
    else:
        providers_to_try = list(PROVIDER_FALLBACK_ORDER)

    last_error = None
    for provider in providers_to_try:
        if api_key_hash and is_rate_limited(api_key_hash, provider):
            provider_requests_total.labels(
                provider=provider, outcome="rate_limited"
            ).inc()
            logger.warning("Provider %s rate-limited for this key, skipping", provider)
            last_error = ProviderError(
                message="rate limited", provider=provider, retries_exhausted=False
            )
            continue

        try:
            result = await call_with_retry(fn, provider, max_retries=max_retries)
            provider_requests_total.labels(provider=provider, outcome="success").inc()
            return result, provider
        except ProviderError as e:
            provider_requests_total.labels(provider=provider, outcome="exhausted").inc()
            logger.error("Provider %s exhausted retries: %s", provider, e.message)
            last_error = e
            continue

    raise ProviderError(
        message=f"All providers failed. Last error: {last_error}",
        provider="all",
        retries_exhausted=True,
    )
