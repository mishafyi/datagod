"""SEC EDGAR — Corporate filings, financials, insider trades."""

from typing import Callable

import httpx

from . import RateLimiter, UpstreamJSON, get_client, safe_get
from ..config import cfg

BASE = "https://data.sec.gov"
ARCHIVES = "https://www.sec.gov/Archives/edgar/data"
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


async def frames(concept: str, period: str, unit: str = "USD",
                 taxonomy: str = "us-gaap") -> UpstreamJSON:
    """Cross-company comparison. One concept for all companies in a period.
    `period` is required (e.g. CY2023, CY2023Q1, CY2023Q4I) — no default."""
    return await _gated_get(
        f"{BASE}/api/xbrl/frames/{taxonomy}/{concept}/{unit}/{period}.json",
        headers=HEADERS,
    )


async def search_filings(params: dict) -> UpstreamJSON:
    """Full-text search inside filing documents — a TRUE transparent pass-through to the
    SEC's EFTS endpoint. Whatever is in `params` is forwarded verbatim (q, forms,
    dateRange, startdt, enddt, from, size, and anything else EFTS accepts). The SEC
    returns a FIXED 100 hits per page and ignores any page-size request, so paginate with
    `from` in steps of 100 (0, 100, 200 … up to ~9900; the SEC's result window caps at
    10,000). `startdt`/`enddt` (YYYY-MM-DD) scope to a filing-date range (EFTS covers
    2001+). Returns the SEC response unchanged: hits.total, hits.hits (≤100),
    aggregations."""
    return await _gated_get(SEARCH, params=params, headers=HEADERS)


async def submissions_overflow(filename: str) -> UpstreamJSON:
    """Fetch a submissions OVERFLOW file by name (for filers with 1000+ filings).
    `filename` comes from the Submissions API's `filings.files[].name`, e.g.
    `CIK0000320193-submissions-001.json`. Returns the SEC JSON unchanged."""
    return await _gated_get(f"{BASE}/submissions/{filename}", headers=HEADERS)


async def filing_document(cik: str, accession: str, document: str) -> httpx.Response | dict:
    """Fetch a RAW filing document from the EDGAR archives. `accession` is the accession
    number WITHOUT dashes (e.g. 000032019324000123); `document` is the filename from the
    Submissions API's `primaryDocument` (e.g. aapl-20240928.htm). Returns the raw httpx
    Response (caller returns its bytes) or the error-dict on failure."""
    await _limiter.acquire()
    url = f"{ARCHIVES}/{cik}/{accession}/{document}"
    try:
        r = await get_client().get(url, headers=HEADERS)
        r.raise_for_status()
        return r
    except Exception as exc:
        upstream_status = getattr(getattr(exc, "response", None), "status_code", 0)
        return {"error": True, "source": "edgar",
                "upstream_status": upstream_status, "message": str(exc)}


async def ticker_to_cik(ticker: str) -> UpstreamJSON:
    """Resolve a ticker symbol to its zero-padded CIK. Returns
    {"ticker": <upper>, "cik": <padded>} or the error-dict if the ticker is unknown."""
    try:
        padded = await _ticker_to_cik(ticker)
    except ValueError as exc:
        return {"error": True, "source": "edgar",
                "upstream_status": 404, "message": str(exc)}
    except Exception as exc:
        return {"error": True, "source": "edgar",
                "upstream_status": 0, "message": str(exc)}
    return {"ticker": ticker.upper(), "cik": padded}


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
