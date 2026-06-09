#!/usr/bin/env python
"""Build data/wilson.db (SQLite + FTS5) from the local Wilson Center Digital Archive mirror.

One-time preprocessing: streams documents.tar.zst, parses each Drupal HTML document page
into structured fields, and writes a SQLite database the wilson.py client reads at runtime.

Usage: .venv/bin/python scripts/build_wilson_index.py
"""

import json
import math
import re
import sqlite3
import subprocess
import tarfile
from pathlib import Path

from selectolax.parser import HTMLParser

ROOT = Path(__file__).resolve().parent.parent
MIRROR = ROOT / "data" / "digitalarchive wilsoncenter"
DOCS_TAR = MIRROR / "documents.tar.zst"
DL_URLS = MIRROR / "download-urls.txt.zst"
DB_PATH = ROOT / "data" / "wilson.db"

NODE_RE = re.compile(r'"currentPath"\s*:\s*"node\\?/(\d+)"')


def load_download_ids() -> set[str]:
    """Numeric document ids that have a downloadable file, from download-urls.txt.zst."""
    out = subprocess.run(["zstd", "-dc", str(DL_URLS)], capture_output=True, text=True).stdout
    return set(re.findall(r"/document/(\d+)/download", out))


def parse_doc(slug: str, html: str) -> dict:
    t = HTMLParser(html)

    def tx(node) -> str:
        return node.text(strip=True) if node else ""

    title = tx(t.css_first("h1")) or tx(t.css_first("title")).split("|")[0].strip()
    node_m = NODE_RE.search(html)
    node_id = node_m.group(1) if node_m else ""

    info: dict[str, str] = {}
    for ib in t.css(".information-block"):
        label = tx(ib.css_first(".sub-title"))
        full = ib.text(strip=True)
        value = full[len(label):].strip() if label and full.startswith(label) else full
        if label:
            info[label] = value

    subjects = [s for s in (tx(p) for p in t.css(".pill-subject")) if s]
    names = [n for n in (tx(p) for p in t.css(".pill")) if n]
    record_id = info.get("Record ID", "")

    main = t.css_first("main") or t.css_first(".region-content") or t.css_first("#content")
    main_text = main.text(separator=" ", strip=True)[:20000] if main else ""
    body = " \n".join([title, " ".join(subjects), " ".join(names),
                       " ".join(info.values()), main_text])

    return {"slug": slug, "node_id": node_id, "record_id": record_id, "title": title,
            "info": info, "subjects": subjects, "names": names, "body": body}


def main() -> None:
    print(f"[*] download ids ...")
    dl_ids = load_download_ids()
    print(f"    {len(dl_ids)} documents have downloads")

    DB_PATH.unlink(missing_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
        CREATE TABLE documents(
            slug TEXT PRIMARY KEY, node_id TEXT, record_id TEXT, title TEXT,
            info TEXT, subjects TEXT, names TEXT,
            download_available INTEGER, download_id TEXT
        );
        CREATE VIRTUAL TABLE documents_fts USING fts5(slug UNINDEXED, title, body);
    """)

    proc = subprocess.Popen(["zstd", "-dc", str(DOCS_TAR)], stdout=subprocess.PIPE)
    tar = tarfile.open(fileobj=proc.stdout, mode="r|")
    n, errors = 0, 0
    for member in tar:
        if not member.isfile() or "/document/" not in member.name:
            continue
        slug = member.name.split("/document/", 1)[1]
        if not slug:
            continue
        try:
            html = tar.extractfile(member).read().decode("utf-8", "replace")
            r = parse_doc(slug, html)
            avail = 1 if r["node_id"] in dl_ids else 0
            db.execute("INSERT OR REPLACE INTO documents VALUES (?,?,?,?,?,?,?,?,?)",
                       (r["slug"], r["node_id"], r["record_id"], r["title"],
                        json.dumps(r["info"], ensure_ascii=False),
                        json.dumps(r["subjects"], ensure_ascii=False),
                        json.dumps(r["names"], ensure_ascii=False),
                        avail, r["node_id"]))
            db.execute("INSERT INTO documents_fts (slug, title, body) VALUES (?,?,?)",
                       (r["slug"], r["title"], r["body"]))
            n += 1
            if n % 2000 == 0:
                print(f"    indexed {n} ...")
                db.commit()
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"    ! parse error on {slug}: {type(e).__name__}: {e}")
    db.commit()
    proc.wait()

    total = db.execute("SELECT count(*) FROM documents").fetchone()[0]
    with_dl = db.execute("SELECT count(*) FROM documents WHERE download_available=1").fetchone()[0]
    db.close()
    print(f"[done] indexed {n} documents ({errors} errors); db has {total} rows, "
          f"{with_dl} with downloads -> {DB_PATH}")


if __name__ == "__main__":
    main()
