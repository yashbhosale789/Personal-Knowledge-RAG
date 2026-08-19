import datetime
import logging
from fastapi import APIRouter, Request, HTTPException
from starlette.concurrency import run_in_threadpool

from api.models.requests import QueryRequest
from api.models.responses import QueryResponse
from api.core.exceptions import ProviderError, PipelineNotReadyError
from api.core.retry import call_with_fallback
from api.routers.health import is_pipeline_ready

logger = logging.getLogger(__name__)

router = APIRouter()


def _run_pipeline(query: str, provider: str, return_contexts: bool) -> dict:
    # Thin Synchronous wrapper around the pipeline.
    # sets the provider in config before calling, resets after.

    import config
    from src.pipeline.advanced_rag import run_advanced_rag_pipeline

    original_provider = config.PIPELINE_PROVIDER

    try:
        config.PIPELINE_PROVIDER = provider
        return run_advanced_rag_pipeline(query, return_contexts=return_contexts)

    finally:
        config.PIPELINE_PROVIDER = original_provider


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Query the RAG Pipeline.",
    status_code=200,
)
async def query_endpoint(request: Request, body: QueryRequest):
    import config

    if not is_pipeline_ready():
        raise PipelineNotReadyError()

    query = body.query.strip()
    if not query:
        raise HTTPException(
            status_code=400, detail="Query must not be empty or whitespace only."
        )

    request_id = getattr(request.state, "request_id", "unknown")
    start_time = __import__("time").monotonic()

    try:

        def make_pipeline_call(provider: str):
            return _run_pipeline(query, provider, body.return_contexts)

        result, provider_used = await call_with_fallback(
            make_pipeline_call,
            preferred_provider=body.provider or config.PIPELINE_PROVIDER,
            max_retries=3,
        )

    except ProviderError as e:
        logger.error(
            "All providers failed.",
            extra={"request_id": request_id, "details": e.details},
        )
        raise HTTPException(status_code=502, detail=e.message)

    latency_ms = (__import__("time").monotonic() - start_time) * 1000

    return QueryResponse(
        query_id=request_id,
        query=body.query,
        rewritten_query=result.get("rewritten_query"),
        answer=result.get("answer", ""),
        sources=result.get("sources", []),
        chunks_used=result.get("chunks_used", 0),
        provider=provider_used,
        latency_ms=round(latency_ms, 2),
        timestamp=datetime.datetime.utcnow().isoformat() + "Z",
        sufficiency=result.get("sufficiency")
    )
