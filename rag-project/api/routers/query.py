import asyncio
import datetime
import hashlib
import json
import logging
import time
from collections.abc import AsyncIterator, Callable

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

import config
from api.core.auth import verify_api_key
from api.core.exceptions import PipelineNotReadyError, ProviderError
from api.core.metrics import rag_query_outcomes_total
from api.core.retry import call_with_fallback
from api.models.requests import QueryRequest
from api.models.responses import QueryResponse, QueryStreamFinal
from api.routers.health import is_pipeline_ready
from src import observability, tracing
from src.feedback import save_grounding
from src.llm.client import model_name
from src.llm.semantic_cache import (
    GROUNDING_FIELDS,
    cache_embedding,
    find_cached_answer,
    store_cache_entry,
)
from src.pipeline.confidence import CAVEAT_TEXT

logger = logging.getLogger(__name__)

router = APIRouter()


def _run_pipeline(query: str, provider: str, return_contexts: bool) -> dict:
    from src.pipeline.advanced_rag import run_advanced_rag_pipeline

    return run_advanced_rag_pipeline(
        query, return_contexts=return_contexts, provider=provider
    )


def _run_stream_pipeline(
    query: str, provider: str, on_token: Callable[[str], None]
) -> dict:
    from src.pipeline.advanced_rag import run_advanced_rag_pipeline

    return run_advanced_rag_pipeline(query, provider=provider, on_token=on_token)


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


async def _save_feedback_grounding(
    request_id: str,
    query: str,
    answer: str,
    outcome: str | None,
    provider: str,
    chunks: list[dict] | None,
) -> None:
    """What POST /feedback stores for this request ID; the client is never asked."""
    await run_in_threadpool(
        save_grounding,
        request_id,
        {
            "query": query,
            "answer": answer,
            "outcome": outcome,
            "prompt_version": config.PROMPT_VERSION,
            "model": model_name(provider),
            "chunks": chunks or [],
        },
    )


async def _lookup_cache(query: str, provider: str) -> tuple[bytes, dict | None]:
    with observability.timed("cache_embed") as obs:
        obs.update(input=query)
        embedding = await run_in_threadpool(cache_embedding, query)
    with observability.timed("cache_lookup") as obs:
        cached = await run_in_threadpool(find_cached_answer, query, provider, embedding)
        hit = {"hit": False}
        if cached is not None:
            hit = {
                "hit": True,
                "similarity": round(cached["similarity"], 4),
                "cached_query": cached["query"],
            }
        obs.update(input=query, output=hit)
    return embedding, cached


async def _record_cache_hit(
    request_id: str,
    query: str,
    cached: dict,
    latency_ms: float,
    stages: list[dict],
    trace: tracing.Observation,
) -> dict:
    """Logs, traces and saves feedback grounding for a cache hit; returns its cached grounding."""
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
    await _save_feedback_grounding(
        request_id,
        query,
        cached["answer"],
        "cached",
        cached["provider"],
        grounding.get("chunks"),
    )
    return grounding


