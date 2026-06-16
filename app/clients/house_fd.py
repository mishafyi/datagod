"""House Financial Disclosures — Member and candidate stock trades."""

import re

from . import UpstreamJSON, get_client

BASE = "https://disclosures-clerk.house.gov"


async def search_members(last_name: str = "", filing_year: str = "",
                         state: str = "", district: str = "") -> UpstreamJSON:
    """Search House member financial disclosures. Returns parsed results
    (list of filings) or the error-dict contract on failure."""
    return await _post_and_parse(
        "FinancialDisclosure/ViewMemberSearchResult",
        {"LastName": last_name, "FilingYear": filing_year,
         "State": state, "District": district},
    )


async def search_candidates(last_name: str = "", election_year: str = "",
                            state: str = "", district: str = "") -> UpstreamJSON:
    """Search House candidate financial disclosures. Returns parsed results
    (list of filings) or the error-dict contract on failure."""
    return await _post_and_parse(
        "FinancialDisclosure/ViewCandidateSearchResult",
        {"LastName": last_name, "ElectionYear": election_year,
         "State": state, "District": district},
    )


async def fetch_pdf(path: str) -> bytes | dict:
    """Fetch a member/candidate disclosure PDF by its url or relative path.

    `path` may be an absolute disclosures-clerk.house.gov URL or a relative
    path like `public_disc/ptr-pdfs/2024/20024542.pdf`. These PDFs are served
    with no auth, no session, no CSRF. Returns the raw PDF bytes on success,
    or the error-dict contract on failure."""
    url = path if path.startswith("http") else f"{BASE}/{path.lstrip('/')}"
    try:
        r = await get_client().get(url)
        r.raise_for_status()
        return r.content
    except Exception as exc:
        upstream_status = getattr(getattr(exc, "response", None), "status_code", 0)
        return {"error": True, "source": "house_fd",
                "upstream_status": upstream_status, "message": str(exc)}


async def _post_and_parse(path: str, data: dict) -> UpstreamJSON:
    try:
        r = await get_client().post(
            f"{BASE}/{path}", data=data,
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        r.raise_for_status()
        return _parse_html_table(r.text)
    except Exception as exc:
        upstream_status = getattr(getattr(exc, "response", None), "status_code", 0)
        return {"error": True, "source": "house_fd",
                "upstream_status": upstream_status, "message": str(exc)}


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
