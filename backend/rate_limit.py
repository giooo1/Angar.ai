"""Single source of truth for our slowapi rate limiter (WS3).

Used to throttle auth + upload endpoints at the IP layer. The
per-org-per-month quota counter (`backend.quota`) is a different layer
and stays in place — quota is about cost ceilings, rate-limit is about
abuse and brute-force.

In-process backend: matches our single-uvicorn-worker reality. When
we scale out we swap the storage to Redis.
"""

from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# A single shared limiter instance. `key_func` selects the remote IP by
# default; per-endpoint decorators can override with a different key.
limiter = Limiter(key_func=get_remote_address)


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Render the 429 response in our standard bilingual envelope so the
    frontend's `unwrapError` reads it without a special case.
    """
    detail = {
        "error": {
            "code": "RATE_LIMITED",
            "message_en": "Too many requests. Please slow down.",
            "message_ka": "ძალიან ბევრი მოთხოვნა. გთხოვთ შეანელეთ.",
        },
    }
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": detail},
    )
