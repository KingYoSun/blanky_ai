import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware


logger = logging.getLogger("skill-server.request")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = uuid.uuid4().hex
        request.state.request_id = request_id
        started_at = time.perf_counter()

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - started_at) * 1000
        response.headers["x-request-id"] = request_id
        logger.info(
            "%s %s -> %s %.2fms request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            request_id,
        )
        return response
