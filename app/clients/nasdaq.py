"""Nasdaq.com — Unofficial quote API. Market cap, prices, history, financials,
insider trades, earnings, calendars, screener.

All endpoints share the same host and browser-like User-Agent (without it the
API returns HTTP 401). Responses are passed through unchanged; numeric fields
come back as strings with commas/dollar signs (e.g. MarketCap
"5,553,872,968,719", price "$228.40") — strip + cast at the call site.

Nasdaq reports most failures with HTTP 200 and the real status inside the body
(`status.rCode` 400 + `bCodeMessage` "Symbol not exists.", "The value 'A' is not
valid."); `_get` turns those into the error-dict so the envelope reports them.
"""

from . import UpstreamJSON, error_dict, safe_get

ROOT = "https://api.nasdaq.com/api"
BASE = f"{ROOT}/quote"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}
# /company/{t}/financials takes frequency 1 (annual) or 2 (quarterly) only.
FREQUENCIES = {"1": "1", "a": "1", "annual": "1", "2": "2", "q": "2", "quarterly": "2"}


async def _get(url: str, params: dict) -> UpstreamJSON:
    data = await safe_get(url, "nasdaq", params=params, headers=HEADERS)
    status = data.get("status") if isinstance(data, dict) and not data.get("error") else None
    if not isinstance(status, dict):
        return data
    code = status.get("rCode")
    if isinstance(code, int) and code != 200:
        reasons = [str(m["errorMessage"]) for m in status.get("bCodeMessage") or []
                   if isinstance(m, dict) and m.get("errorMessage")]
        return error_dict("nasdaq", code, "; ".join(reasons) or f"Nasdaq rCode {code}")
    return data


async def summary(ticker: str, asset_class: str = "stocks") -> UpstreamJSON:
    """Market cap, sector, industry, P/E, dividend, 52-week range."""
    return await _get(f"{BASE}/{ticker}/summary", {"assetclass": asset_class})


async def info(ticker: str, asset_class: str = "stocks") -> UpstreamJSON:
    """Real-time price, bid/ask, volume, percent change."""
    return await _get(f"{BASE}/{ticker}/info", {"assetclass": asset_class})


async def historical(ticker: str, fromdate: str, todate: str,
                     limit: int = 30, asset_class: str = "stocks") -> UpstreamJSON:
    """Daily OHLCV between two dates (YYYY-MM-DD). Newest row first."""
    return await _get(f"{BASE}/{ticker}/historical",
                      {"assetclass": asset_class, "fromdate": fromdate,
                       "todate": todate, "limit": limit})


async def dividends(ticker: str, asset_class: str = "stocks") -> UpstreamJSON:
    """Dividend history."""
    return await _get(f"{BASE}/{ticker}/dividends", {"assetclass": asset_class})


async def financials(ticker: str, frequency: str = "annual") -> UpstreamJSON:
    """Income statement, balance sheet, cash flow. frequency: annual (A, 1) or
    quarterly (Q, 2) — Nasdaq itself accepts only 1 or 2."""
    code = FREQUENCIES.get(frequency.strip().lower())
    if code is None:
        return error_dict("nasdaq", 400, f"frequency must be annual (A, 1) or quarterly (Q, 2); "
                                         f"got {frequency!r}")
    return await _get(f"{ROOT}/company/{ticker}/financials", {"frequency": code})


async def insider_trades(ticker: str, limit: int = 15) -> UpstreamJSON:
    """Recent insider (Form 4) buy/sell transactions for a ticker."""
    return await _get(f"{ROOT}/company/{ticker}/insider-trades", {"limit": limit})


async def earnings_surprise(ticker: str, limit: int = 15) -> UpstreamJSON:
    """Historical reported-vs-consensus EPS surprises for a ticker."""
    return await _get(f"{ROOT}/company/{ticker}/earnings-surprise", {"limit": limit})


async def calendar_earnings(date: str) -> UpstreamJSON:
    """Companies reporting earnings on a given day (YYYY-MM-DD)."""
    return await _get(f"{ROOT}/calendar/earnings", {"date": date})


async def calendar_ipo(date: str) -> UpstreamJSON:
    """IPOs priced/upcoming/filed/withdrawn in a month. Nasdaq takes YYYY-MM and
    rejects a full date, so YYYY-MM-DD is trimmed to its month."""
    return await _get(f"{ROOT}/ipo/calendar", {"date": date.strip()[:7]})


async def screener(limit: int = 25) -> UpstreamJSON:
    """Full stock-screener output (table rows)."""
    return await _get(f"{ROOT}/screener/stocks", {"tableonly": "true", "limit": limit})
