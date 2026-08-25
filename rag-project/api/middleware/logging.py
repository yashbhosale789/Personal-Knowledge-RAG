import time
import uuid
import logging
import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from api.core.metrics import http_requests_total, http_request_duration_seconds


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        start_time = time.monotonic()

        request.state.request_id = request_id

        response = await call_next(request)
        latency_ms = (time.monotonic() - start_time) * 1000

        route = request.scope.get("route")
        metrics_path = route.path if route else "unmatched"

        http_requests_total.labels(
            method=request.method, path=metrics_path, status_code=response.status_code
        ).inc()

        http_request_duration_seconds.labels(
            method=request.method, path=metrics_path
        ).observe(latency_ms / 1000)

        log_record = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "latency_ms": round(latency_ms, 2),
        }

        logging.getLogger("api.access").info(json.dumps(log_record))

        response.headers["X-Request-ID"] = request_id
        return response

        # return await super().dispatch(request, call_next)
