"""Integration test for the arXiv search client.

Exercises `app.clients.arxiv` directly against the LIVE arXiv API
(https://export.arxiv.org/api/query) — no running server required, but it
needs outbound network access to export.arxiv.org.

    .venv/bin/python tests/test_arxiv.py

What it verifies (and documents):

  * `search("electron")` returns a non-empty `entries` list and a sane
    `total_results` count, with each record carrying the fields the client
    promises (arxiv_id, title, authors, pdf_url, primary_category).
  * `max_results` caps the number of returned entries.
  * `sort_by="submittedDate"` ascending vs descending flips the date order —
    the oldest-first run starts earlier than the newest-first run.
  * `get_by_id("0706.0001v1")` returns exactly one matching entry, with its DOI
    and journal_ref populated from the arXiv extension elements. (A bare id like
    "0706.0001" resolves to the LATEST version — v2 here — whose metadata can
    differ: v2 of this paper drops the DOI but keeps the journal_ref, so the test
    pins the version to deterministically exercise the DOI field.)
  * A malformed id surfaces the standard error-dict (upstream HTTP 400), not a
    raised exception.

The arXiv corpus grows over time, so checks use RELATIVE comparisons and
field presence, never absolute counts. The client self-throttles to arXiv's
1-request-per-3-seconds courtesy limit, so this suite takes ~20s to run.
Exits non-zero if any check fails.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.clients import arxiv  # noqa: E402

# A stable, well-known paper. v1 carries both a DOI and a journal reference;
# the bare id "0706.0001" would resolve to the latest version (v2), so the test
# pins v1 to make the DOI assertion deterministic.
KNOWN_ID = "0706.0001v1"


async def run() -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []

    def record(name: str, ok: bool, detail: str) -> None:
        checks.append((name, ok, detail))

    # --- basic search returns entries + well-formed records ----------------
    res = await arxiv.search("electron", max_results=10)
    ok_search = isinstance(res, dict) and not res.get("error") and bool(res.get("entries"))
    total = res.get("total_results") if isinstance(res, dict) else None
    record("search('electron') returns entries",
           ok_search and isinstance(total, int) and total > 0,
           f"entries={len(res.get('entries', [])) if isinstance(res, dict) else 'n/a'} total_results={total}")

    first = (res.get("entries") or [{}])[0] if isinstance(res, dict) else {}
    ok_fields = (bool(first.get("arxiv_id")) and bool(first.get("title"))
                 and isinstance(first.get("authors"), list) and bool(first.get("authors"))
                 and (first.get("pdf_url") or "").endswith(("pdf", first.get("arxiv_id", "\0")))
                 and bool(first.get("primary_category")))
    record("search records carry promised fields",
           ok_fields,
           f"id={first.get('arxiv_id')!r} authors={len(first.get('authors', []))} "
           f"cat={first.get('primary_category')!r} pdf={'yes' if first.get('pdf_url') else 'no'}")

    # --- max_results caps the count ----------------------------------------
    small = await arxiv.search("electron", max_results=3)
    n_small = len(small.get("entries", [])) if isinstance(small, dict) else -1
    record("max_results caps returned entries",
           n_small == 3,
           f"max_results=3 -> {n_small} entries")

    # --- sort order flips the date ordering --------------------------------
    asc = await arxiv.search("electron", max_results=5,
                             sort_by="submittedDate", sort_order="ascending")
    desc = await arxiv.search("electron", max_results=5,
                              sort_by="submittedDate", sort_order="descending")
    asc_first = (asc.get("entries") or [{}])[0].get("published") if isinstance(asc, dict) else None
    desc_first = (desc.get("entries") or [{}])[0].get("published") if isinstance(desc, dict) else None
    record("sort_by submittedDate orders by date (asc oldest, desc newest)",
           bool(asc_first) and bool(desc_first) and asc_first < desc_first,
           f"ascending first={asc_first} < descending first={desc_first}")

    # --- get_by_id returns exactly one matching record ---------------------
    one = await arxiv.get_by_id(KNOWN_ID)
    entries = one.get("entries", []) if isinstance(one, dict) else []
    ok_one = (isinstance(one, dict) and not one.get("error") and len(entries) == 1
              and entries[0].get("arxiv_id", "").startswith(KNOWN_ID)
              and bool(entries[0].get("doi")) and bool(entries[0].get("journal_ref")))
    record(f"get_by_id('{KNOWN_ID}') returns one record with DOI",
           ok_one,
           f"entries={len(entries)} id={entries[0].get('arxiv_id') if entries else None!r} "
           f"doi={entries[0].get('doi') if entries else None!r}")

    # --- a bare id resolves to the single latest version -------------------
    bare = await arxiv.get_by_id("0706.0001")
    bare_entries = bare.get("entries", []) if isinstance(bare, dict) else []
    bare_id = bare_entries[0].get("arxiv_id") if bare_entries else None
    record("bare id resolves to one (latest-version) record",
           len(bare_entries) == 1 and (bare_id or "").startswith("0706.0001v"),
           f"entries={len(bare_entries)} id={bare_id!r}")

    # --- malformed id surfaces the error-dict (HTTP 400), never raises -----
    bad = await arxiv.get_by_id("this-is-not-an-arxiv-id")
    record("malformed id -> error-dict (upstream 400)",
           isinstance(bad, dict) and bad.get("error") is True and bad.get("upstream_status") == 400,
           f"error={bad.get('error') if isinstance(bad, dict) else 'n/a'} "
           f"status={bad.get('upstream_status') if isinstance(bad, dict) else 'n/a'}")

    return checks


def main() -> None:
    checks = asyncio.run(run())
    width = max(len(name) for name, _, _ in checks)
    passed = 0
    print(f"\narXiv client behavior — {len(checks)} checks\n" + "=" * (width + 12))
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name.ljust(width)}  {detail}")
        passed += ok
    print("=" * (width + 12))
    print(f"{passed}/{len(checks)} passed")
    sys.exit(0 if passed == len(checks) else 1)


if __name__ == "__main__":
    main()
