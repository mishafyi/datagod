"""UK National Archives — Discovery API (official, keyless JSON).

Discovery indexes 32M+ record descriptions held at Kew and beyond, including the
declassified intelligence and military series: KV (Security Service/MI5),
HS (Special Operations Executive), DEFE (Ministry of Defence), CAB (Cabinet
Office/JIC), WO/ADM/AIR (services), PREM (Prime Minister's Office). Descriptions
are open; many records link to digitised downloads.

Official API base: https://discovery.nationalarchives.gov.uk/API — plain GET,
no key, JSON with Accept header. Routes pass the upstream JSON through unchanged.
"""

from . import get_client, UpstreamJSON, _error

BASE = "https://discovery.nationalarchives.gov.uk/API"
HEADERS = {"Accept": "application/json"}


async def search(q: str, page: int = 1, per_page: int = 20, series: str = "") -> UpstreamJSON:
    """Full-text search of Discovery record descriptions.

    `series` narrows to a lettercode/series (e.g. KV, HS, DEFE, CAB, PREM) via
    the upstream's `sps.departments` filter — `sps.recordSeries` looks right but
    matches nothing (verified live 2026-08-06). Paging is 1-based.
    """
    params: dict = {
        "sps.searchQuery": q,
        "sps.resultsPageSize": per_page,
        "sps.page": page,
    }
    if series:
        params["sps.departments"] = series
    try:
        r = await get_client().get(f"{BASE}/search/records", params=params, headers=HEADERS)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return _error("tna", exc)


async def record(record_id: str) -> UpstreamJSON:
    """Full details for one record by Discovery id (the `id` field of search results)."""
    try:
        r = await get_client().get(f"{BASE}/records/v1/details/{record_id}", headers=HEADERS)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return _error("tna", exc)
