"""SEC EDGAR — Corporate filings, financials, insider trades."""

import asyncio
from typing import Callable

from . import RateLimiter, UpstreamJSON, get_client, safe_get
from ..config import cfg

BASE = "https://data.sec.gov"
SEARCH = "https://efts.sec.gov/LATEST/search-index"
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
HEADERS = {"User-Agent": cfg.SEC_USER_AGENT}

# SEC's fair-access limit is 10 req/s across the whole IP. Gate EVERY EDGAR call.
_limiter = RateLimiter(rate=10, period=1.0)

_ticker_map: dict[str, str] | None = None


async def _gated_get(url: str, **kwargs) -> UpstreamJSON:
    """safe_get + EDGAR rate limit."""
    await _limiter.acquire()
    return await safe_get(url, "edgar", **kwargs)


async def company(cik: str) -> UpstreamJSON:
    """Get company metadata + filing history. CIK can be number or ticker."""
    return await _by_cik(cik, lambda padded: f"{BASE}/submissions/CIK{padded}.json")


async def financials(cik: str) -> UpstreamJSON:
    """Get all XBRL financial facts for a company."""
    return await _by_cik(cik, lambda padded: f"{BASE}/api/xbrl/companyfacts/CIK{padded}.json")


async def concept(cik: str, concept: str, taxonomy: str = "us-gaap") -> UpstreamJSON:
    """Get one financial concept's history (e.g., Revenues, Assets)."""
    return await _by_cik(
        cik,
        lambda padded: f"{BASE}/api/xbrl/companyconcept/CIK{padded}/{taxonomy}/{concept}.json",
    )


async def frames(concept: str, unit: str = "USD", period: str = "CY2023",
                 taxonomy: str = "us-gaap") -> UpstreamJSON:
    """Cross-company comparison. One concept for all companies in a period."""
    return await _gated_get(
        f"{BASE}/api/xbrl/frames/{taxonomy}/{concept}/{unit}/{period}.json",
        headers=HEADERS,
    )


# SEC EFTS returns a FIXED 100 hits per page (it ignores any `size` request); pages are
# walked with `from`, and its Elasticsearch window caps reachable results at 10,000.
EFTS_PAGE_SIZE = 100
EFTS_MAX_RESULTS = 10_000


async def _fetch_page(base_params: dict, offset: int, attempts: int = 3) -> UpstreamJSON:
    """Fetch one EFTS page, retrying with small backoff — efts.sec.gov 500s
    intermittently on broad queries, which would otherwise truncate a paged walk."""
    page: UpstreamJSON = {"error": True, "source": "edgar", "upstream_status": 0,
                          "message": "no attempt made"}
    for attempt in range(attempts):
        page = await _gated_get(
            SEARCH, params={**base_params, "from": offset, "size": EFTS_PAGE_SIZE},
            headers=HEADERS,
        )
        if not (isinstance(page, dict) and page.get("error")):
            return page
        if attempt < attempts - 1:
            await asyncio.sleep(0.4 * (attempt + 1))
    return page


async def search_filings(query: str, forms: str = "", limit: int = 10,
                         startdt: str = "", enddt: str = "") -> UpstreamJSON:
    """Full-text search inside filing documents.

    `limit` is the max number of hits to return (1..10000). The SEC returns a fixed
    100 hits per page and ignores page-size requests, so this walks pages via `from`
    and concatenates them until it has `limit` hits or the matches run out. `forms`
    filters by form type; `startdt`/`enddt` (YYYY-MM-DD) scope to a filing-date range
    (EFTS covers 2001+). The SEC caps reachable results at 10,000 regardless of `limit`.

    Returns EFTS shape (hits.total, hits.hits, aggregations) with the hits concatenated
    across pages, plus a `_pagination` summary. A failed first page returns the error
    dict; a failure mid-walk returns the hits gathered so far."""
    base_params: dict = {"q": query}
    if forms:
        base_params["forms"] = forms
    if startdt:
        base_params["startdt"] = startdt
    if enddt:
        base_params["enddt"] = enddt

    want = max(1, min(limit, EFTS_MAX_RESULTS))
    collected: list = []
    first: UpstreamJSON | None = None
    pages = 0
    offset = 0
    while offset < EFTS_MAX_RESULTS and len(collected) < want:
        page = await _fetch_page(base_params, offset)
        if isinstance(page, dict) and page.get("error"):
            if first is None:
                return page  # first page failed (after retries) → surface the error
            break            # later page still failing → return what we gathered
        pages += 1
        if first is None:
            first = page
        page_hits = (page.get("hits") or {}).get("hits", [])
        collected.extend(page_hits)
        if len(page_hits) < EFTS_PAGE_SIZE:
            break            # short page → no more results
        offset += EFTS_PAGE_SIZE

    first = first or {}
    hits_obj = dict(first.get("hits") or {})
    hits_obj["hits"] = collected[:want]
    result = dict(first)
    result["hits"] = hits_obj
    result["_pagination"] = {
        "returned": len(hits_obj["hits"]),
        "requested": limit,
        "pages_fetched": pages,
        "page_size": EFTS_PAGE_SIZE,
        "ceiling": EFTS_MAX_RESULTS,
    }
    return result


async def _by_cik(cik: str, url_for: Callable[[str], str]) -> UpstreamJSON:
    """Resolve `cik` (number or ticker) then GET the URL `url_for(padded_cik)`."""
    try:
        padded = await _resolve_cik(cik)
    except ValueError as exc:
        return {"error": True, "source": "edgar",
                "upstream_status": 404, "message": str(exc)}
    except Exception as exc:
        return {"error": True, "source": "edgar",
                "upstream_status": 0, "message": str(exc)}
    return await _gated_get(url_for(padded), headers=HEADERS)


async def _resolve_cik(cik: str) -> str:
    """Return zero-padded CIK; treat digits as CIK, else look up as ticker."""
    if cik.isdigit():
        return cik.zfill(10)
    return await _ticker_to_cik(cik)


async def _ticker_to_cik(ticker: str) -> str:
    global _ticker_map
    if _ticker_map is None:
        await _limiter.acquire()
        r = await get_client().get(TICKERS_URL, headers=HEADERS)
        data = r.json()
        _ticker_map = {entry["ticker"]: str(entry["cik_str"]).zfill(10)
                       for entry in data.values()}
    padded = _ticker_map.get(ticker.upper())
    if padded is None:
        raise ValueError(f"Ticker '{ticker}' not found")
    return padded
