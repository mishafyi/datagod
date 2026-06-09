"""FRED — Federal Reserve Economic Data. 800K+ time series."""

from . import UpstreamJSON, safe_get
from ..config import cfg

BASE = "https://api.stlouisfed.org/fred"


async def get_series(series_id: str, limit: int = 10) -> UpstreamJSON:
    """Get observations for a series (e.g., GDP, UNRATE, CPIAUCSL)."""
    return await safe_get(f"{BASE}/series/observations", "fred", params={
        "series_id": series_id, "api_key": cfg.FRED_API_KEY,
        "file_type": "json", "limit": limit, "sort_order": "desc",
    })


async def search(query: str, limit: int = 10) -> UpstreamJSON:
    """Search for series by keyword."""
    return await safe_get(f"{BASE}/series/search", "fred", params={
        "search_text": query, "api_key": cfg.FRED_API_KEY,
        "file_type": "json", "limit": limit,
    })


async def series_info(series_id: str) -> UpstreamJSON:
    """Get metadata for a series."""
    return await safe_get(f"{BASE}/series", "fred", params={
        "series_id": series_id, "api_key": cfg.FRED_API_KEY,
        "file_type": "json",
    })
