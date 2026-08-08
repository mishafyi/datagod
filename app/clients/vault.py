"""FBI Vault (vault.fbi.gov) — served through the Wayback Machine mirror.

vault.fbi.gov 403s every server-side client (same Akamai wall as cia.gov —
see _wayback.py), so this client reads the archive's captures. The Vault is a
Plone site: a subject page (e.g. /cointel-pro) lists sub-folders
(contenttype-folder) and file pages (contenttype-file); a file page carries
the document PDF. This client parses one page per call — walking a subject's
tree is the caller's loop.

No per-query search (Vault search pages aren't archived per-query); start from
the curated registry of famous subjects in `subjects()`.
"""

import re

from selectolax.parser import HTMLParser

from . import UpstreamJSON
from ._wayback import fetch_capture

ORIGIN = "https://vault.fbi.gov"
BODY_CAP = 16000

# Famous Vault subjects, path → display name. Static on purpose: no listable
# index behind the bot wall. A 404 from wayback just means "pick another".
SUBJECTS = {
    "cointel-pro": "COINTELPRO",
    "roswell": "Roswell UFO incident",
    "majestic-12": "Majestic 12",
    "unusual-phenomena": "Unusual Phenomena (UFO files)",
    "watergate": "Watergate",
    "solo": "Operation SOLO",
    "venona": "VENONA",
    "rosenberg-case": "The Rosenberg Case",
    "alger-hiss": "Alger Hiss",
    "julius-and-ethel-rosenberg": "Julius and Ethel Rosenberg",
    "martin-luther-king-jr": "Martin Luther King, Jr.",
    "the-ku-klux-klan": "The Ku Klux Klan",
}


def _err(status: int, message: str) -> dict:
    return {"error": True, "source": "vault", "upstream_status": status, "message": message}


def _clean(s: str | None) -> str | None:
    return re.sub(r"\s+", " ", s).strip() if s else None


def _unwrap(href: str) -> str:
    m = re.match(r"^(?:https?://web\.archive\.org)?/web/[^/]+/(https?://.+)$", href)
    return m.group(1) if m else href


def _entries(t: HTMLParser, kind: str) -> list[dict]:
    """Plone listing entries by content type ('folder' or 'file')."""
    out: list[dict] = []
    seen: set[str] = set()
    for a in t.css(f"a.contenttype-{kind}"):
        href = _unwrap(a.attributes.get("href", ""))
        title = _clean(a.text())
        m = re.match(rf"^{re.escape(ORIGIN)}/(.+?)/?$", href)
        if not m or not title or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        out.append({"path": m.group(1), "title": title, "url": f"{ORIGIN}/{m.group(1)}"})
    return out


async def page(path: str) -> UpstreamJSON:
    """One Vault page by path (subject, folder or file — the Vault nests):
    title, description text, sub-folders, file pages, and any PDF links."""
    url = f"{ORIGIN}/{path.strip('/')}"
    html, snapshot, err = await fetch_capture(url)
    if err:
        return _err(err["upstream_status"], err["message"])
    t = HTMLParser(html)
    h1 = t.css_first("h1")
    desc = t.css_first("#content .documentDescription, #content .description, #content p")
    pdfs: list[dict] = []
    seen: set[str] = set()
    for a in t.css("a[href]"):
        href = _unwrap(a.attributes.get("href", ""))
        if ("/at_download/" in href or href.lower().endswith(".pdf")) and href not in seen:
            seen.add(href)
            pdfs.append({"title": _clean(a.text()) or href.rsplit("/", 1)[-1], "url": href})
    return {
        "path": path.strip("/"),
        "title": _clean(h1.text()) if h1 else None,
        "description": (_clean(desc.text(separator=" ")) or "")[:BODY_CAP] or None if desc else None,
        "folders": _entries(t, "folder"),
        "files": _entries(t, "file"),
        "pdfs": pdfs[:20],
        "url": url,
        "archived_url": snapshot,
    }


async def subjects() -> UpstreamJSON:
    """The curated registry of famous Vault subjects (static)."""
    return {"subjects": [{"path": p, "name": n, "url": f"{ORIGIN}/{p}"}
                         for p, n in SUBJECTS.items()]}
