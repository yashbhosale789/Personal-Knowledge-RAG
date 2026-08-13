import time
import uuid
import logging
import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        start_time = time.monotonic()

        request.state.request_id = request_id

        response = await call_next(request)
        latency_ms = (time.monotonic() - start_time) * 1000

        log_record = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "latency_ms": round(latency_ms, 2)
        }

        logging.getLogger("api.access").info(json.dump(log_record))

        response.headers["X-Request-ID"] = request_id
        return response

        # return await super().dispatch(request, call_next)