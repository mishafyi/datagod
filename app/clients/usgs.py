"""USGS Earthquake Hazards — worldwide earthquake catalog (FDSN event web service)."""

from . import UpstreamJSON, safe_get

BASE = "https://earthquake.usgs.gov/fdsnws/event/1"


async def earthquakes(starttime: str = "", endtime: str = "", minmagnitude: float = 0.0,
                      orderby: str = "time", limit: int = 10) -> UpstreamJSON:
    """GeoJSON earthquake catalog. Dates are YYYY-MM-DD (default: last 30 days);
    orderby: time | time-asc | magnitude | magnitude-asc."""
    params: dict = {"format": "geojson", "orderby": orderby, "limit": limit}
    if starttime:
        params["starttime"] = starttime
    if endtime:
        params["endtime"] = endtime
    if minmagnitude:
        params["minmagnitude"] = minmagnitude
    return await safe_get(f"{BASE}/query", "usgs", params=params)
