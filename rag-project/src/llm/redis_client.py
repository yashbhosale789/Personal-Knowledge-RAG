import redis_client
import logging

logger = logging.getLogger(__name__)

_client = redis_client.Redis | None = None

def get_redis_client() -> redis_client.Redis:
    global _client
    if _client is None:
        _client = redis_client.Redis(host="localhost", port=6379, decode_responses=True)
        logger.info("Redis client initialized")

    return _client