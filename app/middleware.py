import json
from datetime import UTC, datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .config import redact

# FastAPI's auto-docs and OpenAPI spec must not be wrapped — Swagger/ReDoc parse them raw.
SKIP_PATHS = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}

# Headers recomputed for the rewritten body; every other header is carried over
# (e.g. Allow on a 405).
_BODY_HEADERS = frozenset({"content-length", "content-type"})


def _framework_message(data: object) -> str:
    """Message for a failure FastAPI produced itself (422 validation, 404 route,
    405 method, HTTPException) — those carry `detail`, not the error-dict."""
    detail = data.get("detail") if isinstance(data, dict) else None
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):  # RequestValidationError: [{"loc": [...], "msg": ...}, ...]
        parts = []
        for err in detail:
            if isinstance(err, dict):
                loc = ".".join(str(p) for p in err.get("loc", []))
                parts.append(f"{loc}: {err.get('msg')}" if loc else str(err.get("msg")))
        if parts:
            return "; ".join(parts)
    return json.dumps(data)[:300]


def envelope(path: str, data: object, status_code: int) -> tuple[dict, int]:
    """(envelope, http_status) for a JSON payload `data` the app produced for `path`.

    Error-dicts (`error: true`) map their upstream_status: 4xx passes through,
    5xx / timeout / connect-error (status 0) become 502 Bad Gateway. Any other
    payload with a status >= 400 (FastAPI's own 422/404/405) is an error too,
    keeping its status. Everything else is a success with the original status.
    """
    segments = [s for s in path.strip("/").split("/") if s]
    if isinstance(data, dict) and data.get("error") is True:
        message = redact(str(data.get("message") or "Unknown error"))
        data = {**data, "message": message}
        upstream = data.get("upstream_status")
        upstream = upstream if isinstance(upstream, int) else 0
        http_status = upstream if 400 <= upstream < 500 else 502
    elif status_code >= 400:
        message = redact(_framework_message(data))
        http_status = status_code
    else:
        message = None
        http_status = status_code
    return {
        "meta": {
            "source": segments[0] if segments else "unknown",
            "endpoint": path,
            "timestamp": datetime.now(UTC).isoformat(),
            "status": "error" if message is not None else "success",
        },
        "data": data,
        "error": message,
    }, http_status


class ResponseEnvelopeMiddleware(BaseHTTPMiddleware):
    """Wraps all JSON responses in a standardized envelope."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if request.url.path in SKIP_PATHS:
            return response

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk if isinstance(chunk, bytes) else chunk.encode()

        try:
            data = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return Response(content=body, status_code=response.status_code,
                            media_type=response.media_type)

        wrapped, http_status = envelope(request.url.path, data, response.status_code)
        out = Response(content=json.dumps(wrapped), status_code=http_status,
                       media_type="application/json")
        for key, value in response.headers.items():
            if key.lower() not in _BODY_HEADERS:
                out.headers.append(key, value)
        return out
