"""NARA — US National Archives Catalog (all record groups + the 14 presidential libraries).

Unofficial: uses the public `catalog.archives.gov/proxy` gateway that the catalog's own
web app calls. No API key is needed — the proxy injects NARA's key server-side — but
browser-like fetch headers are required or the edge serves the SPA's HTML instead of JSON.
Response envelope: {"body": {"hits": {"total": {...}, "hits": [{"_source": {"record": {...}}}]}}}.
Results live in body.hits.hits[]._source.record; total in body.hits.total.value.
"""

from . import UpstreamJSON, safe_get

BASE = "https://catalog.archives.gov/proxy"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://catalog.archives.gov/",
    "Origin": "https://catalog.archives.gov",
    "X-Requested-With": "XMLHttpRequest",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Dest": "empty",
}


async def search(q: str = "", page: int = 1, available_online: bool = False,
                 type_of_materials: str = "", level_of_description: str = "") -> UpstreamJSON:
    """Full-text search the National Archives Catalog. Covers every record group, including
    all 14 presidential libraries (scope to one with query terms). `q` supports AND/OR/NOT,
    wildcards (*) and exact "phrases". Fixed page size of 20; `page` is 1-based.
    NOTE: the public /proxy gateway rejects a `limit` param (serves SPA HTML), so paging
    is page-only at 20 results/page.

    Optional frontend filters forwarded to the proxy (each sent only when set):
    `available_online=True` → `availableOnline=true` (records with viewable digital objects),
    `type_of_materials` → `typeOfMaterials`, `level_of_description` → `levelOfDescription`.
    These mirror filters the catalog SPA uses; the proxy may ignore them (no-op is acceptable)."""
    params: dict = {"page": page}
    if q:
        params["q"] = q
    if available_online:
        params["availableOnline"] = "true"
    if type_of_materials:
        params["typeOfMaterials"] = type_of_materials
    if level_of_description:
        params["levelOfDescription"] = level_of_description
    return await safe_get(f"{BASE}/records/search", "nara", params=params, headers=HEADERS)


async def record(na_id: str) -> UpstreamJSON:
    """A single catalog record by its National Archives Identifier (NAID)."""
    return await safe_get(f"{BASE}/records/search", "nara",
                          params={"naId": na_id}, headers=HEADERS)
