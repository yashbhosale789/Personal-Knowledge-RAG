from datetime import datetime, timezone
from src.llm.redis_client import get_redis_client

from config import RATE_LIMIT_PER_MINUTE, RATE_LIMIT_TTL_SECONDS


def is_rate_limited(api_key_hash: str, provider: str) -> bool:
    client = get_redis_client()
    window = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    key = f"ratelimit:{api_key_hash}:{provider}:{window}"

    count = client.incr(key)
    if count == 1:
        client.expire(key, RATE_LIMIT_TTL_SECONDS)

    limit = RATE_LIMIT_PER_MINUTE.get(provider)
    if limit is None:
        return False  # unknown provider (e.g. ollama) — not rate-limited

    return count > limit