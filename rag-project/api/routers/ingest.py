import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

import config
from api.core.auth import verify_api_key
from api.core.exceptions import IngestError
from api.models.requests import IngestRequest
from api.models.responses import DeleteResponse, IngestResponse
from src.ingestion.ingest import IngestRejected, index_changed, ingest_file
from src.vectorstore.store import delete_by_source

logger = logging.getLogger(__name__)

router = APIRouter()


def _resolve_and_validate_path(file_path: str) -> Path:

    # if not os.path.exists(file_path):
    #     raise IngestError(f"File not found: {file_path}", file_path=file_path)

    resolved_path = Path(file_path).resolve()
    allowed_root = config.DATA_DIR.resolve()

    if not resolved_path.is_relative_to(allowed_root):
        raise IngestError(
            "File path is outside the allowed ingest directory.",
            file_path=file_path,
        )

    if resolved_path.suffix.lower() != ".pdf":
        raise IngestError(
            f"Unsupported file type '{resolved_path.suffix}'. Only .pdf is supported.",
            file_path=file_path,
        )

    if not resolved_path.exists():
        raise IngestError(f"File not found: {file_path}", file_path=file_path)

    return resolved_path


def _run_ingest(file_path: str) -> IngestResponse:
    resolved_path = _resolve_and_validate_path(file_path)

    try:
        chunks = ingest_file(resolved_path)

        return IngestResponse(
            status="success",
            file_path=file_path,
            chunks_created=len(chunks),
            message=f"Successfully ingested {len(chunks)} chunks.",
        )

    except IngestRejected as e:
        raise IngestError(str(e), file_path=file_path)

    except Exception:
        logger.exception(f"Ingest failed for {file_path}")
        raise IngestError("Failed to process document.", file_path=file_path)


@router.post("/ingest", response_model=IngestResponse, status_code=200)
async def ingest_endpoint(body: IngestRequest, _: None = Depends(verify_api_key)):
    try:
        result = await run_in_threadpool(_run_ingest, body.file_path)
        return result

    except IngestError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except Exception:
        logger.exception(f"Unexpected ingest error for {body.file_path}.")
        raise HTTPException(
            status_code=500, detail="Internal server error during ingestion."
        )


def _run_delete(file_path: str) -> DeleteResponse:
    resolved_path = _resolve_and_validate_path(file_path)

    try:
        chunks_deleted = delete_by_source(str(resolved_path))
        index_changed()  # before os.remove: Chroma has changed even if the remove fails
        os.remove(resolved_path)

        return DeleteResponse(
            status="success",
            file_path=file_path,
            chunks_deleted=chunks_deleted,
            message=f"Deleted {chunks_deleted} chunks and removed files.",
        )

    except IngestError:
        raise

    except Exception:
        logger.exception(f"Delete failed for {file_path}")
        raise IngestError(
            "Failed to delete document.",
            file_path=file_path,
        )


@router.delete("/ingest", response_model=DeleteResponse, status_code=200)
async def delete_endpoint(file_path: str, _: None = Depends(verify_api_key)):
    try:
        result = await run_in_threadpool(_run_delete, file_path)
        return result

    except IngestError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except Exception:
        logger.exception(f"Unexpected delete error for {file_path}.")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during deletion.",
        )
