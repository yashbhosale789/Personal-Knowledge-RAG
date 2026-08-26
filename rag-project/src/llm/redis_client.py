import redis
import logging

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None

def get_redis_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis(host="localhost", port=6379, decode_responses=True)
        logger.info("Redis client initialized")

    return _client
