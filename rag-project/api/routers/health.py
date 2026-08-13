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
    description="Returns server status and pipeline readiness."
)

async def health_check():
    return HealthResponse(
        status="ok" if _pipeline_ready else "degraged",
        version="0.1.0",
        pipeline_ready=_pipeline_ready,
        timestamp=datetime.datetime.utcnow().isoformat() + "Z"
    )