"""Smithsonian Open Access (EDAN) — 11M+ museum, library & archive records across SI units.

Standard REST API on api.data.gov. Auth via api_key query param. Response envelope is
{"status", "responseCode", "response": {"rows": [...], "facets", "rowCount", "message"}}.
"""

from . import UpstreamJSON, safe_get
from ..config import cfg

BASE = "https://api.si.edu/openaccess/api/v1.0"


async def search(q: str = "", start: int = 0, rows: int = 10,
                 sort: str = "", obj_type: str = "") -> UpstreamJSON:
    """Full-text search of Open Access content. sort: relevancy|newest|updated|random."""
    params: dict = {"api_key": cfg.SMITHSONIAN_API_KEY, "start": start, "rows": rows}
    if q:
        params["q"] = q
    if sort:
        params["sort"] = sort
    if obj_type:
        params["type"] = obj_type
    return await safe_get(f"{BASE}/search", "smithsonian", params=params)


async def content(object_id: str) -> UpstreamJSON:
    """Full metadata record for a single object by its EDAN id."""
    return await safe_get(f"{BASE}/content/{object_id}", "smithsonian",
                          params={"api_key": cfg.SMITHSONIAN_API_KEY})


async def category_search(category: str, q: str = "", start: int = 0, rows: int = 10,
                          sort: str = "", obj_type: str = "") -> UpstreamJSON:
    """Search within a category: art_design | history_culture | science_technology.

    sort: relevancy|newest|updated|random. obj_type forwards to the upstream `type` param.
    """
    params: dict = {"api_key": cfg.SMITHSONIAN_API_KEY, "start": start, "rows": rows}
    if q:
        params["q"] = q
    if sort:
        params["sort"] = sort
    if obj_type:
        params["type"] = obj_type
    return await safe_get(f"{BASE}/category/{category}/search", "smithsonian", params=params)


async def terms(category: str) -> UpstreamJSON:
    """List controlled-vocabulary terms for a category (culture, topic, place,
    object_type, data_source, date, name, set_name, ...)."""
    return await safe_get(f"{BASE}/terms/{category}", "smithsonian",
                          params={"api_key": cfg.SMITHSONIAN_API_KEY})


async def stats() -> UpstreamJSON:
    """Open Access dataset statistics (record counts, CC0 totals by unit)."""
    return await safe_get(f"{BASE}/stats", "smithsonian",
                          params={"api_key": cfg.SMITHSONIAN_API_KEY})
