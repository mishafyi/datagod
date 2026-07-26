"""UCDP — Uppsala Conflict Data Program: georeferenced organized-violence events.

The API was keyless until 2026; upstream now answers every request without an
`x-ucdp-access-token` header with 401 "API token required". A free token
(registration at ucdp.uu.se) set as UCDP_ACCESS_TOKEN re-enables the source.
"""

from . import UpstreamJSON, safe_get
from ..config import cfg

BASE = "https://ucdpapi.pcr.uu.se/api"


async def gedevents(country: str = "", start_date: str = "", end_date: str = "",
                    pagesize: int = 10, page: int = 0,
                    version: str = "24.1") -> UpstreamJSON:
    """GED conflict events. `country` = Gleditsch-Ward numeric id(s),
    comma-separated (e.g. 369 = Ukraine, 365 = Russia); dates YYYY-MM-DD;
    pagesize max 1000; page is 0-based. `version` pins the dataset release."""
    params: dict = {"pagesize": pagesize, "page": page}
    if country:
        params["Country"] = country
    if start_date:
        params["StartDate"] = start_date
    if end_date:
        params["EndDate"] = end_date
    headers = {"x-ucdp-access-token": cfg.UCDP_ACCESS_TOKEN} if cfg.UCDP_ACCESS_TOKEN else {}
    return await safe_get(f"{BASE}/gedevents/{version}", "ucdp", params=params, headers=headers)
