"""Nasdaq.com — Unofficial quote API. Market cap, prices, history, financials,
insider trades, earnings, calendars, screener.

All endpoints share the same host and browser-like User-Agent (without it the
API returns HTTP 401). Responses are passed through unchanged; numeric fields
come back as strings with commas/dollar signs (e.g. MarketCap
"5,553,872,968,719", price "$228.40") — strip + cast at the call site.
"""

from . import UpstreamJSON, safe_get

ROOT = "https://api.nasdaq.com/api"
BASE = f"{ROOT}/quote"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}


async def summary(ticker: str, asset_class: str = "stocks") -> UpstreamJSON:
    """Market cap, sector, industry, P/E, dividend, 52-week range."""
    return await safe_get(f"{BASE}/{ticker}/summary", "nasdaq",
                          params={"assetclass": asset_class}, headers=HEADERS)


async def info(ticker: str, asset_class: str = "stocks") -> UpstreamJSON:
    """Real-time price, bid/ask, volume, percent change."""
    return await safe_get(f"{BASE}/{ticker}/info", "nasdaq",
                          params={"assetclass": asset_class}, headers=HEADERS)


async def historical(ticker: str, fromdate: str, todate: str,
                     limit: int = 30, asset_class: str = "stocks") -> UpstreamJSON:
    """Daily OHLCV between two dates (YYYY-MM-DD). Newest row first."""
    return await safe_get(f"{BASE}/{ticker}/historical", "nasdaq",
                          params={"assetclass": asset_class,
                                  "fromdate": fromdate, "todate": todate,
                                  "limit": limit}, headers=HEADERS)


async def dividends(ticker: str, asset_class: str = "stocks") -> UpstreamJSON:
    """Dividend history."""
    return await safe_get(f"{BASE}/{ticker}/dividends", "nasdaq",
                          params={"assetclass": asset_class}, headers=HEADERS)


async def financials(ticker: str, frequency: str = "1") -> UpstreamJSON:
    """Income statement, balance sheet, cash flow. frequency: '1' annual, '2' quarterly."""
    return await safe_get(f"{ROOT}/company/{ticker}/financials", "nasdaq",
                          params={"frequency": frequency}, headers=HEADERS)


async def insider_trades(ticker: str, limit: int = 15) -> UpstreamJSON:
    """Recent insider (Form 4) buy/sell transactions for a ticker."""
    return await safe_get(f"{ROOT}/company/{ticker}/insider-trades", "nasdaq",
                          params={"limit": limit}, headers=HEADERS)


async def earnings_surprise(ticker: str, limit: int = 15) -> UpstreamJSON:
    """Historical reported-vs-consensus EPS surprises for a ticker."""
    return await safe_get(f"{ROOT}/company/{ticker}/earnings-surprise", "nasdaq",
                          params={"limit": limit}, headers=HEADERS)


async def calendar_earnings(date: str) -> UpstreamJSON:
    """Companies reporting earnings on a given day (YYYY-MM-DD)."""
    return await safe_get(f"{ROOT}/calendar/earnings", "nasdaq",
                          params={"date": date}, headers=HEADERS)


async def calendar_ipo(date: str) -> UpstreamJSON:
    """IPOs priced/expected in a given month (YYYY-MM)."""
    return await safe_get(f"{ROOT}/ipo/calendar", "nasdaq",
                          params={"date": date}, headers=HEADERS)


async def screener(limit: int = 25) -> UpstreamJSON:
    """Full stock-screener output (table rows)."""
    return await safe_get(f"{ROOT}/screener/stocks", "nasdaq",
                          params={"tableonly": "true", "limit": limit}, headers=HEADERS)
