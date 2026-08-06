"""CIA FOIA Electronic Reading Room — served through the Wayback Machine mirror.

cia.gov sits behind TLS-fingerprinting bot protection (Akamai): every server-side
HTTP client gets an infinite 302 loop regardless of headers (verified 2026-08-06),
so the reading room cannot be scraped directly. The Internet Archive's crawlers
DO pass, and web.archive.org mirrors the reading room thoroughly — so this client
reads the archive's latest capture of each page and returns the CANONICAL
cia.gov URLs for citation alongside the archived ones.

Consequences to be honest about:
- content is as fresh as the last crawl (usually days-weeks old, fine for a
  reading room whose corpus is decades old);
- there is no full-text search endpoint — cia.gov search pages aren't archived
  per-query. Browse the curated collections (`collections()` → `collection()`)
  or arrive with a document path from another source (NSArchive, NARA, FRUS all
  cite CIA doc numbers). ponytail: revisit only if cia.gov drops the bot wall.

Wayback rate-limits aggressively (429/503); _wb_get retries with backoff.
"""

import asyncio
import re

from selectolax.parser import HTMLParser

from . import UpstreamJSON, get_client

WAYBACK = "https://web.archive.org/web"
CDX = "https://web.archive.org/cdx/search/cdx"
ORIGIN = "https://www.cia.gov/readingroom"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
BODY_CAP = 8000
RETRIES = (2.0, 5.0)  # backoff sleeps after 429/503

# Famous reading-room collections, slug → display name. Static on purpose: the
# set changes rarely and there is no listable index behind the bot wall.
COLLECTIONS = {
    "crest-25-year-program-archive": "CREST: 25-Year Program Archive",
    "stargate": "STARGATE (remote viewing)",
    "ufos-fact-or-fiction": "UFOs: Fact or Fiction?",
    "bay-pigs-release": "Bay of Pigs Release",
    "argentina-declassification-project-dirty-war-1976-83": "Argentina Declassification Project",
    "creating-intelligence-community-founding-documents": "Founding Documents of the IC",
    "presidents-daily-brief-1961-1969": "President's Daily Brief 1961-1969",
    "presidents-daily-brief-1969-1977": "President's Daily Brief 1969-1977",
    "vietnam-histories": "Vietnam Histories",
    "berlin-tunnel": "The Berlin Tunnel",
    "intelligence-warning-soviet-invasion-czechoslovakia": "Soviet Invasion of Czechoslovakia",
}


def _err(status: int, message: str) -> dict:
    return {"error": True, "source": "cia", "upstream_status": status, "message": message}


def _clean(s: str | None) -> str | None:
    return re.sub(r"\s+", " ", s).strip() if s else None


def _unwrap(archived_href: str) -> str:
    """Original URL from a wayback-rewritten href (/web/{ts}(id_)?/{original})."""
    m = re.match(r"^(?:https?://web\.archive\.org)?/web/[^/]+/(https?://.+)$", archived_href)
    return m.group(1) if m else archived_href


async def _retrying(url: str, **kwargs) -> "object":
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


async def _wb_get(path: str) -> tuple[str | None, str | None, dict | None]:
    """(html, snapshot_url, error). Newest USABLE capture of ORIGIN/path.

    The naive "latest capture" fails two ways here (both seen live 2026-08-06):
    recent captures are stored 403s (cia.gov walls the archive's crawler now),
    and some "200" captures are actually Akamai's ~2KB bm-verify interstitial.
    So: CDX lists the last 10 status-200 captures with payload sizes, and we
    fetch newest-first among captures big enough to be a real page, skipping
    any that still smell like the interstitial. `id_` = original bytes."""
    clean = path.split("?", 1)[0]
    query = ("?" + path.split("?", 1)[1]) if "?" in path else ""
    try:
        cdx = await _retrying(CDX,
                              params={"url": f"{ORIGIN}/{clean}{query}", "output": "json",
                                      "filter": "statuscode:200", "limit": "-10"})
        rows = cdx.json() if cdx.status_code == 200 and cdx.text.strip() else []
        # rows[0] is the header: [urlkey, timestamp, original, mimetype, statuscode, digest, length]
        real = [r for r in rows[1:] if str(r[6]).isdigit() and int(r[6]) > 8000]
        if not real:
            return None, None, _err(404, f"No usable wayback capture of {ORIGIN}/{path}")
        for row in reversed(real[-3:]):  # newest first, at most 3 fetches
            snapshot = f"{WAYBACK}/{row[1]}id_/{ORIGIN}/{path}"
            r = await _retrying(snapshot, follow_redirects=True)
            if r.status_code != 200 or "bm-verify" in r.text[:2000]:
                continue
            return r.text, snapshot, None
        return None, None, _err(404, f"Only interstitial captures of {ORIGIN}/{path}")
    except Exception as exc:
        status = getattr(getattr(exc, "response", None), "status_code", 0)
        return None, None, _err(status, str(exc))


