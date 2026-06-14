from __future__ import annotations

from collections import defaultdict, deque
from time import monotonic

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.requests: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        if request.url.path in {"/health", "/docs", "/openapi.json"}:
            return await call_next(request)
        now = monotonic()
        key = request.client.host if request.client else "unknown"
        history = self.requests[key]
        while history and history[0] <= now - 60:
            history.popleft()
        if len(history) >= settings.rate_limit_per_minute:
            return JSONResponse({"detail": "Rate limit exceeded. Try again shortly."}, status_code=429)
        history.append(now)
        return await call_next(request)
