import json
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# FastAPI's auto-docs and OpenAPI spec must not be wrapped — Swagger/ReDoc parse them raw.
SKIP_PATHS = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}


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

        segments = [s for s in request.url.path.strip("/").split("/") if s]
        source = segments[0] if segments else "unknown"

        has_error = isinstance(data, dict) and data.get("error") is True
        envelope = {
            "meta": {
                "source": source,
                "endpoint": request.url.path,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error" if has_error else "success",
            },
            "data": data,
            "error": data.get("message", "Unknown error") if has_error else None,
        }

        # Upstream client error (404, 400, etc.) → pass through.
        # Upstream 5xx, timeout, connect-error (status=0) → 502 Bad Gateway.
        # No upstream error → keep original status.
        if has_error:
            upstream = data.get("upstream_status") or 0
            http_status = upstream if 400 <= upstream < 500 else 502
        else:
            http_status = response.status_code

        return Response(
            content=json.dumps(envelope),
            status_code=http_status,
            media_type="application/json",
        )
