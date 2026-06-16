"""Census Bureau — Demographics for every US geography."""

from . import UpstreamJSON, _error, get_client
from ..config import cfg

BASE = "https://api.census.gov/data"

# Census 302-redirects key failures to these HTML pages instead of erroring.
_KEY_ERROR_PAGES = ("invalid_key.html", "missing_key.html")


async def acs(year: int, variables: str = "NAME,B01001_001E",
              geo_for: str = "state:*", geo_in: str = "",
              dataset: str = "acs5") -> UpstreamJSON:
    """Query American Community Survey data.

    `year` is required (the upstream has no sensible default vintage).
    `dataset` selects the ACS table set: ``acs5`` (5-year, supports small
    geographies incl. census tracts) or ``acs1`` (1-year, geographies with
    65k+ population only). Defaults to ``acs5`` so tract queries work.
    """
    params: dict = {"get": variables, "for": geo_for}
    if geo_in:
        params["in"] = geo_in
    if cfg.CENSUS_API_KEY:
        params["key"] = cfg.CENSUS_API_KEY
    url = f"{BASE}/{year}/acs/{dataset}"
    try:
        # follow_redirects=False so a key failure surfaces as a 3xx to an
        # HTML page rather than a JSON-parse error after following the hop.
        r = await get_client().get(url, params=params, follow_redirects=False)
        if r.is_redirect and any(
            page in r.headers.get("location", "") for page in _KEY_ERROR_PAGES
        ):
            return {"error": True, "source": "census",
                    "upstream_status": r.status_code,
                    "message": ("Census rejected the API key (redirected to "
                                f"{r.headers.get('location')}). Set a valid "
                                "CENSUS_API_KEY; sign up at "
                                "https://api.census.gov/data/key_signup.html")}
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return _error("census", exc)


async def population_by_state(year: int) -> UpstreamJSON:
    """Shortcut: population by state."""
    return await acs(year, "NAME,B01001_001E", "state:*")


async def income_by_state(year: int) -> UpstreamJSON:
    """Shortcut: median household income by state."""
    return await acs(year, "NAME,B19013_001E", "state:*")
