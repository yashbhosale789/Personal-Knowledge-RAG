import logging

import redis

logger = logging.getLogger(__name__)

import hashlib

from redis.commands.search.field import TagField, TextField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query

from config import (
    CACHE_INDEX_NAME,
    CACHE_KEY_PREFIX,
    CACHE_SIMILARITY_THRESHOLD,
    CACHE_TTL_SECONDS,
    EMBEDDING_DIAMENSION,
    ENTITY_GROUPS,
    EVAL_PROVIDER,
    PROMPT_VERSION,
)
from src.embedding.embedder import get_embedding_model
from src.llm.client import model_name
from src.llm.redis_client import get_redis_client

# import sys
# from pathlib import Path

# sys.path.insert(0, str(Path(__file__).parent.parent))

# from experiments.semantic_cache_threshold import entity_mismatch


def cache_namespace(provider: str | None = None) -> str:
    """
    Everything that changes the answer for the same query: the prompt set, the answering
    model, and the citation-verifier model (it can append a caveat). Entries are stored
    and looked up within one namespace, so changing any of these misses old entries,
    which then expire by TTL. Hex only, so it is safe inside a TAG query.
    """
    parts = f"{PROMPT_VERSION}|{model_name(provider)}|{model_name(EVAL_PROVIDER)}"
    return hashlib.sha256(parts.encode()).hexdigest()[:16]


def create_cache_index() -> None:
    client = get_redis_client()
    try:
        client.ft(CACHE_INDEX_NAME).info()
        return
    except redis.ResponseError:
        pass  # index genuinely doesn't exist yet — fall through to create it
    except redis.RedisError:
        logger.warning("Redis unavailable — skipping cache index setup")
        return

    try:
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
                TextField("query"),
                TextField("answer"),
                TextField("provider"),
                TagField("namespace"),
            ],
            definition=IndexDefinition(
                prefix=[CACHE_KEY_PREFIX], index_type=IndexType.HASH
            ),
        )
    except redis.RedisError:
        logger.warning("Redis unavailable — cache index creation failed")


def cache_embedding(query: str) -> bytes:
    """
    Raw query, no BGE retrieval prefix: CACHE_SIMILARITY_THRESHOLD was tuned on this
    form, so do not swap in embedder.embed_query. Computed once per request and passed
    to both the lookup and the write.
    """
    return get_embedding_model().encode(query).astype("float32").tobytes()


def store_cache_entry(
    query: str, answer: str, provider: str, embedding: bytes | None = None
) -> None:
    client = get_redis_client()
    if embedding is None:
        embedding = cache_embedding(query)
    namespace = cache_namespace(provider)

    key_hash = hashlib.sha256(f"{namespace}|{query}".encode()).hexdigest()
    key = f"{CACHE_KEY_PREFIX}{key_hash}"

    try:
        client.hset(
            # NOTE: raw binary — never read this field back via get_redis_client()
            # (decode_responses=True). Use get_redis_binary_client() instead if this
            # ever needs retrieving (e.g. a debugging hgetall).
            key,
            mapping={
                "embedding": embedding,
                "query": query,
                "answer": answer,
                "provider": provider,
                "namespace": namespace,
            },
        )
        client.expire(key, CACHE_TTL_SECONDS)
    except redis.RedisError:
        logger.warning("Redis unavailable — skipping cache write")


def entity_mismatch(query_a: str, query_b: str) -> bool:
    query_a_lower = query_a.lower()
    query_b_lower = query_b.lower()

    for group in ENTITY_GROUPS:
        terms_in_a = {term for term in group if term in query_a_lower}
        terms_in_b = {term for term in group if term in query_b_lower}

        if terms_in_a and terms_in_b and terms_in_a != terms_in_b:
            return True

    return False


def find_cached_answer(
    query: str, provider: str | None = None, embedding: bytes | None = None
) -> dict | None:
    client = get_redis_client()
    if embedding is None:
        embedding = cache_embedding(query)
    namespace = cache_namespace(provider)

    knn_query = (
        Query(f"(@namespace:{{{namespace}}})=>[KNN 1 @embedding $vec AS score]")
        .sort_by("score")
        .return_fields("query", "answer", "provider", "score")
        .dialect(2)
    )

    try:
        results = client.ft(CACHE_INDEX_NAME).search(
            knn_query, query_params={"vec": embedding}
        )
    except redis.RedisError:
        logger.warning("Redis unavailable — treating as cache miss")
        return None

    if results.total == 0:
        return None

    top_hit = results.docs[0]
    distance = float(top_hit.score)
    similarity = 1 - distance

    if similarity < CACHE_SIMILARITY_THRESHOLD:
        return None

    if entity_mismatch(query, top_hit.query):
        return None

    return {
        "query": top_hit.query,
        "answer": top_hit.answer,
        "provider": top_hit.provider,
        "similarity": similarity,
    }


def clear_cache() -> int:
    client = get_redis_client()
    count = 0
    try:
        for key in client.scan_iter(match=f"{CACHE_KEY_PREFIX}*"):
            client.delete(key)
            count += 1
    except redis.RedisError:
        logger.warning("Redis unavailable — cache clear failed")
    return count


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
"""
python -c "
from src.llm.semantic_cache import store_cache_entry
store_cache_entry('Where is the spare tyre in a Sedan?', 'Under the boot floor in the trunk.', 'groq')
print('stored')
"

"""

# End-to-End testing
"""
python -c "
from src.llm.semantic_cache import find_cached_answer

print('--- Exact match ---')
print(find_cached_answer('Where is the spare tyre in a Sedan?'))

print('--- Paraphrase ---')
print(find_cached_answer('Where can I find the spare wheel in a Sedan?'))

print('--- Dangerous SUV variant (should be blocked) ---')
print(find_cached_answer('Where is the spare tyre in an SUV?'))
"

"""
