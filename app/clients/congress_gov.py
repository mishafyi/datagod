"""Congress.gov — Bills, votes, members, committees."""

from . import UpstreamJSON, safe_get
from ..config import cfg

BASE = "https://api.congress.gov/v3"


async def bills(limit: int = 10, congress: int = 0) -> UpstreamJSON:
    """Recent bills."""
    url = f"{BASE}/bill/{congress}" if congress else f"{BASE}/bill"
    return await safe_get(url, "congress", params={
        "api_key": cfg.CONGRESS_API_KEY, "limit": limit, "format": "json",
    })


async def bill_detail(congress: int, bill_type: str, number: int) -> UpstreamJSON:
    """Get specific bill details."""
    return await safe_get(
        f"{BASE}/bill/{congress}/{bill_type}/{number}", "congress",
        params={"api_key": cfg.CONGRESS_API_KEY, "format": "json"},
    )


async def members(limit: int = 10) -> UpstreamJSON:
    """List members of Congress."""
    return await safe_get(f"{BASE}/member", "congress", params={
        "api_key": cfg.CONGRESS_API_KEY, "limit": limit, "format": "json",
    })


async def votes(chamber: str = "house", congress: int = 119,
                limit: int = 10) -> UpstreamJSON:
    """Recent House votes. Note: only 'house' chamber is supported by Congress.gov API."""
    return await safe_get(f"{BASE}/house-vote/{congress}", "congress", params={
        "api_key": cfg.CONGRESS_API_KEY, "limit": limit, "format": "json",
    })
