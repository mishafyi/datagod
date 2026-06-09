"""OpenFEMA — Disaster declarations, assistance, flood claims."""

from . import UpstreamJSON, safe_get

BASE = "https://www.fema.gov/api/open/v2"


async def disasters(top: int = 10) -> UpstreamJSON:
    """Recent disaster declarations."""
    return await safe_get(f"{BASE}/DisasterDeclarationsSummaries", "fema", params={
        "$top": top, "$orderby": "declarationDate desc",
    })


async def grants(top: int = 10) -> UpstreamJSON:
    """Hazard mitigation grants."""
    return await safe_get(
        f"{BASE}/HazardMitigationGrantProgramDisasterSummaries", "fema",
        params={"$top": top},
    )


async def flood_claims(top: int = 10) -> UpstreamJSON:
    """NFIP flood insurance claims."""
    return await safe_get(f"{BASE}/FimaNfipClaims", "fema", params={"$top": top})
