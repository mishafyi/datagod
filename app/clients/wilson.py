"""Wilson Center Digital Archive — served from a LOCAL mirror, not the live API.

The live site (digitalarchive.wilsoncenter.org) is no longer queried. This client reads
a SQLite + FTS5 index (data/wilson.db) built by scripts/build_wilson_index.py from a
downloaded mirror of 16,756 declassified document pages. Build the index once before use.

sqlite3 is synchronous; calls are dispatched via asyncio.to_thread to keep the loop free.
"""

import asyncio
import json
import math
import re
import sqlite3
from pathlib import Path

from . import UpstreamJSON

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "wilson.db"
MIRROR_REL = "data/digitalarchive wilsoncenter"
_BUILD_HINT = "Local index missing — build it: .venv/bin/python scripts/build_wilson_index.py"


def _err(status: int, message: str) -> dict:
    return {"error": True, "source": "wilson", "upstream_status": status, "message": message}


def _connect() -> sqlite3.Connection:
    db = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


def _fts_match(q: str) -> str:
    """Turn free text into a safe FTS5 query: each token quoted, implicit AND."""
    return " ".join(f'"{tok}"' for tok in re.findall(r"\w+", q))


def _thin(r: sqlite3.Row) -> dict:
    return {"slug": r["slug"], "title": r["title"], "record_id": r["record_id"],
            "node_id": r["node_id"], "subjects": json.loads(r["subjects"]),
            "download_available": bool(r["download_available"])}


def _search(q: str, page: int, items_per_page: int) -> UpstreamJSON:
    if not DB_PATH.exists():
        return _err(503, _BUILD_HINT)
    db = _connect()
    try:
        offset = (page - 1) * items_per_page
        match = _fts_match(q)
        if match:
            total = db.execute(
                "SELECT count(*) FROM documents_fts WHERE documents_fts MATCH ?", (match,)
            ).fetchone()[0]
            slugs = [s["slug"] for s in db.execute(
                "SELECT slug FROM documents_fts WHERE documents_fts MATCH ? "
                "ORDER BY rank LIMIT ? OFFSET ?", (match, items_per_page, offset))]
        else:
            total = db.execute("SELECT count(*) FROM documents").fetchone()[0]
            slugs = [s["slug"] for s in db.execute(
                "SELECT slug FROM documents ORDER BY title LIMIT ? OFFSET ?",
                (items_per_page, offset))]
        rows = []
        for slug in slugs:
            r = db.execute(
                "SELECT slug,title,record_id,node_id,subjects,download_available "
                "FROM documents WHERE slug=?", (slug,)).fetchone()
            if r:
                rows.append(_thin(r))
        pages = math.ceil(total / items_per_page) if items_per_page else 0
        return {"list": rows,
                "pagination": {"page": page, "itemsPerPage": items_per_page,
                               "totalItems": total, "totalPages": pages}}
    finally:
        db.close()


def _document(slug: str) -> UpstreamJSON:
    if not DB_PATH.exists():
        return _err(503, _BUILD_HINT)
    db = _connect()
    try:
        r = db.execute("SELECT * FROM documents WHERE slug=?", (slug,)).fetchone()
        if not r:
            return _err(404, f"No document with slug '{slug}' in the local mirror")
        node_id = r["node_id"]
        return {
            "slug": r["slug"], "node_id": node_id, "record_id": r["record_id"],
            "title": r["title"], "info": json.loads(r["info"]),
            "subjects": json.loads(r["subjects"]), "names": json.loads(r["names"]),
            "download": {
                "available": bool(r["download_available"]), "id": node_id,
                "mirror_path": f"{MIRROR_REL}/downloads.tar.zst::downloads/document/{node_id}/download",
            },
        }
    finally:
        db.close()


async def search_documents(q: str = "", page: int = 1, items_per_page: int = 10) -> UpstreamJSON:
    """Full-text search the local Wilson mirror. Returns {list, pagination}."""
    return await asyncio.to_thread(_search, q, page, items_per_page)


async def document(slug: str) -> UpstreamJSON:
    """Full local record for one document slug, including download availability."""
    return await asyncio.to_thread(_document, slug)
