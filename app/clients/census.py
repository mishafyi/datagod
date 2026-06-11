"""Census Bureau — Demographics for every US geography."""

from . import UpstreamJSON, safe_get
from ..config import cfg

BASE = "https://api.census.gov/data"


async def acs(variables: str = "NAME,B01001_001E", year: int = 2022,
              geo_for: str = "state:*", geo_in: str = "") -> UpstreamJSON:
    """Query American Community Survey data."""
    params: dict = {"get": variables, "for": geo_for}
    if geo_in:
        params["in"] = geo_in
    if cfg.CENSUS_API_KEY:
        params["key"] = cfg.CENSUS_API_KEY
    return await safe_get(f"{BASE}/{year}/acs/acs1", "census",
                          params=params, follow_redirects=True)


async def population_by_state(year: int = 2022) -> UpstreamJSON:
    """Shortcut: population by state."""
    return await acs("NAME,B01001_001E", year, "state:*")


async def income_by_state(year: int = 2022) -> UpstreamJSON:
    """Shortcut: median household income by state."""
    return await acs("NAME,B19013_001E", year, "state:*")
