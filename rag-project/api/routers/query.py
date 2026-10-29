import datetime
import hashlib
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.concurrency import run_in_threadpool

import config
from api.core.auth import verify_api_key
from api.core.exceptions import PipelineNotReadyError, ProviderError
from api.core.metrics import rag_query_outcomes_total
from api.core.retry import call_with_fallback
from api.models.requests import QueryRequest
from api.models.responses import QueryResponse
from api.routers.health import is_pipeline_ready
from src import observability, tracing
from src.llm.semantic_cache import (
    GROUNDING_FIELDS,
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
    latency_ms: float,
    stages: list[dict],
    llm_usage: dict | None = None,
    **fields,
) -> None:
    """fields: outcome-specific extras (cache-hit similarity, rewritten-query hash)."""
    rag_query_outcomes_total.labels(outcome=str(outcome)).inc()
    stages_ms = observability.summarize(stages)
    llm_ms = llm_usage["llm_ms"] if llm_usage else 0
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
                "latency_ms": round(latency_ms, 1),
                # Non-LLM stage self-times, summed over pipeline attempts.
                "stages_ms": stages_ms,
                # Time in neither: failed provider attempts, backoff, thread hand-offs.
                "unaccounted_ms": round(
                    latency_ms - sum(stages_ms.values()) - llm_ms, 1
                ),
                **fields,
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
    request_id = getattr(request.state, "request_id", "unknown")
    with (
        observability.track() as stages,
        tracing.request_trace(request_id, body.query.strip()) as trace,
    ):
        return await _answer(request, body, api_key_hash, stages, trace)


async def _answer(
    request: Request,
    body: QueryRequest,
    api_key_hash: str,
    stages: list[dict],
    trace: tracing.Observation,
) -> QueryResponse:
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

    with observability.timed("cache_embed") as obs:
        obs.update(input=query)
        embedding = await run_in_threadpool(cache_embedding, query)
    with observability.timed("cache_lookup") as obs:
        cached = await run_in_threadpool(
            find_cached_answer, query, preferred_provider, embedding
        )
        hit = {"hit": False}
        if cached is not None:
            hit = {
                "hit": True,
                "similarity": round(cached["similarity"], 4),
                "cached_query": cached["query"],
            }
        obs.update(input=query, output=hit)

    if cached is not None:
        latency_ms = (__import__("time").monotonic() - start_time) * 1000
        # For the Phase 15.3 cache-layer decision: how close hits are, and how many
        # are verbatim repeats an exact-match cache would also catch.
        _log_query(
            request_id,
            "cached",
            cached["provider"],
            latency_ms,
            stages,
            cache_similarity=round(cached["similarity"], 4),
            cache_exact_repeat=cached["query"] == query,
        )
        grounding = cached.get("grounding") or {}
        trace.update(
            output={
                "answer": cached["answer"],
                "outcome": "cached",
                "sources": grounding.get("sources") or [],
            },
            metadata={"provider": cached["provider"]},
        )
        return QueryResponse(
            query_id=request_id,
            query=body.query,
            rewritten_query=None,
            answer=cached["answer"],
            sources=grounding.get("sources") or [],
            chunks_used=grounding.get("chunks_used") or 0,
            provider=cached["provider"],
            latency_ms=round(latency_ms, 2),
            timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
            sufficiency=grounding.get("sufficiency"),
            citation_check=grounding.get("citation_check"),
            confidence=grounding.get("confidence"),
            outcome="cached",
            prompt_version=config.PROMPT_VERSION,
        )

    try:

        def make_pipeline_call(provider: str):
            # One span per provider attempt, so retries and fallbacks show in the trace.
            with tracing.observe(
                "run-rag-pipeline",
                "chain",
                input={"query": query},
                metadata={"provider": provider},
            ) as attempt:
                result = _run_pipeline(query, provider, body.return_contexts)
                attempt.update(
                    output={
                        "answer": result.get("answer"),
                        "outcome": result.get("outcome"),
                    }
                )
                return result

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

    # Not cached: an abstain, or an empty retrieval, which must not outlive the
    # ingest that would answer it; nor an unverified answer, which must not outlive the verifier outage.
    unverified = (result.get("citation_check") or {}).get("tier") == "verifier_error"
    if result.get("outcome") not in ("abstain", "empty") and not unverified:
        with observability.timed("cache_store") as obs:
            obs.update(input={"query": query, "outcome": result.get("outcome")})
            await run_in_threadpool(
                store_cache_entry,
                query,
                result.get("answer", ""),
                provider_used,
                embedding,
                {field: result.get(field) for field in GROUNDING_FIELDS},
            )

    latency_ms = (__import__("time").monotonic() - start_time) * 1000
    rewritten = result.get("rewritten_query")
    _log_query(
        request_id,
        result.get("outcome"),
        provider_used,
        latency_ms,
        stages,
        result.get("llm_usage"),
        # For Phase 15.3: repeats of one rewrite are what a retrieval cache would reuse.
        rewritten_query_hash=(
            hashlib.sha256(rewritten.encode()).hexdigest()[:12] if rewritten else None
        ),
    )

    trace.update(
        output={
            "answer": result.get("answer", ""),
            "outcome": result.get("outcome"),
            "sources": result.get("sources", []),
            "confidence": result.get("confidence"),
        },
        metadata={"provider": provider_used},
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
