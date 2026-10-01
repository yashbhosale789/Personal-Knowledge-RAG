import logging

from config import REWRITE_SYSTEM
from src.llm.client import call_llm

logger = logging.getLogger(__name__)


def rewrite_query(query: str, provider: str | None = None) -> str:
    """
    Rewrites a conversational query into a precise search query.

    Falls back to original query if rewriting fails — retrieval still works,
    just with lower quality input.

    Args:
        query: Raw user query.

    Returns:
        Rewritten query string.
    """

    try:
        rewritten = call_llm(prompt=query, system=REWRITE_SYSTEM, provider=provider)
        logger.info(f"Query rewrite: {query} -> {rewritten}")
        return rewritten

    except Exception as e:  # noqa: BLE001
        logger.info(f"Query rewrite failed, using original. Reason: {e}")
        return query
