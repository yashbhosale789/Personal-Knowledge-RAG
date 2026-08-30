from redis.commands.search.field import VectorField, TextField
from redis.commands.search.index_definition import IndexDefinition, IndexType

from src.llm.redis_client import get_redis_client
from config import EMBEDDING_DIAMENSION, CACHE_INDEX_NAME, CACHE_KEY_PREFIX


def create_cache_index() -> None:
    client = get_redis_client()
    try:
        client.ft(CACHE_INDEX_NAME).info()
        return
    except Exception:
        client.ft(CACHE_INDEX_NAME).create_index(
            fields=[
                VectorField(
                    "embedding",
                    "FLAT",
                    {
                        "TYPE": "FLOAT32",
                        "DIM": EMBEDDING_DIAMENSION,
                        "DISTANCE_METRIC": "COSINE",
                    },
                ),
                TextField("query_text"),
                TextField("answer_text"),
                TextField("provider"),
            ],
            definition=IndexDefinition(
                prefix=[CACHE_KEY_PREFIX], index_type=IndexType.HASH
            ),
        )