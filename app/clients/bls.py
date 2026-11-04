"""BLS — Employment, wages, CPI, occupational data.

Keyless calls use the v1 API. With BLS_API_KEY set they use v2, the version
that honors `registrationkey` (v1 silently ignores it, so the key bought
nothing): 500 queries/day, 50 series and 20 years per query instead of v1's
25/day, 25 series and 10 years.

BLS answers failures with HTTP 200 and status REQUEST_NOT_PROCESSED (daily
threshold reached, invalid key, too many years); `_checked` turns those into
the error-dict so the envelope reports them.
"""

from ..config import cfg
from . import UpstreamJSON, error_dict, safe_get, safe_post

BASE_V1 = "https://api.bls.gov/publicAPI/v1/timeseries/data"
BASE_V2 = "https://api.bls.gov/publicAPI/v2/timeseries/data"

SERIES = {
    "unemployment": "LNS14000000",
    "nonfarm_employment": "CES0000000001",
    "cpi": "CUUR0000SA0",
    "ppi": "WPUFD4",
    "hourly_earnings": "CEU0500000003",
}


def _base() -> str:
    return BASE_V2 if cfg.BLS_API_KEY else BASE_V1


def _checked(data: UpstreamJSON) -> UpstreamJSON:
    if isinstance(data, dict) and data.get("status") == "REQUEST_NOT_PROCESSED":
        message = " ".join(str(m) for m in data.get("message") or []) or "REQUEST_NOT_PROCESSED"
        return error_dict("bls", 429 if "threshold" in message.lower() else 400, message)
    return data


async def series(series_id: str, start_year: int,
                 end_year: int) -> UpstreamJSON:
    """Get time series data. Use SERIES dict for common IDs."""
    series_id = SERIES.get(series_id, series_id)
    params: dict = {"startyear": str(start_year), "endyear": str(end_year)}
    if cfg.BLS_API_KEY:
        params["registrationkey"] = cfg.BLS_API_KEY
    return _checked(await safe_get(f"{_base()}/{series_id}", "bls", params=params))


async def multiple(series_ids: list[str], start_year: int,
                   end_year: int) -> UpstreamJSON:
    """Get multiple series at once (POST, registrationkey added when set)."""
    resolved = [SERIES.get(s, s) for s in series_ids]
    payload: dict = {"seriesid": resolved, "startyear": str(start_year),
                     "endyear": str(end_year)}
    if cfg.BLS_API_KEY:
        payload["registrationkey"] = cfg.BLS_API_KEY
    return _checked(await safe_post(_base() + "/", "bls", json=payload))
