import logging

from config import CONDENSE_SYSTEM, REWRITE_SYSTEM
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
        rewritten = call_llm(
            prompt=query, system=REWRITE_SYSTEM, provider=provider, stage="rewrite"
        )
        # Snippets only: logs keep at most 60 chars of query text (log policy, Data_Privacy.md).
        logger.info(f"Query rewrite: {query[:60]} -> {rewritten[:60]}")
        return rewritten

    except Exception as e:  # noqa: BLE001
        logger.info(f"Query rewrite failed, using original. Reason: {e}")
        return query


def condense_query(
    query: str, history: list[dict], provider: str | None = None
) -> str | None:
    """
    Rewrites a follow-up into a standalone question using the chat history
    (oldest turn first; each has query, rewritten_query and answer).

    Returns None if the call fails or replies with nothing usable, so the caller
    can tell a standalone question from the raw, unresolved follow-up.
    """
    turns = "\n\n".join(
        f"User: {t['query']}\n"
        + (
            f"(standalone: {t['rewritten_query']})\n"
            if t.get("rewritten_query")
            else ""
        )
        + f"Assistant: {t['answer']}"
        for t in history
    )
    prompt = f"<history>\n{turns}\n</history>\n\nLatest message: {query}"
    try:
        standalone = call_llm(
            prompt=prompt, system=CONDENSE_SYSTEM, provider=provider, stage="rewrite"
        ).strip()
    except Exception as e:  # noqa: BLE001
        logger.info(f"Follow-up rewrite failed. Reason: {e}")
        return None
    # A reply this long answered the question instead of restating it.
    if not standalone or len(standalone) > 500:
        return None
    logger.info(f"Follow-up rewrite: {query[:60]} -> {standalone[:60]}")
    return standalone
