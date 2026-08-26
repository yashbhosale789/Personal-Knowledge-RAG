from datetime import datetime, timezone
from src.llm.redis_client import get_redis_client

RATE_LIMIT_PER_MINUTE = 20
RATE_LIMIT_TTL_SECONDS = 120


def is_rate_limited(api_key_hash: str, provider: str) -> bool:
    client = get_redis_client()
    window = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    key = f"ratelimit:{api_key_hash}:{provider}:{window}"

    count = client.incr(key)
    if count == 1:
        client.expire(key, RATE_LIMIT_TTL_SECONDS)

    return count > RATE_LIMIT_PER_MINUTE