"""
Per-client, per-instance rate limiting (sliding window, in memory).

Keyed on the client IP. Behind Firebase Hosting / Cloud Run the client is the
first X-Forwarded-For hop; that header can be forged, so treat this as abuse
damping (stop a script hammering Gemini or the optimiser), not as security.
"""

from __future__ import annotations

import re
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# (path regex, requests per minute). First match wins; unmatched paths use DEFAULT.
EXPENSIVE = [
    (re.compile(r"^/api/fpl-team/\d+/briefing$"), 20),   # Gemini (cached per team; IPs are often shared via carrier NAT)
    (re.compile(r"^/api/teams/optimize$"), 20),          # MILP solve
    (re.compile(r"^/api/fpl-team/\d+(/transfers)?$"), 30),  # 2 upstream FPL calls each
    (re.compile(r"^/api/payments/"), 20),
]
DEFAULT_PER_MIN = 240
EXEMPT = {"/health", "/ping", "/api/payments/webhook"}  # probes + PayFast's servers
_MAX_CLIENTS = 20_000


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def reset(self) -> None:
        self._hits.clear()

    def check(self, client: str, bucket: str, limit: int, now: float | None = None) -> float:
        """Record a hit. Returns 0 if allowed, else seconds until a slot frees up."""
        now = time.monotonic() if now is None else now
        if len(self._hits) > _MAX_CLIENTS:  # crude memory bound under a flood
            self._hits.clear()
        q = self._hits[(client, bucket)]
        while q and now - q[0] >= 60:
            q.popleft()
        if len(q) >= limit:
            return 60 - (now - q[0])
        q.append(now)
        return 0.0


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


limiter = RateLimiter()  # process-wide; tests reset it via limiter.reset()


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limiter: RateLimiter = limiter):
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in EXEMPT or request.method == "OPTIONS":
            return await call_next(request)
        bucket, limit = "default", DEFAULT_PER_MIN
        for pattern, per_min in EXPENSIVE:
            if pattern.match(path):
                bucket, limit = pattern.pattern, per_min
                break
        retry = self.limiter.check(client_ip(request), bucket, limit)
        if retry:
            return JSONResponse(
                {"detail": "Too many requests — please wait a moment and try again."},
                status_code=429,
                headers={"Retry-After": str(int(retry) + 1)},
            )
        return await call_next(request)
