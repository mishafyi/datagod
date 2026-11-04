"""House Financial Disclosures — Member and candidate stock trades."""

from urllib.parse import urljoin, urlsplit

from selectolax.lexbor import LexborHTMLParser

from . import UpstreamJSON, _error, error_dict, get_client

BASE = "https://disclosures-clerk.house.gov"
_HOST = urlsplit(BASE).hostname


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


def _pdf_url(path: str) -> str | None:
    """Absolute https URL for `path` on the disclosures host, or None when `path`
    points anywhere else — the route must not fetch arbitrary URLs (SSRF)."""
    parts = urlsplit(urljoin(f"{BASE}/", path.strip()))
    if parts.scheme not in ("http", "https") or parts.hostname != _HOST or parts.port:
        return None
    return parts._replace(scheme="https").geturl()


async def fetch_pdf(path: str) -> bytes | dict:
    """Fetch a member/candidate disclosure PDF by its url or relative path.

    `path` may be an absolute disclosures-clerk.house.gov URL or a relative
    path like `public_disc/ptr-pdfs/2024/20024542.pdf`. These PDFs are served
    with no auth, no session, no CSRF. Returns the raw PDF bytes on success,
    or the error-dict contract on failure (400 for a URL on any other host)."""
    url = _pdf_url(path)
    if url is None:
        return error_dict("house_fd", 400,
                          f"path must be a {_HOST} document path or URL; got {path!r}")
    try:
        r = await get_client().get(url)
        r.raise_for_status()
        return r.content
    except Exception as exc:
        return _error("house_fd", exc)


async def _post_and_parse(path: str, data: dict) -> UpstreamJSON:
    try:
        r = await get_client().post(
            f"{BASE}/{path}", data=data,
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        r.raise_for_status()
        return _parse_html_table(r.text)
    except Exception as exc:
        return _error("house_fd", exc)


def _parse_html_table(html: str) -> list[dict]:
    """Parse the search-result table into records: one per filing row, keyed by
    each cell's data-label (name, office, filing_year/election_year, filing),
    plus the filing's absolute pdf_url. The header row has no cells and is skipped."""
    results: list[dict] = []
    for row in LexborHTMLParser(html).css("tr"):
        cells = row.css("td[data-label]")
        if not cells:
            continue
        entry: dict = {}
        for cell in cells:
            label = (cell.attributes.get("data-label") or "").strip().lower().replace(" ", "_")
            if label:
                entry[label] = " ".join(cell.text(separator=" ").split()) or None
        link = row.css_first("a[href]")
        href = (link.attributes.get("href") or "") if link else ""
        if href:
            entry["pdf_url"] = urljoin(f"{BASE}/", href)
        results.append(entry)
    return results
