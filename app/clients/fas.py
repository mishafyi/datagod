"""FAS Intelligence Resource Program (irp.fas.org) — HTML scrape (static site).

The Federation of American Scientists' IRP is the working mirror of the US
intelligence/military document world the official reading rooms wall off:
agency pages (NSA, CIA, DIA…), collection-program pages, official documents,
DoD directives, congressional oversight material, foreign services. Pages are
plain static HTML — many are full-text mirrors of primary documents — and the
site serves any client directly (no key, no bot wall; same scrape exception
as frus/nsarchive).

Two shapes: an INDEX page (a list of links) and a CONTENT page (text + PDFs).
`index()` and `page()` parse either; callers decide which they're on.
"""

import re
from urllib.parse import urljoin

from selectolax.parser import HTMLParser

from . import UpstreamJSON, _error, clean_text as _clean, error_dict, get_client

BASE = "https://irp.fas.org"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
TEXT_CAP = 16000

# Verified section paths (all probed 200, 2026-08-08).
SECTIONS = {
    "nsa": "NSA documents",
    "cia": "CIA documents",
    "dia": "DIA documents",
    "agency": "Agencies index",
    "program/collect": "Collection programs",
    "offdocs": "Official documents",
    "doddir": "DoD directives",
    "world": "Foreign intelligence services",
    "congress": "Congressional oversight",
    "ops": "Military operations",
}


class _NotHtml(Exception):
    """The path is a document (PDF, spreadsheet, image…), not an IRP page."""


async def _get(path: str):
    url = f"{BASE}/{path.strip('/')}"
    url += "/" if not re.search(r"\.[a-z]{3,4}$", url, re.I) else ""
    r = await get_client().get(url, headers=HEADERS, follow_redirects=True)
    r.raise_for_status()
    ctype = r.headers.get("content-type", "")
    if "html" not in ctype and not ctype.startswith("text/"):
        # Index pages link PDFs/xlsx/images; parsing those as HTML returned binary noise.
        raise _NotHtml(f"{url} is {ctype or 'not HTML'}, not an IRP page — download it directly")
    return r.text, url


def _failed(exc: Exception) -> dict:
    return error_dict("fas", 415, str(exc)) if isinstance(exc, _NotHtml) else _error("fas", exc)


async def index(path: str) -> UpstreamJSON:
    """An IRP index page: its title and every same-site content link
    (nav/parent links and anchors filtered out)."""
    try:
        html, url = await _get(path)
    except Exception as exc:
        return _failed(exc)
    t = HTMLParser(html)
    # Nav links point UP out of the section ("../index.html", fas.org); real
    # entries live at or below this directory — including child sub-indexes
    # ("uk/index.html"), which is what /world and /congress are made of.
    here = url if url.endswith("/") else url.rsplit("/", 1)[0] + "/"
    links: list[dict] = []
    seen: set[str] = set()
    for a in t.css("a[href]"):
        href = a.attributes.get("href") or ""
        title = _clean(a.text())
        if not title or href.startswith(("#", "mailto:")):
            continue
        absu = urljoin(url, href)
        if not absu.startswith(here) or absu.rstrip("/") == url.rstrip("/"):
            continue
        rel = absu[len(BASE):].lstrip("/")
        if rel in seen:
            continue
        seen.add(rel)
        links.append({"path": rel, "title": title, "url": absu,
                      "is_pdf": rel.lower().endswith(".pdf"),
                      "is_index": rel.lower().endswith(("index.html", "index.htm"))})
    h = t.css_first("h1, h2")
    return {"path": path.strip("/"), "title": _clean(h.text()) if h else None,
            "url": url, "links": links}


async def page(path: str) -> UpstreamJSON:
    """An IRP content page: title, full text (capped) and any PDF links."""
    try:
        html, url = await _get(path)
    except Exception as exc:
        return _failed(exc)
    t = HTMLParser(html)
    for kill in t.css("script, style"):
        kill.decompose()
    h = t.css_first("h1, h2")
    title_tag = t.css_first("title")
    pdfs: list[dict] = []
    for a in t.css("a[href]"):
        href = a.attributes.get("href") or ""
        if href.lower().endswith(".pdf"):
            pdfs.append({"title": _clean(a.text()) or href.rsplit("/", 1)[-1],
                         "url": urljoin(url, href)})
    body = t.body.text(separator=" ", strip=True) if t.body else ""
    return {
        "path": path.strip("/"),
        "title": _clean(h.text()) if h else _clean(title_tag.text()) if title_tag else None,
        "text": (_clean(body) or "")[:TEXT_CAP],
        "pdfs": pdfs[:15],
        "url": url,
    }


async def sections() -> UpstreamJSON:
    """The curated registry of verified IRP sections (static)."""
    return {"sections": [{"path": p, "name": n, "url": f"{BASE}/{p}/"}
                         for p, n in SECTIONS.items()]}
