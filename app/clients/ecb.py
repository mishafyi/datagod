"""ECB Data Portal — euro-area statistics via SDMX (EXR exchange rates, ICP inflation…)."""

from . import UpstreamJSON, safe_get

BASE = "https://data-api.ecb.europa.eu/service/data"


async def series(flow_ref: str, key: str, start_period: str = "",
                 end_period: str = "") -> UpstreamJSON:
    """One series from a dataflow, e.g. EXR / D.USD.EUR.SP00.A (daily USD/EUR
    reference rate). Periods are YYYY-MM-DD (or YYYY / YYYY-MM per frequency)."""
    params: dict = {"format": "jsondata"}
    if start_period:
        params["startPeriod"] = start_period
    if end_period:
        params["endPeriod"] = end_period
    return await safe_get(f"{BASE}/{flow_ref}/{key}", "ecb", params=params)
