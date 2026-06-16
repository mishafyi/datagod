"""OpenFEMA — Disaster declarations, assistance, flood claims."""

from . import UpstreamJSON, safe_get

BASE = "https://www.fema.gov/api/open/v2"


async def disasters(top: int = 10, state: str = "",
                    declared_since: str = "") -> UpstreamJSON:
    """Recent disaster declarations, optionally filtered by state and date.

    `state` is a two-letter USPS code (e.g. ``CA``); `declared_since` is an
    ISO-8601 date (e.g. ``2024-01-01``) matched against ``declarationDate``.
    Both are forwarded as an OpenFEMA OData ``$filter``.
    """
    params: dict = {"$top": top, "$orderby": "declarationDate desc"}
    clauses: list[str] = []
    if state:
        clauses.append(f"state eq '{state}'")
    if declared_since:
        clauses.append(f"declarationDate ge '{declared_since}'")
    if clauses:
        params["$filter"] = " and ".join(clauses)
    return await safe_get(f"{BASE}/DisasterDeclarationsSummaries", "fema", params=params)


async def grants(top: int = 10) -> UpstreamJSON:
    """Hazard mitigation grants, most-recent first."""
    return await safe_get(
        f"{BASE}/HazardMitigationGrantProgramDisasterSummaries", "fema",
        params={"$top": top, "$orderby": "declarationDate desc"},
    )


async def flood_claims(top: int = 10) -> UpstreamJSON:
    """NFIP flood insurance claims, most-recent first."""
    return await safe_get(
        f"{BASE}/FimaNfipClaims", "fema",
        params={"$top": top, "$orderby": "dateOfLoss desc"},
    )
