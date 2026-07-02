#!/usr/bin/env python3
"""Smoke-test every DataGod endpoint against the live API and print a grouped
pass/fail table.

    .venv/bin/python tests/test_all_endpoints.py

PASS = HTTP 200 + meta.status "success". FAIL = anything else (unless expected).
JEFS (2026-06-11) and Wilson (2026-07-02) are disabled on the API and skipped here.
Target host: $DATAGOD_BASE_URL, defaulting to http://localhost:8000.
"""

import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
BASE = os.getenv("DATAGOD_BASE_URL", "http://localhost:8000")
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


def hit(method: str, path: str, group: str, expect_error: bool = False, timeout: int = 45, **kwargs) -> object:
    label = f"{method} {path.split('?')[0]}"
    try:
        r = httpx.request(method, BASE + path, headers=HEADERS, timeout=timeout, follow_redirects=True, **kwargs)
        mstatus, note, body = None, "", None
        is_json = "application/json" in r.headers.get("content-type", "")
        try:
            body = r.json()
            if isinstance(body, dict):
                mstatus = (body.get("meta") or {}).get("status")
                if mstatus == "error":
                    note = str(body.get("error"))[:64]
        except Exception:
            note = f"raw [{r.headers.get('content-type', '').split(';')[0]}, {len(r.content)}b]"
        # raw-bytes routes (edgar/document, house pdf) return a 200 with a non-JSON body
        ok = r.status_code == 200 and (mstatus == "success" or (not is_json and bool(r.content)))
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
hit("GET", "/fred/GDP?limit=2&sort_order=desc&observation_start=2020-01-01", "FRED")  # new params
hit("GET", "/fred?q=unemployment&limit=2", "FRED")
hit("GET", "/fred/series/UNRATE", "FRED")  # new: series metadata
# ── EDGAR ──
hit("GET", "/edgar/company/AAPL", "EDGAR")
hit("GET", "/edgar/financials/AAPL", "EDGAR", timeout=60)
hit("GET", "/edgar/concept/AAPL/Revenues", "EDGAR")
hit("GET", "/edgar/frames/Revenues?period=CY2023", "EDGAR", timeout=60)
hit("GET", "/edgar/search?q=artificial+intelligence", "EDGAR")
hit("GET", "/edgar/search?q=artificial+intelligence&from=100", "EDGAR")  # pagination pass-through
hit("GET", "/edgar/cik/AAPL", "EDGAR")  # new: ticker->CIK
hit("GET", "/edgar/submissions/CIK0000320193-submissions-001.json", "EDGAR")  # new: overflow file
# new: resolve a 10-K document from AAPL's filings, then fetch it raw (bytes, not JSON)
_co = hit("GET", "/edgar/company/320193", "EDGAR")
_recent = ((_co or {}).get("data") or {}).get("filings", {}).get("recent", {}) if isinstance(_co, dict) else {}
_accn = next((a for f, a in zip(_recent.get("form", []), _recent.get("accessionNumber", [])) if f == "10-K"), None)
if _accn:
    _doc = _recent["primaryDocument"][_recent["accessionNumber"].index(_accn)]
    hit("GET", f"/edgar/document/320193/{_accn.replace('-', '')}/{_doc}", "EDGAR")
else:
    skip("EDGAR", "GET /edgar/document/...", "no 10-K accession resolved")
