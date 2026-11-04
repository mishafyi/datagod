"""The tenacity retry-on-throttle policy shared by Wayback (cia/vault) and Wikipedia."""

import httpx2
import pytest

from app.clients import _wayback, wikipedia
from app.resilience import Throttled, get_with_retry

pytestmark = pytest.mark.anyio

URL = "https://throttled.example/api"


def _sequence(*responses):
    it = iter(responses)
    return lambda request: next(it)


async def test_retries_throttling_then_returns_success(upstream, no_sleep):
    upstream.add(URL, _sequence(httpx2.Response(429), httpx2.Response(503), httpx2.Response(200, json={"ok": 1})))
    r = await get_with_retry(URL)
    assert r.status_code == 200 and len(upstream.requests) == 3
    assert no_sleep == [2.0, 5.0]


async def test_honors_retry_after_and_caps_it(upstream, no_sleep):
    upstream.add(URL, _sequence(httpx2.Response(429, headers={"Retry-After": "7"}),
                                httpx2.Response(429, headers={"Retry-After": "999"}),
                                httpx2.Response(200)))
    await get_with_retry(URL, max_wait=20.0)
    assert no_sleep == [7.0, 20.0]


async def test_exhausted_retries_raise_throttled_with_last_response(upstream, no_sleep):
    upstream.add(URL, httpx2.Response(429))
    with pytest.raises(Throttled) as info:
        await get_with_retry(URL)
    assert info.value.response.status_code == 429 and len(upstream.requests) == 3


async def test_non_throttle_errors_are_returned_not_retried(upstream, no_sleep):
    upstream.add(URL, httpx2.Response(404))
    assert (await get_with_retry(URL)).status_code == 404
    assert len(upstream.requests) == 1 and no_sleep == []


async def test_transport_errors_retry_only_when_asked(upstream, no_sleep):
    calls: list[int] = []

    def flaky(request):
        calls.append(1)
        if len(calls) < 3:
            raise httpx2.ConnectTimeout("slow", request=request)
        return httpx2.Response(200)

    upstream.add(URL, flaky)
    assert (await get_with_retry(URL, retry_on=(httpx2.TransportError,))).status_code == 200
    upstream.add(URL, lambda request: (_ for _ in ()).throw(httpx2.ConnectTimeout("slow", request=request)))
    with pytest.raises(httpx2.ConnectTimeout):
        await get_with_retry(URL)


async def test_wikipedia_reports_the_real_throttle_status(upstream, no_sleep):
    upstream.add("https://en.wikipedia.org/", httpx2.Response(429))
    err = await wikipedia.summary("Albert_Einstein")
    assert err["error"] is True and err["upstream_status"] == 429
    assert no_sleep == [2.0, 5.0]


async def test_wayback_throttle_surfaces_429_not_0(upstream, no_sleep):
    upstream.add("https://web.archive.org/", httpx2.Response(429))
    html, snapshot, err = await _wayback.fetch_capture("https://www.cia.gov/readingroom/x")
    assert html is None and err["upstream_status"] == 429
