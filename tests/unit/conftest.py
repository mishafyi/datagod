"""Shared fixtures: an in-process fake for every upstream, and the app client.

`upstream` swaps the shared httpx client for one on an httpx.MockTransport, so
no test touches the network: register a handler per URL prefix, inspect what
was sent in `upstream.requests`.
"""

import sys
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import clients  # noqa: E402
from app.config import cfg  # noqa: E402

API_KEY = "unit-test-key"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class FakeUpstream:
    def __init__(self) -> None:
        self.routes: list[tuple[str, Callable[[httpx.Request], httpx.Response]]] = []
        self.requests: list[httpx.Request] = []

    def add(self, url_prefix: str, handler: Callable[[httpx.Request], httpx.Response] | httpx.Response):
        """Answer requests whose URL starts with `url_prefix` (latest registration wins)."""
        fn = handler if callable(handler) else (lambda request, r=handler: r)
        self.routes.insert(0, (url_prefix, fn))

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        for prefix, fn in self.routes:
            if str(request.url).startswith(prefix):
                return fn(request)
        raise AssertionError(f"unexpected upstream request: {request.method} {request.url}")


@pytest.fixture
def upstream(monkeypatch: pytest.MonkeyPatch) -> FakeUpstream:
    fake = FakeUpstream()
    monkeypatch.setattr(clients, "_client", httpx.AsyncClient(transport=httpx.MockTransport(fake)))
    return fake


@pytest.fixture
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Make retry backoff instant; returns the list of requested sleep durations."""
    import asyncio

    slept: list[float] = []
    real_sleep = asyncio.sleep

    async def fake_sleep(seconds: float, *args, **kwargs):
        slept.append(seconds)
        await real_sleep(0)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    return slept


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch, upstream: FakeUpstream):
    """TestClient for the real app with a known API key; upstreams faked."""
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.setattr(cfg, "DATAGOD_API_KEY", API_KEY)
    with TestClient(app, headers={"X-API-Key": API_KEY}) as client:
        yield client