def _doc_links(t: HTMLParser) -> list[dict]:
    """Every /readingroom/document/ link in a page, deduped, canonical URLs."""
    seen: set[str] = set()
    out: list[dict] = []
    for a in t.css("a[href*='/readingroom/document/']"):
        href = _unwrap(a.attributes.get("href", ""))
        m = re.search(r"/readingroom/document/([^/?#]+)", href)
        title = _clean(a.text())
        if not m or m.group(1) in seen or not title:
            continue
        seen.add(m.group(1))
        out.append({"path": m.group(1), "title": title,
                    "url": f"{ORIGIN}/document/{m.group(1)}"})
    return out


async def document(doc_path: str) -> UpstreamJSON:
    """One reading-room document by its path segment (e.g.
    'cia-rdp96-00788r001700210016-5'): title, field metadata, body text and the
    PDF (original + archived URLs)."""
    html, snapshot, err = await _wb_get(f"document/{doc_path}")
    if err:
        return err
    t = HTMLParser(html)
    title = _clean(t.css_first("h1").text()) if t.css_first("h1") else None
    meta: dict[str, str] = {}
    for f in t.css(".field"):
        label = f.css_first(".field-label")
        item = f.css_first(".field-item")
        if label and item:
            key = _clean(label.text()).rstrip(": ").lower().replace(" ", "_")
            val = _clean(item.text(separator=" "))
            if key and val and len(val) < 500:
                meta[key] = val
    pdf_original = pdf_archived = None
    for a in t.css("a[href]"):
        href = a.attributes.get("href", "")
        if ".pdf" in href.lower():
            pdf_archived = href if href.startswith("http") else f"https://web.archive.org{href}"
            pdf_original = _unwrap(href)
            break
    body = t.css_first(".field-name-body, #content, main")
    return {
        "path": doc_path,
        "title": title,
        "meta": meta,
        "body": (_clean(body.text(separator=" ")) or "")[:BODY_CAP] or None if body else None,
        "pdf_url": pdf_original,
        "pdf_archived_url": pdf_archived,
        "url": f"{ORIGIN}/document/{doc_path}",
        "archived_url": snapshot,
    }


async def collection(slug: str, page: int = 0) -> UpstreamJSON:
    """A reading-room collection page (see `collections()` for famous slugs):
    the collection's description and its document list. `page` forwards the
    listing pager (0-based, as the site counts)."""
    path = f"collection/{slug}" + (f"?page={page}" if page else "")
    html, snapshot, err = await _wb_get(path)
    if err:
        return err
    t = HTMLParser(html)
    title = _clean(t.css_first("h1").text()) if t.css_first("h1") else None
    desc = t.css_first(".field-name-body, .field--name-body")
    return {
        "slug": slug,
        "page": page,
        "title": title,
        "description": (_clean(desc.text(separator=" ")) or "")[:2000] or None if desc else None,
        "documents": _doc_links(t),
        "url": f"{ORIGIN}/collection/{slug}",
        "archived_url": snapshot,
    }


async def collections() -> UpstreamJSON:
    """The curated registry of famous reading-room collections (static)."""
    return {"collections": [{"slug": s, "name": n, "url": f"{ORIGIN}/collection/{s}"}
                            for s, n in COLLECTIONS.items()]}
