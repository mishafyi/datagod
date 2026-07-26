"""Wikipedia — page summaries, full-text search, and Wikimedia pageview counts.

Wikimedia asks for a descriptive User-Agent on all API traffic; the pageviews
endpoint outright requires one. Sent on every call below.
"""

from urllib.parse import quote

from . import UpstreamJSON, safe_get

REST_BASE = "https://en.wikipedia.org/api/rest_v1"
ACTION_BASE = "https://en.wikipedia.org/w/api.php"
PAGEVIEWS_BASE = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
HEADERS = {"User-Agent": "DataGod/1.0 (github.com/mishafyi/datagod)"}


async def summary(title: str) -> UpstreamJSON:
    """Lead-section summary of one page. Use underscores in `title`
    (e.g. Albert_Einstein) — exact titles avoid an unfollowed redirect."""
    return await safe_get(f"{REST_BASE}/page/summary/{quote(title, safe='')}",
                          "wikipedia", headers=HEADERS)


async def search(q: str, limit: int = 10) -> UpstreamJSON:
    """Full-text article search (MediaWiki action API); hits under query.search."""
    return await safe_get(ACTION_BASE, "wikipedia", headers=HEADERS, params={
        "action": "query", "list": "search", "format": "json",
        "srsearch": q, "srlimit": limit,
    })


async def pageviews(title: str, start: str, end: str) -> UpstreamJSON:
    """Daily pageview counts for one article; `start`/`end` are YYYYMMDD."""
    url = (f"{PAGEVIEWS_BASE}/en.wikipedia/all-access/all-agents/"
           f"{quote(title, safe='')}/daily/{start}00/{end}00")
    return await safe_get(url, "wikipedia", headers=HEADERS)
