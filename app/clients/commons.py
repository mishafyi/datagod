"""Wikimedia Commons — video-file search with direct URLs + per-file license.

License varies per file (CC-BY / CC-BY-SA / PD) — the caller must read
imageinfo[0].extmetadata (LicenseShortName, Artist) and credit accordingly.
Wikimedia asks for a descriptive User-Agent on all API traffic.
"""

from . import UpstreamJSON, safe_get

BASE = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "DataGod/1.0 (github.com/mishafyi/datagod)"}


async def search(q: str, limit: int = 10) -> UpstreamJSON:
    """Search video files (File: namespace). Pages under query.pages{}, each
    with imageinfo[0].url (direct file URL), size, mime, and extmetadata."""
    return await safe_get(BASE, "commons", headers=HEADERS, params={
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"filetype:video {q}", "gsrlimit": limit, "gsrnamespace": 6,
        "prop": "imageinfo", "iiprop": "url|extmetadata|size|mime",
    })
