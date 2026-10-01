import logging
import os

import redis

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None
_binary_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=6379,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        logger.info("Redis client initialized")
    return _client


def get_redis_binary_client() -> redis.Redis:
    global _binary_client
    if _binary_client is None:
        _binary_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=6379,
            decode_responses=False,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        logger.info("Redis binary client initialized")
    return _binary_client
