#!/usr/bin/env python3
"""Smoke-test every DataGod endpoint against the live API and print a grouped
pass/fail table.

    .venv/bin/python tests/test_all_endpoints.py

PASS = HTTP 200 + meta.status "success". FAIL = anything else (unless expected).
JEFS /register is skipped (it launches an interactive browser + reCAPTCHA).
Target host: $DATAGOD_BASE_URL or the production URL.
"""

import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
BASE = os.getenv("DATAGOD_BASE_URL", "https://datagod.example.com")
HEADERS = {"X-API-Key": os.getenv("DATAGOD_API_KEY", "")}

rows: list[tuple[str, str, object, str, str]] = []


def find(obj: object, key: str) -> object:
    """First truthy value for `key` anywhere in a nested dict/list."""
    stack = [obj]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            if node.get(key):
                return node[key]
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return None


def hit(method: str, path: str, group: str, expect_error: bool = False, timeout: int = 45) -> object:
    label = f"{method} {path.split('?')[0]}"
    try:
        r = httpx.request(method, BASE + path, headers=HEADERS, timeout=timeout, follow_redirects=True)
        mstatus, note, body = None, "", None
        try:
            body = r.json()
            if isinstance(body, dict):
                mstatus = (body.get("meta") or {}).get("status")
                if mstatus == "error":
                    note = str(body.get("error"))[:64]
        except Exception:
            note = "non-JSON body"
        ok = r.status_code == 200 and mstatus == "success"
        verdict = "PASS" if ok else ("EXP-ERR" if expect_error else "FAIL")
        rows.append((group, label, r.status_code, verdict, note))
        return body
    except Exception as exc:
        rows.append((group, label, "ERR", "EXP-ERR" if expect_error else "FAIL", str(exc)[:64]))
        return None


def skip(group: str, label: str, note: str) -> None:
    rows.append((group, label, "—", "SKIP", note))


# ── Health ──
hit("GET", "/", "Health")
hit("GET", "/health", "Health")
# ── FRED ──
hit("GET", "/fred/GDP?limit=2", "FRED")
hit("GET", "/fred?q=unemployment&limit=2", "FRED")
# ── EDGAR ──
hit("GET", "/edgar/company/AAPL", "EDGAR")
hit("GET", "/edgar/financials/AAPL", "EDGAR", timeout=60)
hit("GET", "/edgar/concept/AAPL/Revenues", "EDGAR")
hit("GET", "/edgar/frames/Revenues?period=CY2023", "EDGAR", timeout=60)
hit("GET", "/edgar/search?q=artificial+intelligence&limit=2", "EDGAR")
# ── Nasdaq ──
hit("GET", "/nasdaq/quote/AAPL", "Nasdaq")
hit("GET", "/nasdaq/price/AAPL", "Nasdaq")
hit("GET", "/nasdaq/history/AAPL?fromdate=2026-01-01&todate=2026-02-01&limit=5", "Nasdaq")
hit("GET", "/nasdaq/dividends/AAPL", "Nasdaq")
# ── yfinance ──
for ep in ["info", "history", "news", "recommendations", "holders", "financials", "dividends", "options"]:
    hit("GET", f"/yfinance/{ep}/AAPL", "yfinance", timeout=60)
# ── USAspending ──
hit("GET", "/usaspending/agencies", "USAspending")
hit("GET", "/usaspending/search?q=defense&limit=2", "USAspending")
hit("GET", "/usaspending/by-agency", "USAspending")
# ── Census (known: needs a valid key) ──
hit("GET", "/census/population", "Census")
hit("GET", "/census/income", "Census")
hit("GET", "/census/acs", "Census")
# ── BLS ──
hit("GET", "/bls/CUUR0000SA0", "BLS")
# ── Treasury ──
hit("GET", "/treasury/debt?limit=2", "Treasury")
hit("GET", "/treasury/rates?limit=2", "Treasury")
hit("GET", "/treasury/exchange?limit=2", "Treasury")
# ── FEC ──
hit("GET", "/fec/candidates?limit=2", "FEC")
hit("GET", "/fec/contributions?name=trump&limit=2", "FEC")  # schedule_a 400s without a filter
hit("GET", "/fec/totals?limit=2", "FEC")
# ── Congress ──
hit("GET", "/congress/bills?limit=2", "Congress")
hit("GET", "/congress/bill/118/hr/1", "Congress")
hit("GET", "/congress/members?limit=2", "Congress")
hit("GET", "/congress/votes?limit=2", "Congress")
# ── FDA ──
hit("GET", "/fda/drug-events?limit=2", "FDA")
hit("GET", "/fda/drug-recalls?limit=2", "FDA")
hit("GET", "/fda/food-recalls?limit=2", "FDA")
# ── Clinical Trials ──
hit("GET", "/clinical-trials?condition=cancer&limit=2", "ClinicalTrials")
hit("GET", "/clinical-trials/NCT04267848", "ClinicalTrials")
# ── EIA ──
hit("GET", "/eia", "EIA")
hit("GET", "/eia/gas-prices?limit=2", "EIA")
hit("GET", "/eia/electricity?limit=2", "EIA")
hit("GET", "/eia/petroleum/pri/gnd?limit=2", "EIA")
# ── FEMA ──
hit("GET", "/fema/disasters?limit=2", "FEMA")
hit("GET", "/fema/grants?limit=2", "FEMA")
hit("GET", "/fema/flood-claims?limit=2", "FEMA")
# ── Federal Register (resolve a doc number) ──
fr = hit("GET", "/federal-register?limit=2", "FederalRegister")
docnum = find(fr, "document_number")
hit("GET", f"/federal-register/{docnum}", "FederalRegister") if docnum else skip(
    "FederalRegister", "GET /federal-register/{doc_number}", "no doc number from list")
