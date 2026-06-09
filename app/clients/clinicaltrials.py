"""ClinicalTrials.gov — 500K+ clinical trials worldwide."""

from . import UpstreamJSON, safe_get

BASE = "https://clinicaltrials.gov/api/v2"


async def search(condition: str = "", intervention: str = "",
                 status: str = "", page_size: int = 10) -> UpstreamJSON:
    """Search clinical trials."""
    params: dict = {"pageSize": page_size}
    if condition:
        params["query.cond"] = condition
    if intervention:
        params["query.intr"] = intervention
    if status:
        params["filter.overallStatus"] = status
    return await safe_get(f"{BASE}/studies", "clinicaltrials", params=params)


async def study(nct_id: str) -> UpstreamJSON:
    """Get a specific study by NCT ID."""
    return await safe_get(f"{BASE}/studies/{nct_id}", "clinicaltrials")
