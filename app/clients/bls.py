"""BLS — Employment, wages, CPI, occupational data."""

from . import UpstreamJSON, safe_get, safe_post
from ..config import cfg

BASE = "https://api.bls.gov/publicAPI/v1/timeseries/data"

SERIES = {
    "unemployment": "LNS14000000",
    "nonfarm_employment": "CES0000000001",
    "cpi": "CUUR0000SA0",
    "ppi": "WPUFD4",
    "hourly_earnings": "CEU0500000003",
}


async def series(series_id: str, start_year: int = 2024,
                 end_year: int = 2026) -> UpstreamJSON:
    """Get time series data. Use SERIES dict for common IDs."""
    series_id = SERIES.get(series_id, series_id)
    return await safe_get(f"{BASE}/{series_id}", "bls", params={
        "startyear": str(start_year), "endyear": str(end_year),
    })


async def multiple(series_ids: list[str], start_year: int = 2024,
                   end_year: int = 2026) -> UpstreamJSON:
    """Get multiple series at once (POST, requires key)."""
    resolved = [SERIES.get(s, s) for s in series_ids]
    payload: dict = {"seriesid": resolved, "startyear": str(start_year),
                     "endyear": str(end_year)}
    if cfg.BLS_API_KEY:
        payload["registrationkey"] = cfg.BLS_API_KEY
    return await safe_post(BASE + "/", "bls", json=payload)
