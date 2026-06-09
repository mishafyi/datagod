"""USAspending — Federal contracts, grants, loans. $6T+/year."""

from . import UpstreamJSON, safe_get, safe_post

BASE = "https://api.usaspending.gov/api/v2"


async def agencies() -> UpstreamJSON:
    """List all toptier agencies with budget data."""
    return await safe_get(f"{BASE}/references/toptier_agencies/", "usaspending")


async def search_awards(keywords: list[str], start_date: str = "", end_date: str = "",
                        limit: int = 10, sort: str = "Award Amount", order: str = "desc",
                        award_type_codes: list[str] | None = None) -> UpstreamJSON:
    """Search spending by award."""
    filters: dict = {
        "keywords": keywords,
        "award_type_codes": award_type_codes or ["A", "B", "C", "D"],
    }
    if start_date and end_date:
        filters["time_period"] = [{"start_date": start_date, "end_date": end_date}]
    return await safe_post(f"{BASE}/search/spending_by_award/", "usaspending", json={
        "filters": filters,
        "fields": ["Award ID", "Recipient Name", "Award Amount",
                   "Awarding Agency", "Start Date", "End Date"],
        "limit": limit, "page": 1, "sort": sort, "order": order,
        "subawards": False,
    })


async def spending_by_agency(fiscal_year: str = "2025", quarter: str = "1") -> UpstreamJSON:
    """Total spending by agency."""
    return await safe_post(f"{BASE}/spending/", "usaspending", json={
        "type": "agency",
        "filters": {"fy": fiscal_year, "quarter": quarter},
    })
