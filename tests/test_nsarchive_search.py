"""Integration test for the NSArchive (National Security Archive, GWU) search client.

Exercises `app.clients.nsarchive` directly against the LIVE Virtual Reading Room
(https://nsarchive.gwu.edu) — no running server required, but it needs outbound
network access to nsarchive.gwu.edu.

    .venv/bin/python tests/test_nsarchive_search.py

What it documents and verifies (findings from reverse-engineering the search):

  * The Reading Room's `search_api_fulltext` GET param defaults to **OR** across
    the entered words — NOT "all of the words" (AND) as the site's on-page Search
    Tips claim. (The site's search *form* applies AND via extra config that the
    raw GET param does not inherit.)
  * Explicit Boolean operators DO work through the GET param: `AND`, `OR`, `NOT`,
    parentheses, `*` wildcards, and "exact phrase" quoting.
  * Date bounding via `field_date[max]` / `field_date[min]` works; `sort_by` is
    ignored (results are always newest-first).

  => To find specific (e.g. Cold-War) documents, use distinctive **exact phrases**
     and/or explicit **AND** + a `field_date[max]` bound. Plain multi-word queries
     only surface the newest FOIA releases.

Totals drift as the archive grows, so checks use RELATIVE comparisons, never
absolute counts. Exits non-zero if any check fails.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.clients import nsarchive  # noqa: E402
from app.clients import get_client  # noqa: E402

# A document known to be in the Reading Room (NSDD-32, CIA Electronic Reading Room).
KNOWN_DOC = "20310-national-security-archive-doc-25-national"


async def _total(q: str) -> int:
    res = await nsarchive.search(q=q, page=1)
    assert isinstance(res, dict) and not res.get("error"), f"search {q!r} errored: {res}"
    total = res.get("total")
    assert isinstance(total, int), f"search {q!r} returned no total: {res}"
    return total


async def _raw_total_dates(q: str, date_max: str) -> tuple[int, list[str]]:
    """Hit the listing directly with a date bound; return (total, ISO dates present)."""
    params = {"search_api_fulltext": q, "field_date[max]": date_max}
    r = await get_client().get(f"{nsarchive.BASE}/virtual-reading-room",
                               params=params, headers=nsarchive.HEADERS)
    r.raise_for_status()
    res = nsarchive._parse_listing(r.text, 1)
    dates = [h["date"] for h in res.get("results", []) if h.get("date")]
    return res.get("total"), dates


async def run() -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []

    def record(name: str, ok: bool, detail: str) -> None:
        checks.append((name, ok, detail))

    # --- operator semantics ------------------------------------------------
    nixon = await _total("Nixon")
    mao = await _total("Mao")
    default = await _total("Nixon Mao")
    and_ = await _total("Nixon AND Mao")
    or_ = await _total("Nixon OR Mao")
    not_ = await _total("Nixon NOT Kissinger")

    record("default multi-word is OR (not AND)",
           default >= max(nixon, mao) and abs(default - or_) <= max(2, or_ // 20),
           f"'Nixon'={nixon} 'Mao'={mao} 'Nixon Mao'={default} 'Nixon OR Mao'={or_}")
    record("explicit AND narrows vs default",
           and_ < default,
           f"'Nixon AND Mao'={and_} < 'Nixon Mao'={default}")
    record("explicit NOT reduces vs single term",
           not_ < nixon,
           f"'Nixon NOT Kissinger'={not_} < 'Nixon'={nixon}")

    # --- wildcard ----------------------------------------------------------
    afg = await _total("Afghanistan")
    afg_w = await _total("Afghan*")
    record("wildcard '*' broadens", afg_w >= afg, f"'Afghan*'={afg_w} >= 'Afghanistan'={afg}")

    # --- exact phrase ------------------------------------------------------
    phrase = await _total('"Nickel Grass"')
    loose = await _total("Nickel Grass")
    record("exact-phrase quoting narrows", 0 < phrase < loose,
           f"'\"Nickel Grass\"'={phrase} (loose 'Nickel Grass'={loose})")

    # --- date bounding -----------------------------------------------------
    bounded_total, bounded_dates = await _raw_total_dates("National Security Decision Directive",
                                                          "1990-12-31")
    over = [d for d in bounded_dates if d[:4].isdigit() and int(d[:4]) > 1990]
    record("field_date[max] bounds results",
           bounded_total > 0 and not over,
           f"total={bounded_total}, dated hits all <=1990 ({len(bounded_dates)} checked, {len(over)} over)")

    # --- single-document fetch --------------------------------------------
    doc = await nsarchive.document(KNOWN_DOC)
    ok_doc = (isinstance(doc, dict) and not doc.get("error")
              and "National Security Decision Directive 32" in (doc.get("title") or "")
              and (doc.get("pdf_url") or "").endswith(".pdf"))
    record("document() fetches + parses a known record", ok_doc,
           f"title={ (doc.get('title') or '')[:60]!r} pdf={'yes' if doc.get('pdf_url') else 'no'}")

    return checks


def main() -> None:
    checks = asyncio.run(run())
    width = max(len(name) for name, _, _ in checks)
    passed = 0
    print(f"\nNSArchive search behavior — {len(checks)} checks\n" + "=" * (width + 12))
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name.ljust(width)}  {detail}")
        passed += ok
    print("=" * (width + 12))
    print(f"{passed}/{len(checks)} passed")
    sys.exit(0 if passed == len(checks) else 1)


if __name__ == "__main__":
    main()
