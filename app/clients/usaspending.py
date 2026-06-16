"""USAspending — Federal contracts, grants, loans. $6T+/year."""

from . import UpstreamJSON, safe_get, safe_post

BASE = "https://api.usaspending.gov/api/v2"


async def agencies() -> UpstreamJSON:
    """List all toptier agencies with budget data."""
    return await safe_get(f"{BASE}/references/toptier_agencies/", "usaspending")


# Contract award type codes. USAspending's spending_by_award REJECTS mixing award
# groups in one query — contracts (A,B,C,D) cannot be combined with grants (02,03,04,05)
# — so the default is contracts-only; pass award_type_codes="02,03,04,05" to query grants.
DEFAULT_AWARD_TYPE_CODES: list[str] = ["A", "B", "C", "D"]


async def search_awards(keywords: list[str], start_date: str = "", end_date: str = "",
                        limit: int = 10, page: int = 1, sort: str = "Award Amount",
                        order: str = "desc",
                        award_type_codes: list[str] | str | None = None) -> UpstreamJSON:
    """Search spending by award."""
    if isinstance(award_type_codes, str):
        codes = [c.strip() for c in award_type_codes.split(",") if c.strip()]
    else:
        codes = award_type_codes
    filters: dict = {
        "keywords": keywords,
        "award_type_codes": codes or DEFAULT_AWARD_TYPE_CODES,
    }
    period: dict = {}
    if start_date:
        period["start_date"] = start_date
    if end_date:
        period["end_date"] = end_date
    if period:
        filters["time_period"] = [period]
    return await safe_post(f"{BASE}/search/spending_by_award/", "usaspending", json={
        "filters": filters,
        "fields": ["Award ID", "Recipient Name", "Award Amount",
                   "Awarding Agency", "Start Date", "End Date"],
        "limit": limit, "page": page, "sort": sort, "order": order,
        "subawards": False,
    })


async def spending_by_agency(fiscal_year: str, quarter: str = "1") -> UpstreamJSON:
    """Total spending by agency."""
    return await safe_post(f"{BASE}/spending/", "usaspending", json={
        "type": "agency",
        "filters": {"fy": fiscal_year, "quarter": quarter},
    })
