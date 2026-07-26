"""NWS — US National Weather Service active alerts (api.weather.gov).

The API is keyless but REQUIRES a User-Agent header — returns 403 without one.
"""

from . import UpstreamJSON, safe_get

BASE = "https://api.weather.gov"
HEADERS = {"User-Agent": "DataGod/1.0 (github.com/mishafyi/datagod)"}


async def alerts(area: str = "", severity: str = "") -> UpstreamJSON:
    """Active alerts (GeoJSON). `area` = two-letter state/marine code (e.g. CA);
    `severity`: Extreme | Severe | Moderate | Minor | Unknown."""
    params: dict = {}
    if area:
        params["area"] = area
    if severity:
        params["severity"] = severity
    return await safe_get(f"{BASE}/alerts/active", "nws", params=params, headers=HEADERS)