async def _record_result(
    request_id: str,
    query: str,
    result: dict,
    provider_used: str,
    embedding: bytes,
    start_time: float,
    stages: list[dict],
    trace: tracing.Observation,
) -> float:
    """Caches, logs, traces and saves feedback grounding for a pipeline result; returns latency_ms."""
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

    latency_ms = (time.monotonic() - start_time) * 1000
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
    await _save_feedback_grounding(
        request_id,
        query,
        result.get("answer", ""),
        result.get("outcome"),
        provider_used,
        result.get("chunks"),
    )
    return latency_ms


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
    start_time = time.monotonic()
    preferred_provider = body.provider or config.PIPELINE_PROVIDER

    embedding, cached = await _lookup_cache(query, preferred_provider)

    if cached is not None:
        latency_ms = (time.monotonic() - start_time) * 1000
        grounding = await _record_cache_hit(
            request_id, query, cached, latency_ms, stages, trace
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

    latency_ms = await _record_result(
        request_id, query, result, provider_used, embedding, start_time, stages, trace
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


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _final_event(
    request_id: str,
    body: QueryRequest,
    answer: str,
    provider: str,
    latency_ms: float,
    grounding: dict,
    outcome: str | None,
    rewritten_query: str | None,
) -> dict:
    """`grounding` is a pipeline result or a cache entry's grounding: both carry these fields."""
    return QueryStreamFinal(
        query_id=request_id,
        query=body.query,
        rewritten_query=rewritten_query,
        answer=answer,
        sources=grounding.get("sources") or [],
        chunks_used=grounding.get("chunks_used") or 0,
        provider=provider,
        latency_ms=round(latency_ms, 2),
        timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
        sufficiency=grounding.get("sufficiency"),
        citation_check=grounding.get("citation_check"),
        confidence=grounding.get("confidence"),
        outcome=outcome,
        prompt_version=config.PROMPT_VERSION,
        caveat=CAVEAT_TEXT if grounding.get("confidence") == "low" else None,
        chunks=grounding.get("chunks") or [],
    ).model_dump(mode="json")


@router.post(
    "/query/stream",
    summary="Query the RAG pipeline, streaming the answer as server-sent events.",
    response_class=StreamingResponse,
)
async def query_stream_endpoint(
    request: Request, body: QueryRequest, api_key_hash: str = Depends(verify_api_key)
):
    """
    Events: `token` {text} while the answer is generated, then one `final`
    (QueryStreamFinal), or one `error` {status, error}. A cache hit, abstain or
    empty retrieval sends only `final`. `final.answer` is authoritative: it carries
    the caveat and character fixes applied after generation.
    """
    if not is_pipeline_ready():
        raise PipelineNotReadyError()
    query = body.query.strip()
    if not query:
        raise HTTPException(
            status_code=400, detail="Query must not be empty or whitespace only."
        )
    request_id = getattr(request.state, "request_id", "unknown")
    return StreamingResponse(
        _stream(request_id, body, query, api_key_hash),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


async def _stream(
    request_id: str, body: QueryRequest, query: str, api_key_hash: str
) -> AsyncIterator[str]:
    # Everything runs inside the body generator, so the trace and stage tracker open
    # and close in the one task that streams the response.
    with (
        observability.track() as stages,
        tracing.request_trace(request_id, query) as trace,
    ):
        start_time = time.monotonic()
        preferred_provider = body.provider or config.PIPELINE_PROVIDER
        embedding, cached = await _lookup_cache(query, preferred_provider)

        if cached is not None:
            latency_ms = (time.monotonic() - start_time) * 1000
            grounding = await _record_cache_hit(
                request_id, query, cached, latency_ms, stages, trace
            )
            yield _sse(
                "final",
                _final_event(
                    request_id,
                    body,
                    cached["answer"],
                    cached["provider"],
                    latency_ms,
                    grounding,
                    "cached",
                    None,
                ),
            )
            return

        loop = asyncio.get_running_loop()
        tokens: asyncio.Queue[str | None] = asyncio.Queue()
        sent = False

        def on_token(text: str) -> None:
            nonlocal sent
            sent = True
            # The pipeline applies the same fix to the final answer.
            text = text.replace("【", "[").replace("】", "]")
            loop.call_soon_threadsafe(tokens.put_nowait, text)

        def attempt(provider: str) -> dict:
            with tracing.observe(
                "run-rag-pipeline",
                "chain",
                input={"query": query},
                metadata={"provider": provider},
            ) as span:
                try:
                    result = _run_stream_pipeline(query, provider, on_token)
                except Exception as e:
                    if not sent:
                        raise  # nothing shown yet: retry or fall back, as /query does
                    # Text already reached the client, so another provider cannot take over.
                    logger.error(
                        "Answer stream broke off.",
                        extra={"request_id": request_id, "provider": provider},
                    )
                    return {"stream_error": str(e)}
                span.update(
                    output={
                        "answer": result.get("answer"),
                        "outcome": result.get("outcome"),
                    }
                )
                return result

        # shortcut: a client that disconnects mid-answer leaves this task to finish in the background (threads cannot be cancelled); fine for one user.
        task = asyncio.ensure_future(
            call_with_fallback(
                attempt,
                preferred_provider=preferred_provider,
                max_retries=1,
                api_key_hash=api_key_hash,
            )
        )
        # Queued after every token, because tokens are queued before the worker thread returns.
        task.add_done_callback(lambda _: tokens.put_nowait(None))
        while (text := await tokens.get()) is not None:
            yield _sse("token", {"text": text})

        try:
            result, provider_used = task.result()
        except ProviderError as e:
            logger.error(
                "All providers failed.",
                extra={"request_id": request_id, "details": e.details},
            )
            # The provider's error text stays in the log; the client gets a fixed message.
            yield _sse(
                "error",
                {
                    "status": 502,
                    "error": "Every LLM provider failed. Try again shortly.",
                },
            )
            return
        if "stream_error" in result:
            yield _sse(
                "error",
                {"status": 502, "error": "The answer stream broke off. Try again."},
            )
            return

        latency_ms = await _record_result(
            request_id,
            query,
            result,
            provider_used,
            embedding,
            start_time,
            stages,
            trace,
        )
        yield _sse(
            "final",
            _final_event(
                request_id,
                body,
                result.get("answer", ""),
                provider_used,
                latency_ms,
                result,
                result.get("outcome"),
                result.get("rewritten_query"),
            ),
        )
