import logging
import logging.config
import asyncio

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.routers import health, query, ingest, metrics
from api.middleware.logging import StructuredLoggingMiddleware
from api.core.exceptions import RAGException

# from api.routers.metrics import router as metrics_router

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "logging.Formatter",
            "fmt": "%(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        }
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}


def _warmup_retrieval_component() -> None:
    """
    Loads retrieval-side components only — embedder, vectorstore, and the
    BM25/reranker singletons owned by advanced_rag.py. Deliberately excludes
    the LLM: provider health is transient and already handled per-request by
    call_with_fallback (see _warmup_llm).

    Importing advanced_rag triggers its own module-level singleton creation
    (_bm25, _reranker) — must import the module itself, not re-instantiate
    BM25Retriever/CrossEncoderReranker separately, or warmup builds throwaway
    copies while the real pipeline still cold-loads its own on first call.
    """
    from src.embedding.embedder import get_embedding_model
    from src.vectorstore.store import get_vectorstore
    import src.pipeline.advanced_rag

    get_embedding_model()
    get_vectorstore()


async def _warmup_llm(logger: logging.Logger) -> None:
    try:
        from api.core.retry import call_with_fallback
        from src.llm.client import call_llm
        import config

        def make_llm_call(provider: str):
            return call_llm("Reply with OK.", provider=provider)

        await call_with_fallback(
            make_llm_call, preferred_provider=config.PIPELINE_PROVIDER, max_retries=1
        )
        logger.info("LLM provider warmed up.")

    except Exception as e:
        logger.warning(f"LLM warmup failed (non-fatal, first request will retry): {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger(__name__)
    logger.info("Starting RAG API - initializing pipeline...")

    try:
        from starlette.concurrency import run_in_threadpool

        # from src.pipeline.advanced_rag import run_advanced_rag_pipeline

        # Warm up: run a dummy query to force model loading
        # await run_in_threadpool(run_advanced_rag_pipeline, "warmup", return_contexts=False)
        await run_in_threadpool(_warmup_retrieval_component)
        health.set_pipeline_ready(True)
        logger.info("Retrieval Components initialized and ready.")

    except Exception as e:
        logger.error("Retrieval Components initialization failed: %s", e)
        # Server starts but in degraded state — health endpoint reports this

    try:
        await asyncio.wait_for(_warmup_llm(logger), timeout=15)
    except asyncio.TimeoutError:
        logger.warning(
            "LLM warmup timed out after 15s (non-fatal, first request will retry)."
        )

    yield  # Server runs here

    logger.info("Shutting down RAG API.")
    health.set_pipeline_ready(False)


app = FastAPI(
    title="RAG API",
    description="Production-grade RAG API.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(StructuredLoggingMiddleware)

app.include_router(health.router, tags=["Health"])
app.include_router(query.router, tags=["Query"])
app.include_router(ingest.router, tags=["Ingest"])
app.include_router(metrics.router, tags=["Metrics"])


@app.exception_handler(RAGException)
async def rag_exception_handler(request: Request, exc: RAGException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "details": exc.details},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, e: Exception):
    logging.getLogger(__name__).exception("Unhandled exception")
    return JSONResponse(status_code=500, content={"error": "Internal server error."})
