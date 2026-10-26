import datetime
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.concurrency import run_in_threadpool

import config
from api.core.auth import verify_api_key
from api.core.exceptions import PipelineNotReadyError, ProviderError
from api.core.retry import call_with_fallback
from api.models.requests import QueryRequest
from api.models.responses import QueryResponse
from api.routers.health import is_pipeline_ready
from src.llm.semantic_cache import (
    cache_embedding,
    find_cached_answer,
    store_cache_entry,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _run_pipeline(query: str, provider: str, return_contexts: bool) -> dict:
    from src.pipeline.advanced_rag import run_advanced_rag_pipeline

    return run_advanced_rag_pipeline(
        query, return_contexts=return_contexts, provider=provider
    )


def _log_query(
    request_id: str,
    outcome: str | None,
    provider: str,
    llm_usage: dict | None = None,
) -> None:
    logger.info(
        json.dumps(
            {
                "event": "query",
                "request_id": request_id,
                "outcome": outcome,
                "provider": provider,
                "prompt_version": config.PROMPT_VERSION,
                # Per-stage tokens/latency of the successful attempt; none on a cache hit.
                "llm_usage": llm_usage,
            }
        )
    )


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Query the RAG Pipeline.",
    status_code=200,
)
async def query_endpoint(
    request: Request, body: QueryRequest, api_key_hash: str = Depends(verify_api_key)
):
    if not is_pipeline_ready():
        raise PipelineNotReadyError()

    query = body.query.strip()
    if not query:
        raise HTTPException(
            status_code=400, detail="Query must not be empty or whitespace only."
        )

    request_id = getattr(request.state, "request_id", "unknown")
    start_time = __import__("time").monotonic()
    preferred_provider = body.provider or config.PIPELINE_PROVIDER

    embedding = await run_in_threadpool(cache_embedding, query)
    cached = await run_in_threadpool(
        find_cached_answer, query, preferred_provider, embedding
    )

    if cached is not None:
        latency_ms = (__import__("time").monotonic() - start_time) * 1000
        _log_query(request_id, "cached", cached["provider"])
        return QueryResponse(
            query_id=request_id,
            query=body.query,
            rewritten_query=None,
            answer=cached["answer"],
            sources=[],
            chunks_used=0,
            provider=cached["provider"],
            latency_ms=round(latency_ms, 2),
            timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
            sufficiency=None,
            citation_check=None,
            confidence=None,
            outcome="cached",
            prompt_version=config.PROMPT_VERSION,
        )

    try:

        def make_pipeline_call(provider: str):
            return _run_pipeline(query, provider, body.return_contexts)

        result, provider_used = await call_with_fallback(
            make_pipeline_call,
            preferred_provider=preferred_provider,
            max_retries=1,
            api_key_hash=api_key_hash,
        )

    except ProviderError as e:
        logger.error(
            "All providers failed.",
            extra={"request_id": request_id, "details": e.details},
        )
        raise HTTPException(status_code=502, detail=e.message)

    if result.get("outcome") != "abstain":
        await run_in_threadpool(
            store_cache_entry, query, result.get("answer", ""), provider_used, embedding
        )

    latency_ms = (__import__("time").monotonic() - start_time) * 1000
    _log_query(
        request_id, result.get("outcome"), provider_used, result.get("llm_usage")
    )

    return QueryResponse(
        query_id=request_id,
        query=body.query,
        rewritten_query=result.get("rewritten_query"),
        answer=result.get("answer", ""),
        sources=result.get("sources", []),
        chunks_used=result.get("chunks_used", 0),
        provider=provider_used,
        latency_ms=round(latency_ms, 2),
        timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
        sufficiency=result.get("sufficiency"),
        citation_check=result.get("citation_check"),
        confidence=result.get("confidence"),
        outcome=result.get("outcome"),
        prompt_version=config.PROMPT_VERSION,
    )
