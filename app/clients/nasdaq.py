"""Nasdaq.com — Unofficial quote API. Market cap, prices, history."""

from . import UpstreamJSON, safe_get

BASE = "https://api.nasdaq.com/api/quote"
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
