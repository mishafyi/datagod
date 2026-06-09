"""House Financial Disclosures — Member and candidate stock trades."""

import re

from . import get_client

BASE = "https://disclosures-clerk.house.gov"


async def search_members(last_name: str = "", filing_year: str = "",
                         state: str = "", district: str = "") -> list[dict]:
    """Search House member financial disclosures. Returns parsed results."""
    return await _post_and_parse(
        "FinancialDisclosure/ViewMemberSearchResult",
        {"LastName": last_name, "FilingYear": filing_year,
         "State": state, "District": district},
    )


async def search_candidates(last_name: str = "", election_year: str = "",
                            state: str = "", district: str = "") -> list[dict]:
    """Search House candidate financial disclosures."""
    return await _post_and_parse(
        "FinancialDisclosure/ViewCandidateSearchResult",
        {"LastName": last_name, "ElectionYear": election_year,
         "State": state, "District": district},
    )


async def _post_and_parse(path: str, data: dict) -> list[dict]:
    try:
        r = await get_client().post(
            f"{BASE}/{path}", data=data,
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        r.raise_for_status()
        return _parse_html_table(r.text)
    except Exception:
        return []


def _parse_html_table(html: str) -> list[dict]:
    """Parse the HTML table response into structured JSON."""
    rows = re.findall(r'<tr role="row">(.*?)</tr>', html, re.DOTALL)
    results: list[dict] = []
    for row in rows:
        href = re.search(r'href="([^"]+)"', row)
        name = re.search(r'target="_blank">([^<]+)</a>', row)
        cells = re.findall(r'data-label="([^"]+)"[^>]*>\s*(?:<a[^>]*>[^<]*</a>|([^<]*))', row)
        entry: dict = {}
        for label, value in cells:
            entry[label.lower().replace(" ", "_")] = value.strip() if value.strip() else None
        if name:
            entry["name"] = name.group(1).strip()
        if href:
            entry["pdf_url"] = f"{BASE}/{href.group(1)}"
        results.append(entry)
    return results
