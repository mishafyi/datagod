"""National Security Archive (GWU) — Virtual Reading Room (HTML scrape, UNOFFICIAL & BRITTLE).

The National Security Archive is an NGO at George Washington University — NOT the government
agency NARA. It has no public API (a Drupal 10 site). This client scrapes its Search-API-
backed Virtual Reading Room: the listing at /virtual-reading-room (full-text searchable via
?search_api_fulltext=, paginated via ?page=) and individual /document/{id-slug} pages.

BRITTLE by design: it parses HTML, so any theme/markup change will break it. Covers only the
free published documents (~14k); the full searchable corpus is the paywalled DNSA (ProQuest).
Like house_fd, it can't use safe_get (HTML, not JSON) — it parses with selectolax and returns
the standard error-dict contract on failure (an intentional exception to the pass-through rule).
"""

import math
import re

from selectolax.parser import HTMLParser

from . import UpstreamJSON, get_client

BASE = "https://nsarchive.gwu.edu"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
PER_PAGE = 20


def _err(status: int, message: str) -> dict:
    return {"error": True, "source": "nsarchive", "upstream_status": status, "message": message}


def _txt(node) -> str | None:
    return node.text(strip=True) if node else None


def _field(scope, name: str) -> str | None:
    """Clean value of a Drupal `field--name-{name}` block (prefers `.field__item`)."""
    item = scope.css_first(f".field--name-{name} .field__item") or scope.css_first(f".field--name-{name}")
    return _txt(item)


def _date(scope) -> tuple[str | None, str | None]:
    """(iso, text) — exact `field-date` (has <time datetime>) or approximate `field-circa-date`."""
    tm = scope.css_first(".field--name-field-date time")
    if tm:
        return tm.attributes.get("datetime"), _txt(tm)
    return None, _field(scope, "field-circa-date")


def _parse_listing(html: str, page: int) -> UpstreamJSON:
    t = HTMLParser(html)
    results: list[dict] = []
    for art in t.css("article.media--type-document"):
        link = art.css_first(".field--name-field-title a")
        href = link.attributes.get("href") if link else None
        if not href:
            continue
        seg = href.rsplit("/document/", 1)[-1]
        img = art.css_first(".field--name-thumbnail img")
        iso, dtext = _date(art)
        results.append({
            "id": seg.split("-", 1)[0],
            "path": seg,
            "title": _txt(art.css_first(".field--name-field-title")),
            "date": iso,
            "date_text": dtext,
            "source": _field(art, "field-source"),
            "url": f"{BASE}{href}",
            "thumbnail": f"{BASE}{img.attributes.get('src')}" if img and img.attributes.get("src") else None,
        })
    body = t.body.text(separator=" ", strip=True) if t.body else ""
    m = re.search(r"([\d,]+)\s+document\(s\) found", body)
    total = int(m.group(1).replace(",", "")) if m else None
    return {"page": page, "per_page": PER_PAGE, "total": total,
            "total_pages": math.ceil(total / PER_PAGE) if total else None,
            "results": results}


def _parse_document(html: str, doc_id: str) -> UpstreamJSON:
    t = HTMLParser(html)
    if not t.css_first("h1"):
        return _err(404, f"No document page for '{doc_id}'")
    pdf = None
    media = t.css_first(".field--name-field-media-file a[href]")
    if media:
        h = media.attributes.get("href", "")
        pdf = f"{BASE}{h}" if h.startswith("/") else h
    if not pdf:  # some docs embed the PDF (iframe/object) instead of a field link
        for n in t.css("a[href], iframe[src], embed[src]"):
            h = n.attributes.get("href") or n.attributes.get("src") or ""
            if ".pdf" in h.lower():
                pdf = f"{BASE}{h}" if h.startswith("/") else h
                break
    body_n = t.css_first(".field--name-body")
    iso, dtext = _date(t)
    return {
        "id": doc_id.split("-", 1)[0],
        "path": doc_id,
        "title": _txt(t.css_first("h1")),
        "date": iso,
        "date_text": dtext,
        "source": _field(t, "field-source"),
        "description": _field(t, "field-description"),
        "body": body_n.text(separator=" ", strip=True)[:5000] if body_n else None,
        "pdf_url": pdf,
        "url": f"{BASE}/document/{doc_id}",
    }


async def search(q: str = "", page: int = 1) -> UpstreamJSON:
    """Full-text search the Virtual Reading Room (empty q browses chronologically). 20/page."""
    params: dict = {"page": max(page - 1, 0)}  # site pager is 0-based
    if q:
        params["search_api_fulltext"] = q
    try:
        r = await get_client().get(f"{BASE}/virtual-reading-room", params=params, headers=HEADERS)
        r.raise_for_status()
        return _parse_listing(r.text, page)
    except Exception as exc:
        return _err(getattr(getattr(exc, "response", None), "status_code", 0), str(exc))


async def document(doc_id: str) -> UpstreamJSON:
    """Full record for one VRR document by its '{id}-{slug}' path (from search results)."""
    try:
        r = await get_client().get(f"{BASE}/document/{doc_id}", headers=HEADERS)
        r.raise_for_status()
        return _parse_document(r.text, doc_id)
    except Exception as exc:
        return _err(getattr(getattr(exc, "response", None), "status_code", 0), str(exc))
