from redis.commands.search.field import VectorField, TextField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query

from src.llm.redis_client import get_redis_client
from config import (
    EMBEDDING_DIAMENSION,
    CACHE_INDEX_NAME,
    CACHE_KEY_PREFIX,
    CACHE_TTL_SECONDS,
)

import hashlib
from src.embedding.embedder import get_embedding_model


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


def store_cache_entry(query: str, answer: str, provider: str) -> None:
    client = get_redis_client()

    model = get_embedding_model()
    embedding = model.encode(query)

    key_hash = hashlib.sha256(query.encode()).hexdigest()
    key = f"{CACHE_KEY_PREFIX}{key_hash}"

    client.hset(
        key,
        mapping={
            "embedding": embedding.astype("float32").tobytes(),
            "query_text": query,
            "answer_text": answer,
            "provider": provider,
        },
    )

    client.expire(key, CACHE_TTL_SECONDS)


def find_cached_answer(query: str) -> dict | None:
    client = get_redis_client()
    model = get_embedding_model()
    embedding = model.encode(query)

    knn_query = (
        Query("*=>[KNN 1 @embedding $vec AS score]")
        .sort_by("score")
        .return_field("query", "answer", "provider", "score")
        .dialect(2)
    )

    results = client.ft(CACHE_INDEX_NAME).search(
        knn_query, query_params={"vec": embedding.astype("float32").tobytes()}
    )


if __name__ == "__main__":
    create_cache_index()
    print("index created")

    store_cache_entry(
        "Where is the spare tyre in a Sedan?",
        "Under the boot floor in the trunk.",
        "groq",
    )
    print("cache entry stored")


# Run the follwing:

# ----- create_cache_index() -----
# python -c "from src.llm.semantic_cache import create_cache_index; create_cache_index(); print('index created')"
# docker docker exec -it redis-stack redis-cli
# FT._LIST


# ----- store_cache_entry() -----
# python -c "
# from src.llm.semantic_cache import store_cache_entry
# store_cache_entry('Where is the spare tyre in a Sedan?', 'Under the boot floor in the trunk.', 'groq')
# print('stored')
# "
