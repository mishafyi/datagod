"""OpenFEMA — Disaster declarations, assistance, flood claims.

Dataset versions move independently (see /api/open/v1/OpenFemaDataSets):
NFIP claims are `NfipClaims` v3 (the old `FimaNfipClaims` v2 now 404s) and the
HMGP disaster summaries are v3 (v2 was frozen 2026-08-31, deprecated 2026-10-15).
"""

from . import UpstreamJSON, safe_get

API = "https://www.fema.gov/api/open"
BASE = f"{API}/v2"


def _quoted(value: str) -> str:
    """An OData string literal: single quotes doubled, so input can't end the literal."""
    return "'" + value.replace("'", "''") + "'"


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
        clauses.append(f"state eq {_quoted(state)}")
    if declared_since:
        clauses.append(f"declarationDate ge {_quoted(declared_since)}")
    if clauses:
        params["$filter"] = " and ".join(clauses)
    return await safe_get(f"{BASE}/DisasterDeclarationsSummaries", "fema", params=params)


async def grants(top: int = 10) -> UpstreamJSON:
    """Hazard mitigation grants, most-recent first."""
    return await safe_get(
        f"{API}/v3/HazardMitigationGrantProgramDisasterSummaries", "fema",
        params={"$top": top, "$orderby": "declarationDate desc"},
    )


async def flood_claims(top: int = 10) -> UpstreamJSON:
    """NFIP flood insurance claims, most-recent first."""
    return await safe_get(
        f"{API}/v3/NfipClaims", "fema",
        params={"$top": top, "$orderby": "dateOfLoss desc"},
    )
