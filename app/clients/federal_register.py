"""Federal Register — Rules, executive orders, agency notices."""

from . import UpstreamJSON, safe_get

BASE = "https://www.federalregister.gov/api/v1"


async def documents(per_page: int = 10, doc_type: str = "", agency: str = "",
                    term: str = "", order: str = "newest") -> UpstreamJSON:
    """Search Federal Register documents."""
    params: dict = {"per_page": per_page, "order": order}
    if doc_type:
        params["conditions[type][]"] = doc_type
    if agency:
        params["conditions[agencies][]"] = agency
    if term:
        params["conditions[term]"] = term
    return await safe_get(f"{BASE}/documents.json", "federal_register", params=params)


async def document(doc_number: str) -> UpstreamJSON:
    """Get a specific document by number."""
    return await safe_get(f"{BASE}/documents/{doc_number}.json", "federal_register")
