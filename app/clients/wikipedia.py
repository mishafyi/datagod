"""Wikipedia — page summaries, whole articles, full-text search, and Wikimedia pageview counts.

Wikimedia asks for a descriptive User-Agent on all API traffic; the pageviews
endpoint outright requires one. Sent on every call below. Wikimedia also
throttles bursts with 429 (sometimes 503) — an agent reading several articles
in a row meets it — so every call waits one out (Retry-After, else BACKOFF)
before it gives up.
"""

from urllib.parse import quote

from ..resilience import get_with_retry
from . import UpstreamJSON, _error, error_dict, json_or_error

REST_BASE = "https://en.wikipedia.org/api/rest_v1"
ACTION_BASE = "https://en.wikipedia.org/w/api.php"
PAGEVIEWS_BASE = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
HEADERS = {"User-Agent": "DataGod/1.0 (https://github.com/mishafyi/datagod)"}
# Seconds to wait after a 429/503 that names no Retry-After; a named wait is capped at MAX_WAIT.
BACKOFF = (2.0, 5.0)
MAX_WAIT = 20.0


async def _get(url: str, params: dict | None) -> UpstreamJSON:
    """GET with the polite User-Agent, waiting out a 429/503 before each retry."""
    try:
        r = await get_with_retry(url, backoff=BACKOFF, max_wait=MAX_WAIT,
                                 headers=HEADERS, params=params)
        r.raise_for_status()
    except Exception as exc:
        return _error("wikipedia", exc)
    return json_or_error(r, "wikipedia")


async def summary(title: str) -> UpstreamJSON:
    """Lead-section summary of one page. Use underscores in `title`
    (e.g. Albert_Einstein) — exact titles avoid an unfollowed redirect."""
    return await _get(f"{REST_BASE}/page/summary/{quote(title, safe='')}", None)


async def search(q: str, limit: int = 10) -> UpstreamJSON:
    """Full-text article search (MediaWiki action API); hits under query.search."""
    return await _get(ACTION_BASE, {
        "action": "query", "list": "search", "format": "json",
        "srsearch": q, "srlimit": limit,
    })


async def article(title: str) -> UpstreamJSON:
    """The WHOLE article as plain text (TextExtracts), redirects followed: under
    query.pages[0].extract, section headings kept as `== Heading ==`. The summary
    endpoint stops at the lead; this is what reading the article means. A title
    with no article answers 404, as /summary does."""
    data = await _get(ACTION_BASE, {
        "action": "query", "prop": "extracts", "explaintext": 1, "exsectionformat": "wiki",
        "redirects": 1, "format": "json", "formatversion": 2, "titles": title,
    })
    if isinstance(data, dict) and not data.get("error"):
        pages = data.get("query", {}).get("pages", [])
        if not pages or pages[0].get("missing") or pages[0].get("invalid"):
            return error_dict("wikipedia", 404, f"No English Wikipedia article titled {title!r}")
    return data


async def pageviews(title: str, start: str, end: str) -> UpstreamJSON:
    """Daily pageview counts for one article; `start`/`end` are YYYYMMDD."""
    url = (f"{PAGEVIEWS_BASE}/en.wikipedia/all-access/all-agents/"
           f"{quote(title, safe='')}/daily/{start}00/{end}00")
    return await _get(url, None)
