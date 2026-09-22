import logging
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from starlette.concurrency import run_in_threadpool

import config
from api.models.responses import IngestResponse
from api.models.responses import DeleteResponse
from api.models.requests import IngestRequest
from api.core.exceptions import IngestError
from api.core.auth import verify_api_key

from src.llm.semantic_cache import clear_cache

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

    if resolved_path.suffix.lower != ".pdf":
        raise IngestError(
            f"Unsupported file type '{resolved_path.suffix}'. Only .pdf is supported.",
            file_path=file_path,
        )

    if not resolved_path.exists():
        raise IngestError(f"File not found: {file_path}", file_path=file_path)

    return resolved_path


def _run_ingest(file_path: str, force_reingest: bool) -> IngestResponse:

    # import os
    # from pathlib import Path
    # import config

    from src.ingestion.loader import load_documents
    from src.ingestion.chunker import chunk_documents

    # from src.embedding.embedder import get_embedding_model
    # from src.vectorstore.store import get_vectorstore

    from src.vectorstore.store import add_chunks
    from src.pipeline.injection_scanner import scan_for_injection

    resolved_path = _resolve_and_validate_path(file_path)

    try:
        # docs = load_documents(file_path)
        docs = load_documents(resolved_path)

        if not docs:
            raise IngestError(
                "No content could be extracted from this document. It may be corrupted or empty.",
                file_path=file_path,
            )

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

        # chunks = chunk_documents(docs)
        # embedder = get_embedding_model()
        # store = get_vectorstore()
        # store.add_documents(chunks, embedder)

        chunks = chunk_documents(docs)
        add_chunks(chunks)

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

    # except Exception as e:
    #     raise IngestError(str(e), file_path=file_path)

    except IngestError:
        raise

    except Exception:
        logger.exception(f"Ingest failed for {file_path}")
        raise IngestError("Failed to process document.", file_path=file_path)


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


def _run_delete(file_path: str) -> DeleteResponse:
    from src.vectorstore.store import delete_by_source

    resolved_path = _resolve_and_validate_path(file_path)

    try:
        chunks_deleted = delete_by_source(str(resolved_path))
        os.remove(resolved_path)

        try:
            cleared_count = clear_cache()
            logger.info(f"Cleared {cleared_count} cache entries after delete.")

        except Exception as e:
            logger.warning(f"Cache clear failed after delete (non-fatal): {e}")

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
