"""Shared HTTP client and request helpers for all upstream API wrappers."""

import asyncio
import re
import time
from collections import deque

import httpx

from ..config import redact

_client: httpx.AsyncClient | None = None

UpstreamJSON = dict | list

# How much of an upstream's error body an error message quotes.
_DETAIL_CAP = 300


class RateLimiter:
    """Async sliding-window limiter: at most `rate` acquire()s in any `period` seconds.

    Kept hand-rolled on purpose: library token/leaky buckets (aiolimiter) allow a
    full burst on top of the steady rate, i.e. up to ~2x `rate` inside one window —
    too loose for SEC's 10 req/s fair-access rule.
    """

    def __init__(self, rate: int, period: float = 1.0) -> None:
        self._rate = rate
        self._period = period
        self._stamps: deque[float] = deque(maxlen=rate)
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            if len(self._stamps) == self._rate:
                wait = self._period - (time.monotonic() - self._stamps[0])
                if wait > 0:
                    await asyncio.sleep(wait)
            self._stamps.append(time.monotonic())


def clean_text(s: str | None) -> str | None:
    """Collapse whitespace runs to single spaces; None for empty/whitespace-only text."""
    return re.sub(r"\s+", " ", s).strip() or None if s else None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=30.0)
    return _client


def error_dict(source: str, upstream_status: int, message: str) -> dict:
    """The error-dict contract, with credentials redacted from `message`."""
    return {"error": True, "source": source,
            "upstream_status": upstream_status, "message": redact(message)}


def _describe(exc: BaseException) -> str:
    """Caller-facing text for `exc`: status + URL for HTTP errors, plus the start
    of the upstream's own error body when it is JSON/text (not an HTML page)."""
    if isinstance(exc, httpx.HTTPStatusError):
        r = exc.response
        message = f"{r.status_code} {r.reason_phrase} from {r.request.url}"
        ctype = r.headers.get("content-type", "")
        if "json" in ctype or ctype.startswith("text/plain"):
            detail = " ".join(r.text[:2000].split())[:_DETAIL_CAP]
            if detail:
                message += f": {detail}"
        return message
    if isinstance(exc, httpx.RequestError):
        try:
            where = f" for {exc.request.url}"
        except RuntimeError:  # request not attached
            where = ""
        return f"{type(exc).__name__}{where}" + (f": {exc}" if str(exc) else "")
    return str(exc) or type(exc).__name__


def _error(source: str, exc: BaseException) -> dict:
    """The error-dict for an exception raised while calling `source`."""
    upstream_status = getattr(getattr(exc, "response", None), "status_code", 0)
    return error_dict(source, upstream_status, _describe(exc))


def json_or_error(r: httpx.Response, source: str) -> UpstreamJSON:
    """`r`'s JSON body, or the error-dict when it isn't JSON (e.g. an HTML
    error/SPA page served with a 200)."""
    try:
        return r.json()
    except ValueError:
        return error_dict(source, 0, f"Non-JSON response "
                                     f"({r.headers.get('content-type') or 'no content-type'}) "
                                     f"from {r.request.url}")


async def _safe_request(method: str, url: str, source: str, **kwargs) -> UpstreamJSON:
    try:
        r = await get_client().request(method, url, **kwargs)
        r.raise_for_status()
    except Exception as exc:
        return _error(source, exc)
    return json_or_error(r, source)


async def safe_get(url: str, source: str, **kwargs) -> UpstreamJSON:
    """GET `url`; return upstream JSON or the error-dict contract on failure."""
    return await _safe_request("GET", url, source, **kwargs)


async def safe_post(url: str, source: str, **kwargs) -> UpstreamJSON:
    """POST `url`; return upstream JSON or the error-dict contract on failure."""
    return await _safe_request("POST", url, source, **kwargs)
