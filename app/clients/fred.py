"""FRED — Federal Reserve Economic Data. 800K+ time series."""

from . import UpstreamJSON, safe_get
from ..config import cfg

BASE = "https://api.stlouisfed.org/fred"


async def get_series(
    series_id: str,
    limit: int = 10,
    offset: int = 0,
    sort_order: str = "asc",
    observation_start: str | None = None,
    observation_end: str | None = None,
) -> UpstreamJSON:
    """Get observations for a series (e.g., GDP, UNRATE, CPIAUCSL).

    `sort_order` ("asc"/"desc") and `offset` mirror FRED's native paging
    (default: oldest-first, no skip). `observation_start`/`observation_end`
    bound the date range (YYYY-MM-DD); omitted when None so FRED's own
    full-history default applies.
    """
    params: dict[str, str | int] = {
        "series_id": series_id, "api_key": cfg.FRED_API_KEY,
        "file_type": "json", "limit": limit, "offset": offset,
        "sort_order": sort_order,
    }
    if observation_start is not None:
        params["observation_start"] = observation_start
    if observation_end is not None:
        params["observation_end"] = observation_end
    return await safe_get(f"{BASE}/series/observations", "fred", params=params)


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
