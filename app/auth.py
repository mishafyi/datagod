"""Authentication for DataGod: API-key for data routes, HTTP Basic for the docs.

Data routes are gated by ``require_api_key`` (FastAPI's built-in ``APIKeyHeader``),
wired as an app-level dependency in ``main.py``. The interactive docs
(``/docs``, ``/redoc``, ``/openapi.json``) are instead protected by HTTP Basic
(``require_docs_auth``) — a browser navigating to those pages can't supply a
header-based API key, so Basic auth (a login prompt) is the right tool there.
Both ``PUBLIC_PATHS`` and ``DOCS_PATHS`` are exempt from the API-key check.
"""

import secrets

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader, HTTPBasic, HTTPBasicCredentials

from .config import cfg

# Reachable with no auth at all (liveness probe for Coolify / uptime monitors).
PUBLIC_PATHS = frozenset({"/health"})

# Served by custom routes guarded with HTTP Basic (require_docs_auth) — exempt
# from the X-API-Key check, but NOT public.
DOCS_PATHS = frozenset({"/docs", "/redoc", "/openapi.json"})

# auto_error=False → returns None when the header is absent, so we raise our own
# error and keep "missing" and "wrong" indistinguishable to the caller.
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

DOCS_BASIC = HTTPBasic(auto_error=True)


class UnauthorizedError(Exception):
    """Raised when a request lacks a valid API key; rendered as a 401 error envelope."""


async def require_api_key(
    request: Request,
    provided_key: str | None = Security(API_KEY_HEADER),
) -> None:
    """Reject any request without a valid ``X-API-Key`` header.

    Lets ``PUBLIC_PATHS`` and ``DOCS_PATHS`` through (the latter are guarded
    separately by HTTP Basic). Otherwise compares the supplied key against
    ``cfg.DATAGOD_API_KEY`` in constant time and raises ``UnauthorizedError`` on
    a missing or mismatched key. Fails closed when no server key is configured.
    """
    if request.url.path in PUBLIC_PATHS or request.url.path in DOCS_PATHS:
        return
    expected = cfg.DATAGOD_API_KEY
    if not expected:
        raise UnauthorizedError("Server API key not configured")
    if provided_key is None or not secrets.compare_digest(provided_key, expected):
        raise UnauthorizedError("Invalid or missing API key")


def require_docs_auth(credentials: HTTPBasicCredentials = Depends(DOCS_BASIC)) -> str:
    """HTTP Basic gate for the interactive docs.

    Username defaults to ``cfg.DATAGOD_DOCS_USER``; the password is
    ``cfg.DATAGOD_DOCS_PASSWORD`` when set, otherwise falls back to
    ``cfg.DATAGOD_API_KEY`` so the docs are protected out of the box. Fails
    closed (503) when no password is available at all.
    """
    expected_user = cfg.DATAGOD_DOCS_USER or "datagod"
    expected_password = cfg.DATAGOD_DOCS_PASSWORD or cfg.DATAGOD_API_KEY
    if not expected_password:
        raise HTTPException(status_code=503, detail="Docs authentication is not configured")
    user_ok = secrets.compare_digest(credentials.username, expected_user)
    pass_ok = secrets.compare_digest(credentials.password, expected_password)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=401,
            detail="Invalid docs credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