# ── JEFS (register is interactive → skip; facets/search need a session) ──
skip("JEFS", "POST /jefs/register", "interactive browser + reCAPTCHA")
hit("GET", "/jefs/facets", "JEFS", expect_error=True)
hit("GET", "/jefs/search", "JEFS", expect_error=True)
hit("POST", "/jefs/reset", "JEFS")
# ── House Disclosures ──
hit("GET", "/house-disclosures/members?last_name=pelosi", "HouseFD")
hit("GET", "/house-disclosures/candidates?last_name=smith", "HouseFD")
# ── NARA (resolve a naId) ──
na = hit("GET", "/nara/search?q=war&page=1", "NARA")
naid = find(na, "naId")
hit("GET", f"/nara/record/{naid}", "NARA") if naid else skip("NARA", "GET /nara/record/{na_id}", "no naId from search")
# ── NSArchive (scrape; resolve a doc id) ──
nsr = hit("GET", "/nsarchive/search?q=cuba", "NSArchive")
nsdoc = find(nsr, "path")  # the document id is the full "{id}-{slug}" path, not bare "id"
hit("GET", f"/nsarchive/document/{nsdoc}", "NSArchive") if nsdoc else skip(
    "NSArchive", "GET /nsarchive/document/{doc_id}", "no doc id from search")
# ── Smithsonian (resolve an EDAN id) ──
sm = hit("GET", "/smithsonian/search?q=apollo&rows=2", "Smithsonian")
sid = find(sm, "id")
hit("GET", f"/smithsonian/object/{sid}", "Smithsonian") if sid else skip(
    "Smithsonian", "GET /smithsonian/object/{id}", "no id from search")
hit("GET", "/smithsonian/category/art_design/search?q=painting&rows=2", "Smithsonian")
hit("GET", "/smithsonian/terms/culture", "Smithsonian")
hit("GET", "/smithsonian/stats", "Smithsonian")
# ── Wilson Center (local SQLite mirror; not shipped in the Docker image) ──
wd = hit("GET", "/wilson/documents?q=korea&page=1", "Wilson")
slug = find(wd, "slug")
hit("GET", f"/wilson/document/{slug}", "Wilson") if slug else skip(
    "Wilson", "GET /wilson/document/{slug}", "no slug from search")
# ── Cross-Reference (fans out to several upstreams) ──
hit("GET", "/cross-reference/company/apple", "CrossRef", timeout=90)
hit("GET", "/cross-reference/politician/pelosi", "CrossRef", timeout=90)
# ── Admin ──
hit("POST", "/admin/clear-cache", "Admin")

# ── Report ──
icons = {"PASS": "✓", "FAIL": "✗", "EXP-ERR": "~", "SKIP": "-"}
print(f"\nTarget: {BASE}\n" + "=" * 78)
current = None
for group, label, code, verdict, note in rows:
    if group != current:
        current = group
        print(f"\n## {group}")
    print(f"  {icons[verdict]} {str(code):>4}  {label:46} {note}")
counts = {k: sum(1 for r in rows if r[3] == k) for k in icons}
print("\n" + "=" * 78)
print(f"PASS {counts['PASS']}   FAIL {counts['FAIL']}   EXPECTED-ERR {counts['EXP-ERR']}   "
      f"SKIP {counts['SKIP']}   / {len(rows)} endpoints")
sys.exit(1 if counts["FAIL"] else 0)
