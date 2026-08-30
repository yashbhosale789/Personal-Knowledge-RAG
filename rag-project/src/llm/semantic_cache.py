from redis.commands.search.field import VectrorField, TextField
from redis.commands.search.index_definition import IndexDefinition, IndexType

from src.llm.redis_client import get_redis_client
from config import EMBEDDING_DIAMENSION, CACHE_INDEX_NAME, CACHE_KEY_PREFIX

def create_cache_index() -> None:
    try:
        return None

    except Exception as e:
        return e