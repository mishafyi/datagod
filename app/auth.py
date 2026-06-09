"""API-key authentication for DataGod's own endpoints.

Uses FastAPI's built-in ``APIKeyHeader`` security scheme — industry standard, no
extra dependency. Every route is gated by ``require_api_key`` via the app-level
``dependencies`` in ``main.py``; the only exceptions are ``PUBLIC_PATHS`` and
FastAPI's own docs routes (``/docs``, ``/redoc``, ``/openapi.json``), which are
not subject to app-level dependencies.
"""

import secrets

from fastapi import Request, Security
from fastapi.security import APIKeyHeader

from .config import cfg

# Paths reachable without an API key (liveness probe for Coolify / uptime checks).
PUBLIC_PATHS = frozenset({"/health"})

# auto_error=False → returns None when the header is absent, so we raise our own
# error and keep "missing" and "wrong" indistinguishable to the caller.
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


class UnauthorizedError(Exception):
    """Raised when a request lacks a valid API key; rendered as a 401 error envelope."""


async def require_api_key(
    request: Request,
    provided_key: str | None = Security(API_KEY_HEADER),
) -> None:
    """Reject any request without a valid ``X-API-Key`` header.

    Lets ``PUBLIC_PATHS`` through untouched. Otherwise compares the supplied key
    against ``cfg.DATAGOD_API_KEY`` in constant time and raises
    ``UnauthorizedError`` on a missing or mismatched key. Fails closed: if no
    server key is configured, every gated request is rejected.
    """
    if request.url.path in PUBLIC_PATHS:
        return
    expected = cfg.DATAGOD_API_KEY
    if not expected:
        raise UnauthorizedError("Server API key not configured")
    if provided_key is None or not secrets.compare_digest(provided_key, expected):
        raise UnauthorizedError("Invalid or missing API key")
