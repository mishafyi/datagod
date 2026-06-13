"""SEC EDGAR — Corporate filings, financials, insider trades."""

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


async def search_filings(query: str, forms: str = "", limit: int = 10,
                         startdt: str = "", enddt: str = "") -> UpstreamJSON:
    """Full-text search inside filing documents. Optional `startdt`/`enddt`
    (YYYY-MM-DD) scope results to a filing-date range (SEC EFTS covers 2001+)."""
    params: dict = {"q": query, "from": 0, "size": limit}
    if forms:
        params["forms"] = forms
    if startdt:
        params["startdt"] = startdt
    if enddt:
        params["enddt"] = enddt
    return await _gated_get(SEARCH, params=params, headers=HEADERS)


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
