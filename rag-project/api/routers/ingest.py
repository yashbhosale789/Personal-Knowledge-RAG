import logging
from fastapi import APIRouter, HTTPException, Depends
from starlette.concurrency import run_in_threadpool

from api.models.responses import IngestResponse
from api.models.requests import IngestRequest
from api.core.exceptions import IngestError
from api.core.auth import verify_api_key

from src.llm.semantic_cache import clear_cache

logger = logging.getLogger(__name__)

router = APIRouter()


def _run_ingest(file_path: str, force_reingest: bool) -> IngestResponse:
    # Complete this function
    import os
    from pathlib import Path
    import config
    from src.ingestion.loader import load_documents
    from src.ingestion.chunker import chunk_documents
    from src.embedding.embedder import get_embedding_model
    from src.vectorstore.store import get_vectorstore
    from src.pipeline.injection_scanner import scan_for_injection

    # if not os.path.exists(file_path):
    #     raise IngestError(f"File not found: {file_path}", file_path=file_path)

    resolved_path = Path(file_path).resolve()
    allowed_root = config.DATA_DIR.resolve()

    if not resolved_path.is_relative_to(allowed_root):
        raise IngestError(
            "File path is outside the allowed ingest directory.", file_path=file_path
        )

    try:
        docs = load_documents(file_path)

        full_text = "\n".join(doc.page_content for doc in docs)
        scan_result = scan_for_injection(full_text)

        if scan_result["flagged"]:
            logger.warning(
                f"Ingest blocked after {file_path} - injection patterns detected: {scan_result['categories']}"
            )
            raise IngestError(
                f"Document rejected: possible prompt injection detected ({','.join(scan_result['categories'])})",
                file_path=file_path,
            )

        chunks = chunk_documents(docs)
        embedder = get_embedding_model()
        store = get_vectorstore()
        store.add_documents(chunks, embedder)

        try:
            cleared_count = clear_cache()
            logger.info(f"Cleared {cleared_count} cache entries after ingest.")

        except Exception as e:
            logger.warning(f"Cache cleare failed aftrer ingest (non-fatal): {e}")

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
