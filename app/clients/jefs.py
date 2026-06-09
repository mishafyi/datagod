"""JEFS — Judicial Financial Disclosures (pub.jefs.uscourts.gov).

There is no public REST API. The site is session-based, reCAPTCHA-protected,
30-min idle timeout. Federal judges file annual financial disclosures here.

Architecture:
- `register(name, occupation, address)` — uses Playwright (headed) to complete
  the user-agreement form + solve reCAPTCHA, then captures the session cookie
- `search(query, ...)` — POST to /index.php?action=search using the session
- `get_facets()` — POST returns filter dropdowns (years, courts, positions)
- `download(filing_ids)` — GET to /index.php?action=download returns ZIP

The Playwright step is interactive — a browser window opens, user solves
reCAPTCHA and submits the user-agreement, then the script captures the cookie.
After that, all calls go through httpx with the cookie set.

Sessions expire after 30 minutes of idle.

USAGE NOTE: JEFS requires users to provide their real name, occupation, and
address under penalty of perjury for every session. This module exposes the
plumbing; the user must explicitly supply real credentials at registration.
"""

import asyncio
from typing import Any
from urllib.parse import urlencode

import httpx

from . import UpstreamJSON

BASE = "https://pub.jefs.uscourts.gov"
INDEX = f"{BASE}/index.php"


class JEFSSession:
    """In-process JEFS session holder. One per server, refreshed every ~25 min."""

    def __init__(self) -> None:
        self._cookies: dict[str, str] = {}
        self._client: httpx.AsyncClient | None = None
        self._lock = asyncio.Lock()

    def is_registered(self) -> bool:
        return bool(self._cookies)

    async def register_via_playwright(self, name: str, occupation: str,
                                       address: str, headed: bool = True) -> None:
        """Run Playwright to complete the user-agreement form + reCAPTCHA.
        Headed by default so the user can solve the reCAPTCHA manually."""
        try:
            from playwright.async_api import async_playwright
        except ImportError as e:
            raise RuntimeError("Playwright not installed; run `pip install playwright && playwright install chromium`") from e

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=not headed)
            ctx = await browser.new_context()
            page = await ctx.new_page()
            await page.goto(f"{BASE}/")

            # Fill the user-agreement form (selectors derived from JEFS DOM —
            # adjust if the site changes)
            await page.fill('input[name="name"]', name)
            await page.fill('input[name="occupation"]', occupation)
            await page.fill('input[name="address"]', address)

            # User solves reCAPTCHA manually in the headed browser; we wait
            # until they submit. The submit button's selector or form_id may
            # vary — adjust per site state.
            await page.wait_for_url(lambda url: "search" in url or "results" in url,
                                     timeout=300_000)  # 5 min for human

            # Capture cookies
            cookies = await ctx.cookies()
            self._cookies = {c["name"]: c["value"] for c in cookies if BASE in f"https://{c['domain']}"}
            await browser.close()

        if not self._cookies:
            raise RuntimeError("JEFS registration completed but no cookies captured")

    async def _client_for_session(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=BASE,
                cookies=self._cookies,
                timeout=30.0,
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
        return self._client

    async def search(self, query: str = "", facets: dict | None = None,
                     sort_by: str = "published_dt", sort_dir: str = "desc",
                     start: int = 0, page_size: int = 25) -> UpstreamJSON:
        """Search filings. `facets` is a dict like {'operating_year_s': ['2023', '2024']}."""
        async with self._lock:
            if not self.is_registered():
                return {"error": True, "source": "jefs", "upstream_status": 401,
                        "message": "JEFS session not registered — call register_via_playwright() first"}
            client = await self._client_for_session()
            import json as _json
            payload = {
                "action": "search",
                "q": query,
                "facet_string": _json.dumps(facets or {}),
                "sort_by": sort_by,
                "sort_dir": sort_dir,
                "start": str(start),
                "page_size": str(page_size),
            }
            try:
                r = await client.post("/index.php", data=payload)
                r.raise_for_status()
                return r.json()
            except Exception as exc:
                upstream_status = getattr(getattr(exc, "response", None), "status_code", 0)
                return {"error": True, "source": "jefs",
                        "upstream_status": upstream_status, "message": str(exc)}

    async def get_facets(self) -> UpstreamJSON:
        """Return filter dropdown options (years, courts, positions, report types)."""
        async with self._lock:
            if not self.is_registered():
                return {"error": True, "source": "jefs", "upstream_status": 401,
                        "message": "JEFS session not registered"}
            client = await self._client_for_session()
            try:
                r = await client.post("/index.php", data={"action": "get_facets"})
                r.raise_for_status()
                return r.json()
            except Exception as exc:
                upstream_status = getattr(getattr(exc, "response", None), "status_code", 0)
                return {"error": True, "source": "jefs",
                        "upstream_status": upstream_status, "message": str(exc)}

    async def download(self, filing_ids: list[str]) -> bytes | dict:
        """Download selected filings as a ZIP. Max 100 at a time per JEFS limit.
        Returns raw ZIP bytes on success, or error dict on failure."""
        async with self._lock:
            if not self.is_registered():
                return {"error": True, "source": "jefs", "upstream_status": 401,
                        "message": "JEFS session not registered"}
            if len(filing_ids) > 100:
                return {"error": True, "source": "jefs", "upstream_status": 400,
                        "message": "JEFS download limit: 100 filings per call"}
            client = await self._client_for_session()
            try:
                # Step 1: add each filing to download queue
                for fid in filing_ids:
                    await client.post("/index.php", data={"action": "add", "id": fid})
                # Step 2: trigger download
                r = await client.get("/index.php", params={"action": "download"})
                r.raise_for_status()
                return r.content
            except Exception as exc:
                upstream_status = getattr(getattr(exc, "response", None), "status_code", 0)
                return {"error": True, "source": "jefs",
                        "upstream_status": upstream_status, "message": str(exc)}

    async def reset(self) -> None:
        """Clear session — must re-register before next call."""
        async with self._lock:
            if self._client is not None:
                try:
                    await self._client.post("/index.php", data={"action": "reset"})
                except Exception:
                    pass
                await self._client.aclose()
                self._client = None
            self._cookies = {}


# Process-singleton (one session per server process)
_session = JEFSSession()


def get_session() -> JEFSSession:
    return _session


async def register(name: str, occupation: str, address: str, headed: bool = True) -> UpstreamJSON:
    """Convenience wrapper: register the singleton session."""
    try:
        await _session.register_via_playwright(name, occupation, address, headed=headed)
        return {"registered": True, "cookies_captured": len(_session._cookies)}
    except Exception as exc:
        return {"error": True, "source": "jefs", "upstream_status": 0, "message": str(exc)}


async def search(query: str = "", facets: dict | None = None,
                 sort_by: str = "published_dt", sort_dir: str = "desc",
                 start: int = 0) -> UpstreamJSON:
    return await _session.search(query, facets, sort_by, sort_dir, start)


async def get_facets() -> UpstreamJSON:
    return await _session.get_facets()


async def download(filing_ids: list[str]) -> bytes | dict:
    return await _session.download(filing_ids)


async def reset() -> UpstreamJSON:
    await _session.reset()
    return {"reset": True}
