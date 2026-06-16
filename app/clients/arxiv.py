"""arXiv — e-print preprint repository (Atom XML, parsed with feedparser).

arXiv exposes a single query endpoint (`export.arxiv.org/api/query`) that returns
Atom 1.0 XML, NOT JSON. Like nsarchive/house_fd, this client therefore can't use
`safe_get` (which calls `.json()`): it fetches the XML with the shared async httpx
client, parses it with `feedparser`, builds clean records, and returns the standard
error-dict contract on failure — an intentional exception to the pass-through rule.

Quirks honored here (see docs/ARXIV_API.md):
  * The `http://` endpoint 301-redirects to `https://`; we use the https BASE and
    also pass `follow_redirects=True` (httpx does NOT follow redirects by default,
    so without this the client would parse an empty 301 body).
  * arXiv asks callers to make at most one request every three seconds on a single
    connection (legacy-API Terms of Use). A module-level RateLimiter enforces 1/3s.
  * A malformed `id_list` (e.g. "not-an-id") returns HTTP 400 with an error feed;
    raise_for_status() raises and we return the error-dict (upstream_status=400).
    A valid-pattern but nonexistent id returns 200 with zero entries.
  * Paging is `start` (offset) + `max_results`; arXiv caps `max_results` at 2000 and
    recommends <=2000 per call, paging with `start`. We cap at 100 like sibling routes.
"""

import feedparser

from . import RateLimiter, UpstreamJSON, get_client

BASE = "https://export.arxiv.org/api/query"
_SORT_BY = frozenset({"relevance", "lastUpdatedDate", "submittedDate"})
_SORT_ORDER = frozenset({"ascending", "descending"})
# arXiv legacy-API Terms of Use: <=1 request / 3 seconds, single connection.
_limiter = RateLimiter(rate=1, period=3.0)


def _err(status: int, message: str) -> dict:
    return {"error": True, "source": "arxiv", "upstream_status": status, "message": message}


def _bare_id(entry_id: str) -> str:
    """'http://arxiv.org/abs/2301.00001v2' -> '2301.00001v2' (keeps the version)."""
    return entry_id.rsplit("/abs/", 1)[-1]


def _pdf_url(entry: feedparser.FeedParserDict) -> str | None:
    """The rel='related' application/pdf link arXiv attaches to every entry."""
    for link in entry.get("links", []):
        if link.get("type") == "application/pdf":
            return link.get("href")
    return None


def _entry_to_record(entry: feedparser.FeedParserDict) -> dict:
    primary = entry.get("arxiv_primary_category") or {}
    return {
        "arxiv_id": _bare_id(entry.get("id", "")),
        "title": entry.get("title"),
        "summary": entry.get("summary"),
        "authors": [a.get("name") for a in entry.get("authors", [])],
        "published": entry.get("published"),
        "updated": entry.get("updated"),
        "primary_category": primary.get("term"),
        "categories": [t.get("term") for t in entry.get("tags", [])],
        "pdf_url": _pdf_url(entry),
        "abstract_url": entry.get("id"),
        "doi": entry.get("arxiv_doi"),
        "journal_ref": entry.get("arxiv_journal_ref"),
        "comment": entry.get("arxiv_comment"),
    }


def _build(text: str) -> UpstreamJSON:
    """Parse an arXiv Atom feed (already fetched) into the clean envelope."""
    feed = feedparser.parse(text)
    meta = feed.feed
    total = meta.get("opensearch_totalresults")
    start = meta.get("opensearch_startindex")
    per_page = meta.get("opensearch_itemsperpage")
    return {
        "total_results": int(total) if total is not None else None,
        "start": int(start) if start is not None else None,
        "items_per_page": int(per_page) if per_page is not None else None,
        "entries": [_entry_to_record(e) for e in feed.entries],
    }


async def _query(params: dict) -> UpstreamJSON:
    try:
        await _limiter.acquire()
        r = await get_client().get(BASE, params=params, follow_redirects=True)
        r.raise_for_status()
        return _build(r.text)
    except Exception as exc:
        return _err(getattr(getattr(exc, "response", None), "status_code", 0), str(exc))


async def search(query: str, start: int = 0, max_results: int = 10,
                 sort_by: str = "relevance", sort_order: str = "descending") -> UpstreamJSON:
    """Full-text search arXiv (title, abstract, authors, …) via `search_query`.

    `query` is forwarded as `search_query`. A bare term (e.g. "electron") searches all
    fields; field prefixes (`ti:`, `au:`, `abs:`, `cat:`, `all:`) and boolean operators
    (`AND`/`OR`/`ANDNOT`) work too — e.g. `ti:"quantum computing" AND cat:cs.LG`.
    `sort_by` ∈ {relevance, lastUpdatedDate, submittedDate}; `sort_order` ∈
    {ascending, descending}. Invalid values fall back to the arXiv defaults.
    """
    params: dict = {
        "search_query": query,
        "start": max(start, 0),
        "max_results": max_results,
    }
    if sort_by in _SORT_BY:
        params["sortBy"] = sort_by
    if sort_order in _SORT_ORDER:
        params["sortOrder"] = sort_order
    return await _query(params)


async def get_by_id(arxiv_id: str) -> UpstreamJSON:
    """Fetch one (or more, comma-separated) papers by arXiv id via `id_list`.

    Accepts new-style ('2301.00001', optionally '…v2') or old-style ('cond-mat/0011267')
    ids. A malformed id yields the error-dict (upstream HTTP 400); a well-formed but
    unknown id yields `entries: []` with `total_results` 0.
    """
    return await _query({"id_list": arxiv_id})
