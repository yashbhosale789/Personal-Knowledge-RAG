import logging
from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from api.models.responses import IngestResponse
from api.models.requests import IngestRequest
from api.core.exceptions import IngestError

logger = logging.getLogger(__name__)

router = APIRouter()


def _run_ingest(file_path : str, force_reingest: bool) -> IngestResponse:
    # Complete this function
    return None     # Remove this

@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=200
)
async def ingest_endpoint(body: IngestRequest):
    try:
        result = await run_in_threadpool(_run_ingest, body.file_path, body.force_reingest)
        return result

    except IngestError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except Exception as e:
        logger.exception(f"Unexpected ingest error for {body.file_path}.")
        raise HTTPException(status_code=500, detail="Internal server error during ingestion.")