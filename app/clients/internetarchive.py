"""Internet Archive — keyless item search + per-item metadata with download paths.

Video-harvest targets are the public-domain movie collections (prelinger,
newsreels…). License is PER ITEM — read `licenseurl` from the search fields or
the item metadata before reuse; download URLs are
https://archive.org/download/{identifier}/{file.name}.
"""

from urllib.parse import quote

from . import UpstreamJSON, safe_get

BASE = "https://archive.org"
FIELDS = ["identifier", "title", "year", "licenseurl", "mediatype"]


async def search(q: str, rows: int = 10, page: int = 1) -> UpstreamJSON:
    """Advanced search; hits under response.docs[]. Free-text `q` is scoped to
    mediatype:movies unless the query already constrains mediatype."""
    query = q if "mediatype:" in q else f"({q}) AND mediatype:movies"
    return await safe_get(f"{BASE}/advancedsearch.php", "internetarchive", params={
        "q": query, "fl[]": FIELDS, "rows": rows, "page": page, "output": "json",
    })


async def item(identifier: str) -> UpstreamJSON:
    """Full item metadata incl. files[] (name, format, size) and licenseurl."""
    return await safe_get(f"{BASE}/metadata/{quote(identifier, safe='')}",
                          "internetarchive")
