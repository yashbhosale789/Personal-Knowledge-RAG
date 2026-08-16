import asyncio
import logging
import random
import time
from typing import Callable, List, Optional, Any
from api.core.exceptions import ProviderError

logger = logging.getLogger(__name__)

PROVIDER_FALLBACK_ORDER = ["groq", "openrouter", "gemini"]


async def call_with_retry(
    fn: Callable,
    provider: str,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 8.0,
) -> Any:
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None, lambda: fn(provider)
            )
        except Exception as e:
            last_exception = e
            if attempt == max_retries:
                break

            delay = min(base_delay * (2**attempt), max_delay)
            jitter = delay * random.uniform(-0.2, 0.2)
            sleep_time = max(0, delay + jitter)

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
) -> tuple[Any, str]:
    providers_to_try: List[str] = []

    if preferred_provider and preferred_provider in PROVIDER_FALLBACK_ORDER:
        providers_to_try.append(preferred_provider)
        providers_to_try.extend(
            p for p in PROVIDER_FALLBACK_ORDER if p != preferred_provider
        )
    else:
        providers_to_try = list(PROVIDER_FALLBACK_ORDER)

    last_error = None
    for provider in providers_to_try:
        try:
            result = await call_with_retry(fn, provider, max_retries=max_retries)
            return result, provider
        except ProviderError as e:
            logger.error("Provider %s exhausted retries: %s", provider, e.message)
            last_error = e
            continue

    raise ProviderError(
        message=f"All provieders failed. Last error: {last_error}",
        provider="all",
        retries_exhausted=True,
    )
