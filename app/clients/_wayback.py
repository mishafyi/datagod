"""Shared Wayback Machine access for origins that wall out server-side clients.

cia.gov and vault.fbi.gov sit behind TLS-fingerprinting bot protection (Akamai):
every server-side HTTP client gets an infinite 302 loop or a flat 403 regardless
of headers. The Internet Archive's crawlers DO pass, so these clients read
web.archive.org's captures instead and cite the canonical URLs.

Two failure modes make "latest capture" naive (both seen live 2026-08):
recent captures can be stored 403s, and some "200" captures are actually the
~2-6KB Akamai bm-verify interstitial. fetch_capture() CDX-lists recent
status-200 captures with payload sizes, walks newest-first among ones big
enough to be a real page, and skips interstitials. Captures fetched with the
`id_` flag are original bytes — sometimes stored gzip-compressed with no
Content-Encoding header (vault.fbi.gov), so the body is gunzipped manually.
"""

import asyncio
import gzip

from . import get_client

WAYBACK = "https://web.archive.org/web"
CDX = "https://web.archive.org/cdx/search/cdx"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
RETRIES = (2.0, 5.0)  # backoff sleeps after wayback 429/503 throttling


async def retrying_get(url: str, **kwargs):
    """GET with backoff on wayback throttling (429/503) and timeouts."""
    last_exc: Exception | None = None
    for attempt in range(len(RETRIES) + 1):
        try:
            r = await get_client().get(url, headers=HEADERS, timeout=60.0, **kwargs)
            if r.status_code in (429, 503):
                raise Exception(f"wayback throttled ({r.status_code})")
            return r
        except Exception as exc:
            last_exc = exc
            if attempt < len(RETRIES):
                await asyncio.sleep(RETRIES[attempt])
    raise last_exc  # type: ignore[misc]


def _decode(r) -> str:
    """Capture body as text; id_ captures may be raw gzip with no header."""
    raw: bytes = r.content
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw.decode("utf-8", "replace")


async def fetch_capture(url: str, min_bytes: int = 8000,
                        ) -> tuple[str | None, str | None, dict | None]:
    """(html, snapshot_url, error_dict_fields). Newest usable capture of `url`.

    error_dict_fields is {"upstream_status", "message"} — the caller wraps it
    with its own source name.
    """
    try:
        cdx = await retrying_get(CDX, params={"url": url, "output": "json",
                                              "filter": "statuscode:200", "limit": "-10"})
        rows = cdx.json() if cdx.status_code == 200 and cdx.text.strip() else []
        # rows[0] is the header: [urlkey, timestamp, original, mimetype, statuscode, digest, length]
        real = [r for r in rows[1:] if str(r[6]).isdigit() and int(r[6]) > min_bytes // 4]
        if not real:
            return None, None, {"upstream_status": 404,
                                "message": f"No usable wayback capture of {url}"}
        for row in reversed(real[-3:]):  # newest first, at most 3 fetches
            snapshot = f"{WAYBACK}/{row[1]}id_/{url}"
            r = await retrying_get(snapshot, follow_redirects=True)
            if r.status_code != 200:
                continue
            html = _decode(r)
            if "bm-verify" in html[:2000] or len(html) < min_bytes // 2:
                continue
            return html, snapshot, None
        return None, None, {"upstream_status": 404,
                            "message": f"Only interstitial captures of {url}"}
    except Exception as exc:
        status = getattr(getattr(exc, "response", None), "status_code", 0)
        return None, None, {"upstream_status": status, "message": str(exc)}
