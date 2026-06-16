"""Standalone test for the Google Scholar (vendored sortgs) client.

Exercises `app.clients.scholar.search` directly against the LIVE Google Scholar
HTML search — no running server required, but it needs outbound network access
to scholar.google.com.

    .venv/bin/python tests/test_scholar.py

KNOWN-BRITTLE BY DESIGN. Google Scholar aggressively blocks automated access
(CAPTCHA / HTTP 429 / IP block). This test makes ONE small real search and then
classifies the outcome into exactly one of three buckets:

  * DATA    — results came back; we assert they are well-formed (each record has
              a Title and an int Citations field, plus the count/keyword wrapper).
  * BLOCKED — the wrapper returned the error-dict (robot/CAPTCHA wall, 429, etc.).
              This is an EXPECTED condition from a non-residential IP, NOT a
              failure: the contract is "return the error-dict gracefully", and
              that is exactly what happened.
  * EMPTY   — a clean page with zero results (also acceptable; treated like a
              soft outcome).

The test FAILS (exit 1) only if the wrapper violates its contract — e.g. it
raises instead of returning the error-dict, returns a malformed shape, or
returns records missing required fields. Being blocked is reported, not failed.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.clients import scholar  # noqa: E402

KEYWORD = "transformer neural network"
NRESULTS = 5


def _check_data(res: dict) -> None:
    """Assert a successful response is well-formed. Raises AssertionError on violation."""
    assert "results" in res and "count" in res and "keyword" in res, (
        f"success dict missing wrapper keys: {sorted(res)}")
    assert res["keyword"] == KEYWORD, f"keyword echoed wrong: {res['keyword']!r}"
    results = res["results"]
    assert isinstance(results, list), f"results is not a list: {type(results)}"
    assert res["count"] == len(results), (
        f"count {res['count']} != len(results) {len(results)}")
    assert len(results) <= NRESULTS, f"got more than nresults: {len(results)}"
    for i, rec in enumerate(results):
        assert isinstance(rec, dict), f"record {i} not a dict: {type(rec)}"
        assert rec.get("Title"), f"record {i} has no Title: {rec}"
        assert isinstance(rec.get("Citations"), int), (
            f"record {i} Citations not an int: {rec.get('Citations')!r}")
        # Rank/Year are also expected to be present and integral.
        assert isinstance(rec.get("Rank"), int), f"record {i} missing int Rank: {rec}"


async def main() -> int:
    print(f"Querying Google Scholar: keyword={KEYWORD!r} nresults={NRESULTS} ...")
    try:
        res = await scholar.search(KEYWORD, nresults=NRESULTS, sort_by="Citations",
                                   start_year=None, end_year=None)
    except Exception as exc:  # noqa: BLE001 — the wrapper must NOT raise; if it does, that's a hard fail.
        print(f"FAIL: scholar.search raised instead of returning the error-dict: "
              f"{type(exc).__name__}: {exc}")
        return 1

    if not isinstance(res, dict):
        print(f"FAIL: scholar.search returned non-dict: {type(res)} -> {res!r}")
        return 1

    # ---- BLOCKED bucket: contract-compliant error-dict ----
    if res.get("error") is True:
        for key in ("source", "upstream_status", "message"):
            if key not in res:
                print(f"FAIL: error-dict missing '{key}': {res}")
                return 1
        if res["source"] != "scholar":
            print(f"FAIL: error-dict source is {res['source']!r}, expected 'scholar'")
            return 1
        print("BLOCKED (expected, known-brittle): Google Scholar refused the "
              "automated request and the wrapper returned the error-dict cleanly.")
        print(f"  upstream_status={res['upstream_status']}  message={res['message']!r}")
        print("PASS: wrapper honored its contract (graceful error-dict, no crash).")
        return 0

    # ---- DATA / EMPTY buckets ----
    try:
        _check_data(res)
    except AssertionError as exc:
        print(f"FAIL: malformed success response: {exc}")
        return 1

    if res["count"] == 0:
        print("EMPTY (acceptable): Scholar returned a page with zero parsable "
              "results (likely a soft block or no matches).")
        print("PASS: response shape is well-formed.")
        return 0

    print(f"DATA: got {res['count']} well-formed result(s). Top entries:")
    for rec in res["results"][:NRESULTS]:
        print(f"  [#{rec.get('Rank')}] cit={rec.get('Citations')} "
              f"({rec.get('Year')}) {str(rec.get('Title'))[:70]!r}")
    print("PASS: live Google Scholar returned well-formed, ranked data.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
