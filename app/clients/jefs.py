"""JEFS — Judicial Financial Disclosures (pub.jefs.uscourts.gov).

There is no public REST API. The site is session-based, reCAPTCHA-protected,
30-min idle timeout. Federal judges file annual financial disclosures here.

Architecture:
- `register(name, occupation, email, phone, address…)` — uses Playwright (headed)
  to fill the registration form (#registration-form), then the human solves the
  invisible reCAPTCHA + clicks "Enter Database"; the authorized cookie is captured
- `search(query, ...)` — POST to /index.php?action=search using the session
- `get_facets()` — POST returns filter dropdowns (years, courts, positions)
- `download(filing_ids)` — GET to /index.php?action=download returns ZIP

The Playwright step is interactive — a browser window opens, the human solves
reCAPTCHA and submits the registration form; on success JEFS closes the dialog
and reloads "/", and the script captures the now-authorized cookies. After that,
all calls go through httpx with the cookies set.

Because it needs a visible browser + a human-solved reCAPTCHA, registration only
works where someone can see the window — it cannot run on a headless server.
Sessions expire after 30 minutes of idle.

USAGE NOTE: JEFS requires users to provide their real name, occupation, email,
phone, and mailing address, and to certify under penalty of perjury (28 U.S.C.
§ 1746) for every session. This module exposes the plumbing; the user must
explicitly supply real credentials at registration.
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

    async def register_via_playwright(self, name: str, occupation: str, email: str,
                                       phone: str, address_line1: str, address_line2: str,
                                       city: str, state: str, postalcode: str,
                                       representing: str, representing_address: str,
                                       headed: bool) -> None:
        """Fill the live JEFS registration form with Playwright, then hand off to the
        human to solve the invisible reCAPTCHA and click "Enter Database".

        The form lives in the #register-dialog (opened by the "Begin Registration"
        button) as #registration-form. On a successful POST the site's own JS runs
        `Metro.dialog.close('#register-dialog'); location.href = "/"` — so the success
        signal is the registration form disappearing, after which we capture the
        now-authorized cookies (including the F5/TS WAF cookies, which must be sent
        back on later requests). Selectors verified against the live DOM 2026-06-10.

        Headed by default so the human can solve the reCAPTCHA; this cannot run on a
        headless server."""
        try:
            from playwright.async_api import async_playwright
        except ImportError as e:
            raise RuntimeError("Playwright not installed; run `.venv/bin/pip install playwright && .venv/bin/playwright install chromium`") from e

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=not headed)
            ctx = await browser.new_context()
            page = await ctx.new_page()
            await page.goto(f"{BASE}/")

            # Open the registration dialog so its inputs become visible/fillable.
            await page.click("#register-btn")
            await page.wait_for_selector("#registration-form", state="visible", timeout=15_000)

            # Fill the form. JEFS splits the mailing address into five inputs — there
            # is no single name="address" field.
            await page.fill('input[name="name"]', name)
            await page.fill('input[name="occupation"]', occupation)
            await page.fill('input[name="email"]', email)
            await page.fill('input[name="phone"]', phone)
            await page.fill('input[name="address-line-1"]', address_line1)
            if address_line2:
                await page.fill('input[name="address-line-2"]', address_line2)
            await page.fill('input[name="address-city"]', city)
            await page.fill('input[name="address-state"]', state)
            await page.fill('input[name="address-postalcode"]', postalcode)

            # "Requesting on Behalf of" is required. The site's handleUser() toggle runs
            # on blur (not on fill), so blur after filling: entering "Self" (or blank)
            # hides the mailing-address sub-field, any other entity reveals it (slideDown)
            # and makes it required — so fill that only in the non-Self case.
            await page.fill('input[name="representing"]', representing)
            await page.locator('input[name="representing"]').blur()
            if representing.strip().lower() not in ("", "self") and representing_address:
                await page.fill('input[name="representing-address"]', representing_address)

            # Tick "I certify under penalty of perjury … (28 U.S.C. § 1746)." The Metro
            # UI hides the real <input> behind a styled control, so check it by force.
            await page.check('input[name="certified"]', force=True)

            # Hand off: the human clicks "Enter Database", the invisible reCAPTCHA runs,
            # and on success JEFS closes the dialog + reloads "/". Wait (up to 5 min) for
            # the form to disappear — that, not a URL change, is the real success signal.
            await page.wait_for_selector("#registration-form", state="hidden", timeout=300_000)

            cookies = await ctx.cookies()
            self._cookies = {c["name"]: c["value"] for c in cookies}
            await browser.close()

        if not self._cookies:
            raise RuntimeError("JEFS registration finished but no session cookie was captured")

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


async def register(name: str, occupation: str, email: str, phone: str,
                   address_line1: str, address_line2: str, city: str, state: str,
                   postalcode: str, representing: str, representing_address: str,
                   headed: bool) -> UpstreamJSON:
    """Convenience wrapper: register the singleton session, then probe it so the
    caller gets real evidence the session is authorized."""
    try:
        await _session.register_via_playwright(name, occupation, email, phone,
                                               address_line1, address_line2, city,
                                               state, postalcode, representing,
                                               representing_address, headed=headed)
        facets = await _session.get_facets()
        ok = not (isinstance(facets, dict) and facets.get("error"))
        return {"registered": ok, "cookies_captured": len(_session._cookies),
                "session_check": "get_facets returned data" if ok else facets}
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