# ── Nasdaq ──
hit("GET", "/nasdaq/quote/AAPL", "Nasdaq")
hit("GET", "/nasdaq/price/AAPL", "Nasdaq")
hit("GET", "/nasdaq/history/AAPL?fromdate=2026-01-01&todate=2026-02-01&limit=5", "Nasdaq")
hit("GET", "/nasdaq/dividends/AAPL", "Nasdaq")
hit("GET", "/nasdaq/financials/NVDA", "Nasdaq")            # new
hit("GET", "/nasdaq/insider-trades/NVDA", "Nasdaq")        # new
hit("GET", "/nasdaq/earnings-surprise/NVDA", "Nasdaq")     # new
hit("GET", "/nasdaq/calendar/earnings?date=2026-06-15", "Nasdaq")  # new (date required)
hit("GET", "/nasdaq/calendar/ipo?date=2026-06", "Nasdaq")          # new (IPO calendar takes YYYY-MM)
hit("GET", "/nasdaq/screener?limit=5", "Nasdaq")           # new
# ── yfinance ──
for ep in ["info", "history", "news", "recommendations", "holders", "financials", "dividends", "options", "earnings"]:
    hit("GET", f"/yfinance/{ep}/AAPL", "yfinance", timeout=60)  # 'earnings' is new
# ── USAspending ──
hit("GET", "/usaspending/agencies", "USAspending")
hit("GET", "/usaspending/search?q=defense&limit=2", "USAspending")  # default: contracts
hit("GET", "/usaspending/search?q=university&award_type_codes=02,03,04,05&limit=2", "USAspending")  # new: grants reachable
hit("GET", "/usaspending/by-agency?fy=2025", "USAspending")  # fy now required
# ── Census (known: needs a valid key) ──
hit("GET", "/census/population?year=2022", "Census")  # year now required
hit("GET", "/census/income?year=2022", "Census")
hit("GET", "/census/acs?year=2022", "Census")  # defaults to acs5 (supports tract)
# ── BLS ──
hit("GET", "/bls/CUUR0000SA0?start_year=2024&end_year=2025", "BLS")  # years now required
hit("POST", "/bls/batch", "BLS", json={"series_ids": ["cpi", "unemployment"], "start_year": 2023, "end_year": 2025})  # new
# ── Treasury ──
hit("GET", "/treasury/debt?limit=2", "Treasury")
hit("GET", "/treasury/rates?limit=2", "Treasury")
hit("GET", "/treasury/exchange?limit=2", "Treasury")
# ── FEC ──
hit("GET", "/fec/candidates?limit=2", "FEC")
hit("GET", "/fec/contributions?name=trump&limit=2", "FEC")  # schedule_a 400s without a filter
hit("GET", "/fec/totals?year=2024&limit=2", "FEC")  # year now required
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
# ── JEFS (disabled on the API 2026-06-11 — routes commented out in main.py) ──
skip("JEFS", "POST /jefs/register", "JEFS disabled on the API (2026-06-11)")
skip("JEFS", "GET /jefs/facets", "JEFS disabled on the API (2026-06-11)")
skip("JEFS", "GET /jefs/search", "JEFS disabled on the API (2026-06-11)")
skip("JEFS", "POST /jefs/reset", "JEFS disabled on the API (2026-06-11)")
# ── House Disclosures ──
hm = hit("GET", "/house-disclosures/members?last_name=pelosi", "HouseFD")
hit("GET", "/house-disclosures/candidates?last_name=smith", "HouseFD")
_pdf = find(hm, "pdf_url")  # new: fetch a real disclosure PDF (raw bytes)
if _pdf:
    from urllib.parse import quote
    hit("GET", f"/house-disclosures/pdf?path={quote(str(_pdf), safe='')}", "HouseFD")
else:
    skip("HouseFD", "GET /house-disclosures/pdf", "no pdf_url resolved from members search")
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
# ── Wilson Center (disabled on the API 2026-07-02 — routes commented out in main.py) ──
skip("Wilson", "GET /wilson/documents", "Wilson disabled on the API (2026-07-02)")
skip("Wilson", "GET /wilson/document/{slug}", "Wilson disabled on the API (2026-07-02)")
# ── arXiv ──
hit("GET", "/arxiv/search?query=electron&max_results=2", "arXiv")
hit("GET", "/arxiv/2301.00001", "arXiv")
# ── Scholar (Google blocks server IPs → expected error, not a hard fail) ──
hit("GET", "/scholar/search?keyword=transformer+neural+network&nresults=3", "Scholar", expect_error=True)
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
