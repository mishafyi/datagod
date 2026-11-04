"""Congress.gov — Bills, votes, members, committees."""

from datetime import date

from ..config import cfg
from . import UpstreamJSON, safe_get

BASE = "https://api.congress.gov/v3"


async def bills(limit: int = 10, congress: int = 0, offset: int = 0) -> UpstreamJSON:
    """Recent bills."""
    url = f"{BASE}/bill/{congress}" if congress else f"{BASE}/bill"
    return await safe_get(url, "congress", params={
        "api_key": cfg.CONGRESS_API_KEY, "limit": limit, "offset": offset,
        "format": "json",
    })


async def bill_detail(congress: int, bill_type: str, number: int) -> UpstreamJSON:
    """Get specific bill details."""
    return await safe_get(
        f"{BASE}/bill/{congress}/{bill_type}/{number}", "congress",
        params={"api_key": cfg.CONGRESS_API_KEY, "format": "json"},
    )


async def members(limit: int = 10, offset: int = 0) -> UpstreamJSON:
    """List members of Congress."""
    return await safe_get(f"{BASE}/member", "congress", params={
        "api_key": cfg.CONGRESS_API_KEY, "limit": limit, "offset": offset,
        "format": "json",
    })


def current_congress(today: date | None = None) -> int:
    """The Congress in session on `today`: the 1st began in 1789 and each runs
    two years from January 3 of an odd year (2025-01-03 → the 119th)."""
    today = today or date.today()
    year = today.year - 1 if (today.month, today.day) < (1, 3) else today.year
    return (year - 1789) // 2 + 1


async def votes(congress: int | None = None, limit: int = 10,
                offset: int = 0) -> UpstreamJSON:
    """Recent House roll-call votes, by default of the Congress now in session.
    Congress.gov v3 exposes House votes only (`house-vote/{congress}`); there is
    no Senate-vote endpoint."""
    congress = congress or current_congress()
    return await safe_get(f"{BASE}/house-vote/{congress}", "congress", params={
        "api_key": cfg.CONGRESS_API_KEY, "limit": limit, "offset": offset,
        "format": "json",
    })
