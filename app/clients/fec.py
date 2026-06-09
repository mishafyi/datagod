"""FEC — Campaign finance. Candidates, donations, expenditures."""

from . import UpstreamJSON, safe_get
from ..config import cfg

BASE = "https://api.open.fec.gov/v1"


async def candidates(office: str = "", state: str = "",
                     per_page: int = 10) -> UpstreamJSON:
    """Search candidates. office: P(resident), S(enate), H(ouse)."""
    params: dict = {"api_key": cfg.FEC_API_KEY, "per_page": per_page}
    if office:
        params["office"] = office
    if state:
        params["state"] = state
    return await safe_get(f"{BASE}/candidates/", "fec", params=params)


async def contributions(contributor_name: str = "", candidate_id: str = "",
                        per_page: int = 10) -> UpstreamJSON:
    """Search individual contributions."""
    params: dict = {"api_key": cfg.FEC_API_KEY, "per_page": per_page}
    if contributor_name:
        params["contributor_name"] = contributor_name
    if candidate_id:
        params["candidate_id"] = candidate_id
    return await safe_get(f"{BASE}/schedules/schedule_a/", "fec", params=params)


async def candidate_totals(office: str = "P", election_year: int = 2024,
                           per_page: int = 10) -> UpstreamJSON:
    """Candidate financial totals sorted by receipts."""
    return await safe_get(f"{BASE}/candidates/totals/", "fec", params={
        "api_key": cfg.FEC_API_KEY, "office": office,
        "election_year": election_year, "sort": "-receipts", "per_page": per_page,
    })
