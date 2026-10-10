import datetime

from fastapi import APIRouter

from api.models.responses import HealthResponse

router = APIRouter()

_pipeline_ready = False


def set_pipeline_ready(value: bool):
    global _pipeline_ready
    _pipeline_ready = value


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns server status and pipeline readiness.",
)
async def health_check():
    return HealthResponse(
        status="ok" if _pipeline_ready else "degraded",
        version="0.1.0",
        pipeline_ready=_pipeline_ready,
        timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
    )


def is_pipeline_ready() -> bool:
    return _pipeline_ready
