"""World Bank Open Data — development indicators for every country (16K+ series)."""

from . import UpstreamJSON, safe_get

BASE = "https://api.worldbank.org/v2"


async def indicator(indicator_id: str, countries: str = "all", date_range: str = "",
                    per_page: int = 200) -> UpstreamJSON:
    """One indicator (e.g. NY.GDP.MKTP.CD) for `countries` — ISO2 codes joined
    with ";" ("us;cn;fr") or "all". Response is [paging-metadata, rows];
    `date_range` bounds years as YYYY:YYYY."""
    params: dict = {"format": "json", "per_page": per_page}
    if date_range:
        params["date"] = date_range
    return await safe_get(f"{BASE}/country/{countries}/indicator/{indicator_id}",
                          "worldbank", params=params)


async def countries(per_page: int = 300) -> UpstreamJSON:
    """All countries/aggregates with region, income level, and ISO codes."""
    return await safe_get(f"{BASE}/country", "worldbank",
                          params={"format": "json", "per_page": per_page})
