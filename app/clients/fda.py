"""openFDA — Drug adverse events, recalls, devices."""

from . import UpstreamJSON, safe_get

BASE = "https://api.fda.gov"


async def _search(path: str, search: str, limit: int) -> UpstreamJSON:
    params: dict = {"limit": limit}
    if search:
        params["search"] = search
    return await safe_get(f"{BASE}/{path}", "fda", params=params)


async def drug_events(search: str = "", limit: int = 10) -> UpstreamJSON:
    """Drug adverse events. search: e.g. 'patient.drug.openfda.brand_name:aspirin'."""
    return await _search("drug/event.json", search, limit)


async def drug_recalls(search: str = "", limit: int = 10) -> UpstreamJSON:
    """Drug enforcement/recall actions."""
    return await _search("drug/enforcement.json", search, limit)


async def food_recalls(search: str = "", limit: int = 10) -> UpstreamJSON:
    """Food enforcement/recall actions."""
    return await _search("food/enforcement.json", search, limit)
