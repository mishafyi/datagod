"""NASA Image and Video Library — public-domain space/science media (images.nasa.gov).

Keyless. Everything is public domain; crediting "NASA" is courteous.
"""

from urllib.parse import quote

from . import UpstreamJSON, safe_get

BASE = "https://images-api.nasa.gov"


async def search(q: str, media_type: str = "video", year_start: str = "",
                 year_end: str = "", page: int = 1, page_size: int = 10) -> UpstreamJSON:
    """Search the library. media_type: video | image | audio. Hits under
    collection.items[]; each item's data[0].nasa_id feeds asset()."""
    params: dict = {"q": q, "media_type": media_type, "page": page,
                    "page_size": page_size}
    if year_start:
        params["year_start"] = year_start
    if year_end:
        params["year_end"] = year_end
    return await safe_get(f"{BASE}/search", "nasa_images", params=params)


async def asset(nasa_id: str) -> UpstreamJSON:
    """All downloadable renditions for one nasa_id (mp4 sizes, srt, thumbs) —
    direct file URLs under collection.items[].href."""
    return await safe_get(f"{BASE}/asset/{quote(nasa_id, safe='')}", "nasa_images")
