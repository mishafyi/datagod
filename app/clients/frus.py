"""Foreign Relations of the United States (history.state.gov) — HTML scrape.

FRUS is the official documentary record of US foreign policy: 500+ volumes of
declassified cables, memoranda and meeting minutes, including the retrospective
covert-action volumes (Iran 1951-54, Guatemala 1952-54, Congo 1960-68, Chile
1969-73, the Intelligence Community volumes). history.state.gov has no public
JSON API, but both search results and document pages are server-rendered, so
this client parses them with selectolax (same intentional exception to the
pass-through rule as nsarchive/house_fd — brittle if the theme changes).

Search results: div.hsg-search-result blocks, paginated by ?start= (10/page).
Documents: /historicaldocuments/{volume}/d{n}, TEI-classed HTML in div.content.
"""

import re

from selectolax.parser import HTMLParser

from . import UpstreamJSON, get_client

BASE = "https://history.state.gov"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
PER_PAGE = 10
BODY_CAP = 40000  # generous: the DESK owns the final context slice (long memcons exceed 16K chars)


def _err(status: int, message: str) -> dict:
    return {"error": True, "source": "frus", "upstream_status": status, "message": message}


def _clean(s: str | None) -> str | None:
    return re.sub(r"\s+", " ", s).strip() if s else None


def _parse_search(html: str, start: int) -> UpstreamJSON:
    t = HTMLParser(html)
    results: list[dict] = []
    for block in t.css("div.hsg-search-result"):
        a = block.css_first("h3.hsg-search-result-heading a")
        if not a:
            continue
        href = a.attributes.get("href", "")
        m = re.match(r"/historicaldocuments/([^/]+)/d(\d+)$", href)
        summary = block.css_first("p.hsg-search-result-summary")
        results.append({
            "title": _clean(a.text()),
            "volume": m.group(1) if m else None,
            "doc": int(m.group(2)) if m else None,
            "url": f"{BASE}{href}",
            "summary": _clean(summary.text(separator=" ")) if summary else None,
        })
    body = t.body.text(separator=" ", strip=True) if t.body else ""
    m = re.search(r"([\d,]+)\s+results?\b", body)
    total = int(m.group(1).replace(",", "")) if m else None
    return {"start": start, "per_page": PER_PAGE, "total": total, "results": results}


def _parse_document(html: str, volume: str, doc: int) -> UpstreamJSON:
    t = HTMLParser(html)
    content = t.css_first("div.content")
    if not content:
        return _err(404, f"No document content for {volume}/d{doc}")
    head = content.css_first("h3")
    # Source note (archival citation) rides in a footnote-styled block when present.
    note = content.css_first(".tei-note1, .tei-sourcenote")
    return {
        "volume": volume,
        "doc": doc,
        "title": _clean(head.text()) if head else None,
        "source_note": _clean(note.text(separator=" ")) if note else None,
        "body": _clean(content.text(separator=" "))[:BODY_CAP],
        "url": f"{BASE}/historicaldocuments/{volume}/d{doc}",
    }


async def search(q: str, start: int = 1) -> UpstreamJSON:
    """Full-text search across all FRUS volumes. `start` is the 1-based result
    offset (10 results/page; next page = start+10)."""
    try:
        r = await get_client().get(f"{BASE}/search",
                                   params={"q": q, "start": start, "sort-by": "relevance"},
                                   headers=HEADERS)
        r.raise_for_status()
        return _parse_search(r.text, start)
    except Exception as exc:
        return _err(getattr(getattr(exc, "response", None), "status_code", 0), str(exc))


async def document(volume: str, doc: int) -> UpstreamJSON:
    """One FRUS document by volume id + document number (from search results),
    e.g. volume=frus1969-76v21, doc=7."""
    try:
        r = await get_client().get(f"{BASE}/historicaldocuments/{volume}/d{doc}", headers=HEADERS)
        r.raise_for_status()
        return _parse_document(r.text, volume, doc)
    except Exception as exc:
        return _err(getattr(getattr(exc, "response", None), "status_code", 0), str(exc))
