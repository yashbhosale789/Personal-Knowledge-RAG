import logging
import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

import config
from api.core.auth import verify_api_key
from api.core.exceptions import IngestError
from api.models.requests import IngestRequest
from api.models.responses import (
    DeleteResponse,
    DocumentInfo,
    DocumentListResponse,
    IngestResponse,
)
from src.ingestion.ingest import IngestRejected, index_changed, ingest_file
from src.llm.rate_limiter import is_rate_limited
from src.vectorstore.store import chunk_counts, delete_by_source

logger = logging.getLogger(__name__)

router = APIRouter()

# One write at a time: every ingest and delete holds this. Re-entrant so an upload can hold it
# across its file swap and the _run_ingest inside. Per process: one uvicorn worker (Dockerfile).
_write_lock = threading.RLock()


@contextmanager
def _writing(file_path: str):
    # Non-blocking: a queue of waiting uploads would each hold a spooled file on a 1 GiB box.
    if not _write_lock.acquire(blocking=False):
        raise IngestError(
            "Another document is being processed. Try again shortly.",
            file_path=file_path,
            status_code=409,
        )
    try:
        yield
    finally:
        _write_lock.release()


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


def _run_ingest(file_path: str, *, max_chars: int | None = None) -> IngestResponse:
    resolved_path = _resolve_and_validate_path(file_path)

    with _writing(file_path):
        try:
            chunks = ingest_file(resolved_path, max_chars=max_chars)

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

    with _writing(file_path):
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


# --- /documents: the UI's upload, list and delete (Phase 15.0 PR 2) -----------------------


def _check_name(name: str | None) -> str:
    """A bare file name ending in .pdf. Rejected, not stripped: browsers send a bare name."""
    if (
        not name
        or any(c in "/\\" or ord(c) < 32 for c in name)
        or not name.lower().endswith(".pdf")  # also rejects "." and ".."
        or len(name.encode()) > 255
    ):
        raise IngestError(
            "Invalid file name: use a plain file name ending in .pdf.",
            file_path=str(name),
            status_code=400,
        )
    return name


async def _check_rate(api_key_hash: str) -> None:
    if await run_in_threadpool(is_rate_limited, api_key_hash, "documents"):
        raise HTTPException(
            status_code=429, detail="Too many document changes; retry in a minute."
        )


def _save_upload(upload: BinaryIO, part: Path, name: str) -> None:
    if upload.read(5) != b"%PDF-":
        raise IngestError("Not a PDF file.", file_path=name, status_code=400)
    upload.seek(0)
    size = 0
    with open(part, "wb") as out:
        while block := upload.read(1024 * 1024):
            size += len(block)
            if size > config.MAX_UPLOAD_BYTES:
                raise IngestError(
                    f"File is larger than the {config.MAX_UPLOAD_BYTES // 2**20} MB limit.",
                    file_path=name,
                    status_code=413,
                )
            out.write(block)


def _run_upload(name: str, upload: BinaryIO) -> IngestResponse:
    final = config.DATA_DIR / name
    # Dot names with a non-.pdf suffix: never listed, never picked up by scripts/ingest.py.
    part = final.with_name(f".{name}.part")
    backup = final.with_name(f".{name}.bak")

    with _writing(name):
        try:
            _save_upload(upload, part, name)
            had_old = final.exists()
            if had_old:
                os.replace(final, backup)
            os.replace(part, final)  # `source` must be the final path
            try:
                result = _run_ingest(str(final), max_chars=config.MAX_UPLOAD_CHARS)
            except Exception:
                # Rejections raise before delete_by_source, so the old file matches its chunks again.
                if had_old:
                    os.replace(backup, final)
                else:
                    final.unlink(missing_ok=True)
                raise
            backup.unlink(missing_ok=True)
        finally:
            part.unlink(missing_ok=True)

    return result.model_copy(update={"file_path": name})


def _list_documents() -> DocumentListResponse:
    counts = chunk_counts()
    files = sorted(
        p
        for p in config.DATA_DIR.iterdir()
        if p.is_file() and p.suffix.lower() == ".pdf"
    )
    return DocumentListResponse(
        documents=[
            DocumentInfo(name=p.name, chunks=counts.get(str(p.resolve()), 0))
            for p in files
        ]
    )


@router.post(
    "/documents",
    response_model=IngestResponse,
    summary="Upload a PDF; a document with the same name is replaced.",
)
async def upload_document(
    file: UploadFile, api_key_hash: str = Depends(verify_api_key)
):
    await _check_rate(api_key_hash)
    try:
        name = _check_name(file.filename)
        return await run_in_threadpool(_run_upload, name, file.file)

    except IngestError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except Exception:
        logger.exception("Unexpected upload error.")
        raise HTTPException(
            status_code=500, detail="Internal server error during upload."
        )


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="The PDFs in the documents folder, with their chunk counts.",
)
async def list_documents(_: str = Depends(verify_api_key)):
    return await run_in_threadpool(_list_documents)


@router.delete(
    "/documents/{name}",
    response_model=DeleteResponse,
    summary="Delete a document and its chunks.",
)
async def delete_document(name: str, api_key_hash: str = Depends(verify_api_key)):
    await _check_rate(api_key_hash)
    try:
        path = config.DATA_DIR / _check_name(name)
        if not path.is_file():
            raise IngestError("Document not found.", file_path=name, status_code=404)
        result = await run_in_threadpool(_run_delete, str(path))
        return result.model_copy(update={"file_path": name})

    except IngestError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except Exception:
        logger.exception("Unexpected delete error.")
        raise HTTPException(
            status_code=500, detail="Internal server error during deletion."
        )
