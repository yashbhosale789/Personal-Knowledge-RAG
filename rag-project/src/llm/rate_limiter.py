import logging

import redis

logger = logging.getLogger(__name__)

from datetime import datetime, timezone

from config import RATE_LIMIT_PER_MINUTE, RATE_LIMIT_TTL_SECONDS
from src.llm.redis_client import get_redis_client


def is_rate_limited(api_key_hash: str, provider: str) -> bool:
    client = get_redis_client()
    window = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    key = f"ratelimit:{api_key_hash}:{provider}:{window}"

    try:
        count = client.incr(key)
        if count == 1:
            client.expire(key, RATE_LIMIT_TTL_SECONDS)
    except redis.RedisError:
        logger.warning("Redis unavailable — rate limiting disabled for this request")
        return False

    limit = RATE_LIMIT_PER_MINUTE.get(provider)
    if limit is None:
        return False

    return count > limit
