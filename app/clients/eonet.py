"""NASA EONET — global natural-event tracker (wildfires, severe storms, volcanoes…).

The keyless global-wildfire feed (stands in for Copernicus EFFIS, whose data has
no clean public JSON API).
"""

from . import UpstreamJSON, safe_get

BASE = "https://eonet.gsfc.nasa.gov/api/v3"


async def events(category: str = "", status: str = "open", limit: int = 10,
                 days: int = 0) -> UpstreamJSON:
    """Natural events with geometry + source links. `category` e.g. wildfires |
    severeStorms | volcanoes (see categories()); status: open | closed | all;
    `days` limits to the last N days."""
    params: dict = {"status": status, "limit": limit}
    if category:
        params["category"] = category
    if days:
        params["days"] = days
    return await safe_get(f"{BASE}/events", "eonet", params=params)


async def categories() -> UpstreamJSON:
    """All event categories with ids and descriptions."""
    return await safe_get(f"{BASE}/categories", "eonet")
