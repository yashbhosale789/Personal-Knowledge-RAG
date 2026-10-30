import json
import logging

import redis
from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from api.core.auth import verify_api_key
from api.models.requests import FeedbackRequest
from api.models.responses import FeedbackResponse
from src import feedback
from src.llm.rate_limiter import is_rate_limited

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    summary="Rate an answer from /query.",
    status_code=200,
)
async def feedback_endpoint(
    body: FeedbackRequest, api_key_hash: str = Depends(verify_api_key)
):
    if await run_in_threadpool(is_rate_limited, api_key_hash, "feedback"):
        raise HTTPException(
            status_code=429, detail="Too many feedback requests; retry in a minute."
        )

    request_id = str(body.request_id)
    try:
        grounding = await run_in_threadpool(feedback.load_grounding, request_id)
    except redis.RedisError:
        raise HTTPException(status_code=503, detail="Feedback store unavailable.")
    if grounding is None:
        raise HTTPException(
            status_code=404,
            detail="Unknown request ID, or its answer is older than 24 hours.",
        )

    comment = (body.comment or "").strip() or None
    await run_in_threadpool(
        feedback.record, request_id, body.rating, comment, grounding
    )
    # No comment text in logs: it is untrusted and kept only in the feedback store.
    logger.info(
        json.dumps(
            {
                "event": "feedback",
                "feedback_request_id": request_id,
                "rating": body.rating,
                "has_comment": comment is not None,
            }
        )
    )
    return FeedbackResponse(status="recorded", request_id=request_id)
