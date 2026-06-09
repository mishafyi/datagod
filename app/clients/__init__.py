"""Shared HTTP client and request helpers for all government API wrappers."""

import asyncio
import time
from collections import deque

import httpx

_client: httpx.AsyncClient | None = None

UpstreamJSON = dict | list


class RateLimiter:
    """Async leaky-bucket: at most `rate` acquire()s per `period` seconds."""

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


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=30.0)
    return _client


def _error(source: str, exc: BaseException) -> dict:
    upstream_status = getattr(getattr(exc, "response", None), "status_code", 0)
    return {"error": True, "source": source,
            "upstream_status": upstream_status, "message": str(exc)}


async def safe_get(url: str, source: str, **kwargs) -> UpstreamJSON:
    """GET `url`; return upstream JSON or the error-dict contract on failure."""
    try:
        r = await get_client().get(url, **kwargs)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return _error(source, exc)


async def safe_post(url: str, source: str, **kwargs) -> UpstreamJSON:
    """POST `url`; return upstream JSON or the error-dict contract on failure."""
    try:
        r = await get_client().post(url, **kwargs)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return _error(source, exc)
