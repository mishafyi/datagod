"""Live-upstream tests for the intel-archive clients: cia, frus, tna.

No server needed — calls the client modules directly (network required).
Run: .venv/bin/python tests/test_intel_archives.py
Wayback throttles hard; the cia tests tolerate a throttled miss but fail on
parse regressions when a page does come back.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.clients import cia, frus, tna  # noqa: E402

PASS, FAIL = [], []


def check(name: str, ok: bool, detail: str = "") -> None:
    (PASS if ok else FAIL).append(name)
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail[:140]}")


async def main() -> None:
    # ── TNA ──
    r = await tna.search("KGB defector", per_page=5)
    check("tna.search returns records", isinstance(r, dict) and len(r.get("records", [])) > 0,
          f"count={r.get('count')}")
    r2 = await tna.search("KGB defector", page=2, per_page=5)
    first = r.get("records", [{}])[0].get("id")
    second = r2.get("records", [{}])[0].get("id")
    check("tna.search paging distinct", bool(first) and first != second, f"{first} vs {second}")
    rs = await tna.search("double agent", per_page=5, series="KV")
    refs = [x.get("reference", "") for x in rs.get("records", [])]
    check("tna.search series=KV filters", bool(refs) and all(str(x).startswith("KV") for x in refs),
          ",".join(map(str, refs[:3])))
    if first:
        det = await tna.record(str(first))
        check("tna.record detail", isinstance(det, dict) and not det.get("error")
              and (det.get("scopeContent") is not None or det.get("citableReference")),
              str(det.get("citableReference")))

    # ── FRUS ──
    r = await frus.search("covert action Chile")
    check("frus.search returns results", len(r.get("results", [])) > 0, f"total={r.get('total')}")
    hit = next((x for x in r.get("results", []) if x.get("volume") and x.get("doc")), None)
    check("frus.search parses volume/doc", hit is not None, str(hit)[:100] if hit else "")
    if hit:
        d = await frus.document(hit["volume"], hit["doc"])
        check("frus.document body", not d.get("error") and d.get("body") and len(d["body"]) > 200,
              f"title={d.get('title')}")

    # ── CIA (wayback-mirrored; tolerate throttling) ──
    d = await cia.document("cia-rdp96-00788r001700210016-5")
    if d.get("error") and d.get("upstream_status") in (0, 429, 503):
        check("cia.document (wayback throttled — soft pass)", True, d.get("message", ""))
    else:
        check("cia.document title", bool(d.get("title")) and "gateway" in d["title"].lower(),
              str(d.get("title")))
        check("cia.document pdf", bool(d.get("pdf_url")), str(d.get("pdf_url"))[:80])
    c = await cia.collection("stargate")
    if c.get("error") and c.get("upstream_status") in (0, 429, 503):
        check("cia.collection (wayback throttled — soft pass)", True, c.get("message", ""))
    else:
        check("cia.collection documents", len(c.get("documents", [])) > 0,
              f"n={len(c.get('documents', []))} title={c.get('title')}")
    reg = await cia.collections()
    check("cia.collections registry", len(reg.get("collections", [])) >= 8)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    sys.exit(1 if FAIL else 0)


asyncio.run(main())
