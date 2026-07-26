"""IMF SDMX-JSON — macroeconomic time series (IFS, DOT, BOP, GFS…) + dataflow structures.

Upstream is notoriously slow and flaky (long stalls, frequent 5xx). Calls ride the
shared 30s client timeout; failures surface as the standard error-dict via safe_get.
"""

from . import UpstreamJSON, safe_get

BASE = "http://dataservices.imf.org/REST/SDMX_JSON.svc"


async def compact_data(database: str, key: str, start_period: str = "",
                       end_period: str = "") -> UpstreamJSON:
    """Time series from a database (e.g. IFS) by SDMX key (e.g. M.US.PCPI_IX =
    monthly US CPI index). Periods are years like 2020 (or 2020-01)."""
    params: dict = {}
    if start_period:
        params["startPeriod"] = start_period
    if end_period:
        params["endPeriod"] = end_period
    return await safe_get(f"{BASE}/CompactData/{database}/{key}", "imf", params=params)


async def structure(database: str) -> UpstreamJSON:
    """Data structure (dimensions + code lists) for a database (e.g. IFS)."""
    return await safe_get(f"{BASE}/DataStructure/{database}", "imf")
