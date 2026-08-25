import logging
from fastapi import APIRouter, HTTPException, Depends
from starlette.concurrency import run_in_threadpool

from api.models.responses import IngestResponse
from api.models.requests import IngestRequest
from api.core.exceptions import IngestError
from api.core.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter()


def _run_ingest(file_path: str, force_reingest: bool) -> IngestResponse:
    # Complete this function
    import os
    from src.ingestion.loader import load_documents
    from src.ingestion.chunker import chunk_documents
    from src.embedding.embedder import get_embedding_model
    from src.vectorstore.store import get_vectorstore

    if not os.path.exists(file_path):
        raise IngestError(f"File not found: {file_path}", file_path=file_path)

    try:
        docs = load_documents(file_path)
        chunks = chunk_documents(docs)
        embedder = get_embedding_model()
        store = get_vectorstore()
        store.add_documents(chunks, embedder)

        return IngestResponse(
            status="success",
            file_path=file_path,
            chunks_created=len(chunks),
            message=f"Successfully ingested {len(chunks)} chunks.",
        )

    except Exception as e:
        raise IngestError(str(e), file_path=file_path)


@router.post("/ingest", response_model=IngestResponse, status_code=200)
async def ingest_endpoint(body: IngestRequest, _: None = Depends(verify_api_key)):
    try:
        result = await run_in_threadpool(
            _run_ingest, body.file_path, body.force_reingest
        )
        return result

    except IngestError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except Exception as e:
        logger.exception(f"Unexpected ingest error for {body.file_path}.")
        raise HTTPException(
            status_code=500, detail="Internal server error during ingestion."
        )
