import logging
import logging.config

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.routers import health, query, ingest
from api.middleware.logging import StructuredLoggingMiddleware
from api.core.exceptions import RAGException

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
    "root": {
        "level": "INFO",
        "handlers": ["console"]
    }
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger(__name__)
    logger.info("Starting RAG API - initializing pipeline...")

    try:
        from starlette.concurrency import run_in_threadpool
        from src.pipeline.advanced_rag import run_advanced_rag_pipeline

        # Warm up: run a dummy query to force model loading
        await run_in_threadpool(run_advanced_rag_pipeline, "warmup", return_contexts=False)
        health.set_pipeline_ready(True)
        logger.info("Pipeline initialized and ready.")

    except Exception as e:
        logger.error("Pipeline initialization failed: %s", e)
        # Server starts but in degraded state — health endpoint reports this

    yield  # Server runs here

    logger.info("Shutting down RAG API.")
    health.set_pipeline_ready(False)


app = FastAPI(
    title="RAG API",
    description="Production-grade RAG API.",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(StructuredLoggingMiddleware)

app.include_router(health.router, tags=["Health"])
app.include_router(query.router, tags=["Query"])
app.include_router(ingest.router, tags=["Ingest"])


@app.exception_handler(RAGException)
async def rag_exception_handler(request: Request, exc: RAGException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error":exc.message, "details":exc.details}
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, e: Exception):
    logging.getLogger(__name__).exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"error":"Internal saerver error."}
    )
