"""Retry-on-throttle for upstreams that rate-limit bursts (tenacity).

Used by the Wayback mirror clients (cia, vault via clients/_wayback.py) and
Wikipedia. A 429/503 response is retried after the upstream's Retry-After
(capped), else the next `backoff` step. When attempts run out, `Throttled` is
raised carrying the last response, so the error-dict reports the real status.
"""

from collections.abc import Sequence

import httpx2
from tenacity import AsyncRetrying, RetryCallState, retry_if_exception_type, stop_after_attempt

from .clients import get_client

THROTTLE_STATUSES = frozenset({429, 503})


class Throttled(Exception):
    """A 429/503 that outlasted every retry; `.response` is the last one."""

    def __init__(self, response: httpx2.Response) -> None:
        super().__init__(f"{response.status_code} {response.reason_phrase} from "
                         f"{response.request.url} (throttled; retries exhausted)")
        self.response = response


def _retry_after(response: httpx2.Response, fallback: float, max_wait: float) -> float:
    try:
        return min(float(response.headers.get("retry-after", "")), max_wait)
    except ValueError:  # absent, or an HTTP-date
        return fallback


def _waiter(backoff: Sequence[float], max_wait: float):
    def wait(state: RetryCallState) -> float:
        fallback = backoff[min(state.attempt_number, len(backoff)) - 1]
        exc = state.outcome.exception() if state.outcome else None
        if isinstance(exc, Throttled):
            return _retry_after(exc.response, fallback, max_wait)
        return fallback
    return wait


async def get_with_retry(url: str, *, backoff: Sequence[float] = (2.0, 5.0),
                         max_wait: float = 20.0,
                         retry_on: tuple[type[BaseException], ...] = (),
                         **kwargs) -> httpx2.Response:
    """GET `url`, retrying up to len(backoff) times on 429/503 and on any
    `retry_on` exception. Returns the first non-throttled response (any status);
    raises `Throttled` or the last exception once retries are exhausted."""
    async for attempt in AsyncRetrying(retry=retry_if_exception_type((Throttled, *retry_on)),
                                       stop=stop_after_attempt(len(backoff) + 1),
                                       wait=_waiter(backoff, max_wait), reraise=True):
        with attempt:
            r = await get_client().get(url, **kwargs)
            if r.status_code in THROTTLE_STATUSES:
                raise Throttled(r)
    return r
