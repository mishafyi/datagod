#!/usr/bin/env python3
"""Smoke-test every DataGod endpoint against a live server and verify each one
actually RETURNS INFORMATION, then print a grouped table.

    .venv/bin/python tests/test_all_endpoints.py

Target host: $DATAGOD_BASE_URL (default http://localhost:8000), key: $DATAGOD_API_KEY.

Verdicts
  PASS     HTTP 200, meta.status "success", and the content check found real data
           (the note says what came back: row counts, a title, the latest value).
  NO-DATA  HTTP 200 + success but the payload is empty or no longer has the
           expected shape — an upstream change or a client bug. Counts as a failure.
  FAIL     any other error. Counts as a failure.
  CONFIG   the target lacks a key or setting (FRED/Census/UCDP key, NEWSNOW_BASE_URL,
           the Wilson index). Not a code failure — set it and re-run.
  LIMIT    an upstream quota or rate limit (DEMO_KEY, BLS daily threshold).
  BLOCKED  the upstream refuses this network (Wikimedia's bot wall on some cloud IPs).
  EXP-ERR  an error the source is known for (Google Scholar CAPTCHAs, Wayback throttling).
  SKIP     a chained call whose id could not be resolved, or a disabled source (JEFS).
The exit status is 1 when anything is FAIL or NO-DATA.
A last "Contract" group checks error handling end to end (status codes and
meta.status for bad input, SSRF refusal, framework errors).
"""

import os
import sys
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
BASE = os.getenv("DATAGOD_BASE_URL", "http://localhost:8000").rstrip("/")
HEADERS = {"X-API-Key": os.getenv("DATAGOD_API_KEY", "")}

rows: list[tuple[str, str, object, str, str]] = []

# Error-message fragments that mean "the environment, not the code".
CONFIG_HINTS = ("variable api_key", "rejected the api key", "api token required", "not configured",
                "api_key_missing", "api_key_invalid", "local index missing")
LIMIT_HINTS = ("429 too many", "daily threshold", "over_rate_limit", "rate limit", "throttl")
BLOCKED_HINTS = ("respect our robot policy",)


def classify(status: object, message: str) -> str:
    m = message.lower()
    if status == 429 or any(h in m for h in LIMIT_HINTS):
        return "LIMIT"
    if any(h in m for h in CONFIG_HINTS):
        return "CONFIG"
    if any(h in m for h in BLOCKED_HINTS):
        return "BLOCKED"
    return "FAIL"


def n(items: object, what: str, allow_empty: bool = False) -> str:
    """'<count> <what>' for a list/dict; raises when it is empty (no information came back)."""
    if not isinstance(items, (list, dict)):
        raise ValueError(f"no {what} (got {type(items).__name__})")
    if not items and not allow_empty:
        raise ValueError(f"0 {what}")
    return f"{len(items)} {what}"


def text(value: object, what: str = "text") -> str:
    """Short preview of a non-empty string field."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"no {what}")
    return value.strip()[:48]


def chars(value: object, what: str = "text") -> str:
    """'<length> chars' for a non-empty string field."""
    return f"{len(text(value, what)) and len(value):,} chars"  # text() raises when empty


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


def data_of(body: object) -> object:
    return body.get("data") if isinstance(body, dict) else None


def run_check(check: Callable[[object], str] | None, payload: object) -> tuple[str, str]:
    """(verdict, note) for a successful response: PASS with a summary of what came
    back, or NO-DATA when the check raises/returns falsy (empty or reshaped payload)."""
    if check is None:
        return "PASS", ""
    try:
        summary = check(payload)
    except Exception as exc:  # KeyError/IndexError/ValueError … = no data where it should be
        return "NO-DATA", f"{type(exc).__name__}: {exc}"
    return ("PASS", str(summary)) if summary else ("NO-DATA", "check found no data")


def hit(method: str, path: str, group: str, check: Callable[[object], str] | None = None,
        expect_error: bool = False, timeout: int = 45, **kwargs) -> object:
    """Call one endpoint and record a verdict. `check(data)` returns a short summary of
    what came back and raises (or returns falsy) when the payload carries no data."""
    label = f"{method} {path.split('?')[0]}"
    try:
        r = httpx.request(method, BASE + path, headers=HEADERS, timeout=timeout,
                          follow_redirects=True, **kwargs)
    except Exception as exc:
        rows.append((group, label, "ERR", "EXP-ERR" if expect_error else "FAIL",
                     f"{type(exc).__name__}: {exc}"))
        return None
    ctype = r.headers.get("content-type", "")
    if "application/json" not in ctype:  # raw-bytes routes (EDGAR documents, House PDFs)
        if r.status_code == 200 and r.content:
            verdict, note = run_check(check, r.content)
        else:
            verdict, note = "FAIL", f"HTTP {r.status_code}, {len(r.content):,} bytes {ctype.split(';')[0]}"
        rows.append((group, label, r.status_code, verdict, note))
        return None
    try:
        body = r.json()
    except ValueError:
        rows.append((group, label, r.status_code, "FAIL", "invalid JSON body"))
        return None
    status = (body.get("meta") or {}).get("status") if isinstance(body, dict) else None
    if r.status_code == 200 and status == "success":
        verdict, note = run_check(check, body["data"])
    else:
        note = str(body.get("error") if isinstance(body, dict) else body)
        verdict = "EXP-ERR" if expect_error else classify(r.status_code, note)
    rows.append((group, label, r.status_code, verdict, note))
    return body


def skip(group: str, label: str, note: str) -> None:
    rows.append((group, label, "—", "SKIP", note))


def expect(method: str, path: str, group: str, status: int, note: str, **kwargs) -> None:
    """PASS when the route answers `status` with an error envelope (negative checks)."""
    label = f"{method} {path.split('?')[0]}"
    headers = {**HEADERS, **kwargs.pop("headers", {})}
    try:
        r = httpx.request(method, BASE + path, headers=headers, timeout=45, **kwargs)
        mstatus = (r.json().get("meta") or {}).get("status")
        ok = r.status_code == status and mstatus == "error"
        rows.append((group, label, r.status_code, "PASS" if ok else "FAIL",
                     note if ok else f"want {status}+error, got meta.status={mstatus}"))
    except Exception as exc:
        rows.append((group, label, "ERR", "FAIL", str(exc)))


def fred_obs(d: dict) -> str:
    obs = d["observations"]
    return f"{n(obs, 'observations')}, last {obs[-1]['date']} = {obs[-1]['value']}"


def sdmx_series(d: dict) -> str:
    """IMF/ECB SDMX-JSON 1.0: series count × observation periods."""
    series = d["dataSets"][0]["series"]
    periods = [v.get("value", v.get("id")) for v in d["structure"]["dimensions"]["observation"][0]["values"]]
    first = next(iter(series.values()))["observations"]
    return f"{n(series, 'series')} × {n(first, 'obs')}, {periods[0]}..{periods[-1]}"


def worldbank_rows(d: list) -> str:
    values = [row for row in d[1] if row.get("value") is not None]
    return f"{n(d[1], 'rows')}, {len(values)} with values"


# ── Health ──
hit("GET", "/", "Health", lambda d: f"{d['sources']} sources")
hit("GET", "/health", "Health", lambda d: d["status"] == "ok" and "ok")
# ── FRED ──
hit("GET", "/fred/GDP?limit=2", "FRED", fred_obs)
hit("GET", "/fred/GDP?limit=2&sort_order=desc&observation_start=2020-01-01", "FRED", fred_obs)
hit("GET", "/fred?q=unemployment&limit=2", "FRED", lambda d: n(d["seriess"], "series"))
hit("GET", "/fred/series/UNRATE", "FRED", lambda d: text(d["seriess"][0]["title"], "title"))
# ── EDGAR ──
hit("GET", "/edgar/company/AAPL", "EDGAR",
    lambda d: f"{text(d['name'])}, {n(d['filings']['recent']['form'], 'recent filings')}")
hit("GET", "/edgar/financials/AAPL", "EDGAR", lambda d: n(d["facts"]["us-gaap"], "us-gaap concepts"), timeout=60)
hit("GET", "/edgar/concept/AAPL/Revenues", "EDGAR", lambda d: n(next(iter(d["units"].values())), "facts"))
hit("GET", "/edgar/frames/Revenues?period=CY2023", "EDGAR", lambda d: n(d["data"], "filers"), timeout=60)
hit("GET", "/edgar/search?q=artificial+intelligence", "EDGAR",
    lambda d: f"{n(d['hits']['hits'], 'hits')} of {d['hits']['total']['value']}")
hit("GET", "/edgar/search?q=artificial+intelligence&from=100", "EDGAR", lambda d: n(d["hits"]["hits"], "hits"))
hit("GET", "/edgar/cik/AAPL", "EDGAR", lambda d: text(d["cik"], "cik"))
hit("GET", "/edgar/submissions/CIK0000320193-submissions-001.json", "EDGAR",
    lambda d: n(d["accessionNumber"], "older filings"))
# resolve a 10-K document from AAPL's filings, then fetch it raw (bytes, not JSON)
_co = data_of(hit("GET", "/edgar/company/320193", "EDGAR", lambda d: text(d["name"]))) or {}
_recent = _co.get("filings", {}).get("recent", {})
_accn = next((a for f, a in zip(_recent.get("form", []), _recent.get("accessionNumber", []), strict=False) if f == "10-K"), None)
if _accn:
    _doc = _recent["primaryDocument"][_recent["accessionNumber"].index(_accn)]
    hit("GET", f"/edgar/document/320193/{_accn.replace('-', '')}/{_doc}", "EDGAR",
        lambda raw: len(raw) > 10_000 and f"10-K, {len(raw):,} bytes")
else:
    skip("EDGAR", "GET /edgar/document/...", "no 10-K accession resolved")
# ── Nasdaq ──
hit("GET", "/nasdaq/quote/AAPL", "Nasdaq", lambda d: n(d["data"]["summaryData"], "summary fields"))
hit("GET", "/nasdaq/price/AAPL", "Nasdaq", lambda d: text(d["data"]["primaryData"]["lastSalePrice"], "price"))
# Nasdaq answers 0 rows for a window that ended weeks ago — ask for one ending today.
_today = date.today()
hit("GET", f"/nasdaq/history/AAPL?fromdate={_today - timedelta(days=30)}&todate={_today}&limit=5", "Nasdaq",
    lambda d: n(d["data"]["tradesTable"]["rows"], "daily bars"))
hit("GET", "/nasdaq/dividends/AAPL", "Nasdaq", lambda d: n(d["data"]["dividends"]["rows"], "dividends"))
hit("GET", "/nasdaq/financials/NVDA", "Nasdaq",
    lambda d: n(d["data"]["incomeStatementTable"]["rows"], "income-statement rows"))
hit("GET", "/nasdaq/financials/NVDA?frequency=quarterly", "Nasdaq",
    lambda d: text(d["data"]["incomeStatementTable"]["headers"]["value1"], "period header"))
hit("GET", "/nasdaq/insider-trades/NVDA", "Nasdaq", lambda d: n(d["data"]["transactionTable"]["table"]["rows"], "trades"))
hit("GET", "/nasdaq/earnings-surprise/NVDA", "Nasdaq", lambda d: n(d["data"]["earningsSurpriseTable"]["rows"], "quarters"))
hit("GET", "/nasdaq/calendar/earnings?date=2026-06-15", "Nasdaq", lambda d: n(d["data"]["rows"], "companies"))
hit("GET", "/nasdaq/calendar/ipo?date=2026-06", "Nasdaq", lambda d: n(d["data"]["priced"]["rows"], "priced IPOs"))
hit("GET", "/nasdaq/screener?limit=5", "Nasdaq", lambda d: n(d["data"]["table"]["rows"], "stocks"))
# ── yfinance ──
hit("GET", "/yfinance/info/AAPL", "yfinance", lambda d: text(d.get("longName") or d.get("shortName"), "name"), timeout=60)
hit("GET", "/yfinance/history/AAPL", "yfinance", lambda d: n(d, "daily bars"), timeout=60)
hit("GET", "/yfinance/news/AAPL", "yfinance", lambda d: n(d, "articles"), timeout=60)
hit("GET", "/yfinance/recommendations/AAPL", "yfinance", lambda d: n(d, "periods"), timeout=60)
hit("GET", "/yfinance/holders/AAPL", "yfinance", lambda d: n(d["institutional"], "institutional holders"), timeout=60)
hit("GET", "/yfinance/financials/AAPL", "yfinance", lambda d: n(d["income_stmt"], "income-statement lines"), timeout=60)
hit("GET", "/yfinance/dividends/AAPL", "yfinance", lambda d: n(d, "dividends"), timeout=60)
hit("GET", "/yfinance/earnings/AAPL", "yfinance", lambda d: n(d["earnings_dates"], "earnings dates"), timeout=60)
_expiries = (data_of(hit("GET", "/yfinance/options/AAPL", "yfinance",
                         lambda d: n(d["expirations"], "expiries"), timeout=60)) or {}).get("expirations") or []
if _expiries:
    hit("GET", f"/yfinance/options/AAPL?expiry={_expiries[0]}", "yfinance",
        lambda d: f"{n(d['calls'], 'calls')}, {n(d['puts'], 'puts')}", timeout=60)
else:
    skip("yfinance", "GET /yfinance/options/{ticker}?expiry=", "no expiry resolved")
# ── USAspending ──
hit("GET", "/usaspending/agencies", "USAspending", lambda d: n(d["results"], "agencies"))
hit("GET", "/usaspending/search?q=defense&limit=2", "USAspending", lambda d: n(d["results"], "contracts"))
hit("GET", "/usaspending/search?q=university&award_type_codes=02,03,04,05&limit=2", "USAspending",
    lambda d: n(d["results"], "grants"))
hit("GET", "/usaspending/by-agency?fy=2025", "USAspending", lambda d: n(d["results"], "agencies"))
# ── Census (needs a valid CENSUS_API_KEY) ──
hit("GET", "/census/population?year=2022", "Census", lambda d: n(d[1:], "states"))
hit("GET", "/census/income?year=2022", "Census", lambda d: n(d[1:], "states"))
hit("GET", "/census/acs?year=2022", "Census", lambda d: n(d[1:], "rows"))
# ── BLS ──
hit("GET", "/bls/CUUR0000SA0?start_year=2024&end_year=2025", "BLS",
    lambda d: n(d["Results"]["series"][0]["data"], "months"))
hit("POST", "/bls/batch", "BLS", lambda d: n(d["Results"]["series"], "series"),
    json={"series_ids": ["cpi", "unemployment"], "start_year": 2023, "end_year": 2025})
# ── Treasury ──
hit("GET", "/treasury/debt?limit=2", "Treasury",
    lambda d: f"{n(d['data'], 'days')}, latest {d['data'][0]['record_date']}")
hit("GET", "/treasury/rates?limit=2", "Treasury", lambda d: n(d["data"], "rates"))
hit("GET", "/treasury/exchange?limit=2", "Treasury", lambda d: n(d["data"], "rates"))
# ── FEC ──
hit("GET", "/fec/candidates?limit=2", "FEC", lambda d: n(d["results"], "candidates"))
hit("GET", "/fec/candidates?name=pelosi&limit=5", "FEC", lambda d: text(d["results"][0]["name"], "candidate"))
hit("GET", "/fec/contributions?name=trump&limit=2", "FEC", lambda d: n(d["results"], "contributions"))
hit("GET", "/fec/totals?year=2024&limit=2", "FEC", lambda d: n(d["results"], "candidates"))
# ── Congress ──
hit("GET", "/congress/bills?limit=2", "Congress", lambda d: n(d["bills"], "bills"))
hit("GET", "/congress/bill/118/hr/1", "Congress", lambda d: text(d["bill"]["title"], "title"))
hit("GET", "/congress/members?limit=2", "Congress", lambda d: n(d["members"], "members"))
hit("GET", "/congress/votes?limit=2", "Congress",
    lambda d: f"{n(d['houseRollCallVotes'], 'votes')}, congress {d['houseRollCallVotes'][0]['congress']}")
# ── FDA ──
hit("GET", "/fda/drug-events?limit=2", "FDA", lambda d: n(d["results"], "reports"))
hit("GET", "/fda/drug-recalls?limit=2", "FDA", lambda d: n(d["results"], "recalls"))
hit("GET", "/fda/food-recalls?limit=2", "FDA", lambda d: n(d["results"], "recalls"))
# ── Clinical Trials ──
hit("GET", "/clinical-trials?condition=cancer&limit=2", "ClinicalTrials", lambda d: n(d["studies"], "studies"))
hit("GET", "/clinical-trials/NCT04267848", "ClinicalTrials",
    lambda d: text(d["protocolSection"]["identificationModule"]["briefTitle"], "title"))
# ── EIA ──
hit("GET", "/eia", "EIA", lambda d: n(d["response"]["routes"], "datasets"))
hit("GET", "/eia/gas-prices?limit=2", "EIA", lambda d: n(d["response"]["data"], "prices"))
hit("GET", "/eia/electricity?limit=2", "EIA", lambda d: n(d["response"]["data"], "rows"))
hit("GET", "/eia/petroleum/pri/gnd?limit=2", "EIA", lambda d: n(d["response"]["data"], "rows"))
# ── FEMA ──
hit("GET", "/fema/disasters?limit=2", "FEMA", lambda d: n(d["DisasterDeclarationsSummaries"], "declarations"))
hit("GET", "/fema/grants?limit=2", "FEMA", lambda d: n(d["HazardMitigationGrantProgramDisasterSummaries"], "grants"))
hit("GET", "/fema/flood-claims?limit=2", "FEMA", lambda d: n(d["NfipClaims"], "claims"))
# ── Federal Register (resolve a doc number) ──
docnum = find(hit("GET", "/federal-register?limit=2", "FederalRegister", lambda d: n(d["results"], "documents")),
              "document_number")
hit("GET", f"/federal-register/{docnum}", "FederalRegister", lambda d: text(d["title"], "title")) if docnum else skip(
    "FederalRegister", "GET /federal-register/{doc_number}", "no doc number from list")
# ── JEFS (disabled on the API 2026-06-11 — routes commented out in main.py) ──
for _route in ("POST /jefs/register", "GET /jefs/facets", "GET /jefs/search", "POST /jefs/reset"):
    skip("JEFS", _route, "JEFS disabled on the API (2026-06-11)")
# ── House Disclosures ──
hm = hit("GET", "/house-disclosures/members?last_name=pelosi", "HouseFD",
         lambda d: f"{n(d, 'filings')}, first {d[0]['name']}")
hit("GET", "/house-disclosures/candidates?last_name=smith", "HouseFD", lambda d: n(d, "filings"))
_pdf = find(hm, "pdf_url")
if _pdf:
    hit("GET", f"/house-disclosures/pdf?path={quote(str(_pdf), safe='')}", "HouseFD",
        lambda raw: raw.startswith(b"%PDF") and f"PDF, {len(raw):,} bytes")
else:
    skip("HouseFD", "GET /house-disclosures/pdf", "no pdf_url resolved from members search")
# ── NARA (resolve a naId) ──
na = hit("GET", "/nara/search?q=war&page=1", "NARA",
         lambda d: f"{n(d['body']['hits']['hits'], 'records')} of {d['body']['hits']['total']['value']}")
naid = find(na, "naId")
hit("GET", f"/nara/record/{naid}", "NARA",
    lambda d: text(d["body"]["hits"]["hits"][0]["_source"]["record"]["title"], "title")) if naid else skip(
    "NARA", "GET /nara/record/{na_id}", "no naId from search")
# ── NSArchive (scrape; resolve a doc id) ──
nsr = hit("GET", "/nsarchive/search?q=cuba", "NSArchive", lambda d: f"{n(d['results'], 'documents')} of {d['total']}")
nsdoc = find(nsr, "path")  # the document id is the full "{id}-{slug}" path, not bare "id"
hit("GET", f"/nsarchive/document/{nsdoc}", "NSArchive", lambda d: text(d["title"], "title")) if nsdoc else skip(
    "NSArchive", "GET /nsarchive/document/{doc_id}", "no doc id from search")
# ── Smithsonian (resolve an EDAN id) ──
sm = hit("GET", "/smithsonian/search?q=apollo&rows=2", "Smithsonian", lambda d: n(d["response"]["rows"], "records"))
sid = find(data_of(sm), "id")
hit("GET", f"/smithsonian/object/{sid}", "Smithsonian", lambda d: text(d["response"]["title"], "title")) if sid else skip(
    "Smithsonian", "GET /smithsonian/object/{id}", "no id from search")
hit("GET", "/smithsonian/category/art_design/search?q=painting&rows=2", "Smithsonian",
    lambda d: n(d["response"]["rows"], "records"))
hit("GET", "/smithsonian/terms/culture", "Smithsonian", lambda d: n(d["response"]["terms"], "terms"))
hit("GET", "/smithsonian/stats", "Smithsonian", lambda d: f"{d['response']['total_objects']:,} objects")
# ── Wilson Center (local mirror — CONFIG unless data/wilson.db is mounted) ──
wd = hit("GET", "/wilson/documents?q=cuba&items_per_page=2", "Wilson", lambda d: n(d["list"], "documents"))
wslug = find(data_of(wd), "slug")
hit("GET", f"/wilson/document/{wslug}", "Wilson", lambda d: text(d["title"], "title")) if wslug else skip(
    "Wilson", "GET /wilson/document/{slug}", "no slug (local index not mounted?)")
# ── Declassified / intel archives (CIA + Vault read the Wayback mirror, which throttles) ──
hit("GET", "/cia/collections", "Archives", lambda d: n(d["collections"], "collections"))
hit("GET", "/cia/collection/stargate", "Archives", lambda d: n(d["documents"], "documents"),
    expect_error=True, timeout=120)
hit("GET", "/cia/document/cia-rdp96-00788r001700210016-5", "Archives", lambda d: text(d["title"], "title"),
    expect_error=True, timeout=120)
hit("GET", "/vault/subjects", "Archives", lambda d: n(d["subjects"], "subjects"))
hit("GET", "/vault/page/cointel-pro", "Archives",
    lambda d: f"{text(d['title'], 'title')}: {n(d['folders'] + d['files'], 'entries')}",
    expect_error=True, timeout=120)
fr_s = hit("GET", "/frus/search?q=covert+action+Chile", "Archives", lambda d: f"{n(d['results'], 'documents')} of {d['total']}")
fr_hit = next((x for x in (data_of(fr_s) or {}).get("results", []) if x.get("volume") and x.get("doc")), None)
hit("GET", f"/frus/document/{fr_hit['volume']}/{fr_hit['doc']}", "Archives",
    lambda d: chars(d["body"], "body")) if fr_hit else skip(
    "Archives", "GET /frus/document/{volume}/{doc}", "no volume/doc from search")
tna_s = hit("GET", "/tna/search?q=KGB+defector&per_page=2", "Archives", lambda d: f"{n(d['records'], 'records')} of {d['count']}")
tna_id = find(data_of(tna_s), "id")
hit("GET", f"/tna/record/{tna_id}", "Archives", lambda d: text(d["citableReference"], "reference")) if tna_id else skip(
    "Archives", "GET /tna/record/{record_id}", "no id from search")
hit("GET", "/fas/sections", "Archives", lambda d: n(d["sections"], "sections"))
fas_i = hit("GET", "/fas/index/nsa", "Archives", lambda d: n(d["links"], "links"))
fas_link = next((link["path"] for link in (data_of(fas_i) or {}).get("links", [])
                 if link["path"].lower().endswith((".html", ".htm")) and not link.get("is_index")), None)
hit("GET", f"/fas/page/{fas_link}", "Archives", lambda d: chars(d["text"])) if fas_link else skip(
    "Archives", "GET /fas/page/{path}", "no content link from index")
# ── arXiv ──
hit("GET", "/arxiv/search?query=electron&max_results=2", "arXiv",
    lambda d: f"{n(d['entries'], 'papers')} of {d['total_results']:,}")
hit("GET", "/arxiv/2301.00001", "arXiv", lambda d: text(d["entries"][0]["title"], "title"))
# ── Scholar (Google blocks server IPs → expected error, not a hard fail) ──
hit("GET", "/scholar/search?keyword=transformer+neural+network&nresults=3", "Scholar",
    lambda d: n(d["results"], "papers"), expect_error=True)
# ── Trending (NewsNow — self-hosted; needs NEWSNOW_BASE_URL reachable from the API) ──
hit("GET", "/trending", "Trending", lambda d: n(d["sources"], "boards"))
hit("GET", "/trending/hackernews", "Trending", lambda d: n(d["items"], "items"))
# ── World Bank ──
hit("GET", "/worldbank/countries?per_page=5", "WorldBank", lambda d: n(d[1], "countries"))
hit("GET", "/worldbank/NY.GDP.MKTP.CD?countries=us;cn&date_range=2020:2023", "WorldBank", worldbank_rows)
# ── IMF (the IMF's own SDMX API — DBnomics stopped updating in 2025-09) ──
hit("GET", "/imf/structure/WEO", "IMF", lambda d: n(d["data"]["codelists"], "codelists"), timeout=90)
hit("GET", "/imf/WEO/USA.NGDP_RPCH?start_period=2024&end_period=2027", "IMF", sdmx_series, timeout=60)
hit("GET", "/imf/CPI/USA.CPI._T.IX.M?start_period=2026-01", "IMF", sdmx_series, timeout=60)
# ── Eurostat ──
hit("GET", "/eurostat/tps00001?geo=DE&time=2024", "Eurostat", lambda d: f"{n(d['value'], 'values')}: {d['label'][:30]}")
# ── ECB ──
hit("GET", "/ecb/EXR/D.USD.EUR.SP00.A?start_period=2026-07-01&end_period=2026-07-10", "ECB", sdmx_series)
# ── Comtrade (keyless public preview — ≤500 records, rate-limited) ──
hit("GET", "/comtrade?reporterCode=842&period=2023&partnerCode=0&cmdCode=TOTAL&flowCode=M", "Comtrade",
    lambda d: n(d["data"], "flows"))
# ── UCDP (needs a free UCDP_ACCESS_TOKEN since 2026) ──
hit("GET", "/ucdp/gedevents?country=369&start_date=2025-01-01&end_date=2025-12-31&pagesize=2", "UCDP",
    lambda d: f"{n(d['Result'], 'events')} of {d['TotalCount']:,}")
# ── USGS ──
hit("GET", "/usgs/earthquakes?minmagnitude=5&limit=2", "USGS", lambda d: n(d["features"], "earthquakes"))
# ── NWS (an area may legitimately have no active alerts) ──
hit("GET", "/nws/alerts?area=CA", "NWS", lambda d: n(d["features"], "active alerts", allow_empty=True))
# ── EONET ──
hit("GET", "/eonet/events?category=wildfires&status=open&limit=2", "EONET", lambda d: n(d["events"], "events"))
hit("GET", "/eonet/categories", "EONET", lambda d: n(d["categories"], "categories"))
# ── Wikipedia ──
hit("GET", "/wikipedia/summary/Albert_Einstein", "Wikipedia", lambda d: text(d["extract"], "extract"))
hit("GET", "/wikipedia/summary/AC%2FDC", "Wikipedia", lambda d: text(d["title"], "title"))  # "/" in a title
hit("GET", "/wikipedia/article/Albert_Einstein", "Wikipedia",
    lambda d: chars(d["query"]["pages"][0]["extract"], "extract"))
hit("GET", "/wikipedia/search?q=quantum+computing&limit=3", "Wikipedia", lambda d: n(d["query"]["search"], "hits"))
hit("GET", "/wikipedia/pageviews/Albert_Einstein?start=20260701&end=20260707", "Wikipedia",
    lambda d: f"{n(d['items'], 'days')}, {sum(i['views'] for i in d['items']):,} views")
# ── NASA Image and Video Library (resolve a nasa_id) ──
nasr = hit("GET", "/nasa/search?q=apollo+11&media_type=video&page_size=2", "NASAImages",
           lambda d: n(d["collection"]["items"], "videos"))
nasa_id = find(nasr, "nasa_id")
hit("GET", f"/nasa/asset/{nasa_id}", "NASAImages", lambda d: n(d["collection"]["items"], "files")) if nasa_id else skip(
    "NASAImages", "GET /nasa/asset/{nasa_id}", "no nasa_id from search")
# ── Internet Archive (resolve an identifier) ──
iar = hit("GET", "/archive/search?q=moon+landing&rows=2", "InternetArchive",
          lambda d: f"{n(d['response']['docs'], 'items')} of {d['response']['numFound']:,}")
ia_id = find(iar, "identifier")
hit("GET", f"/archive/item/{ia_id}", "InternetArchive", lambda d: n(d["files"], "files")) if ia_id else skip(
    "InternetArchive", "GET /archive/item/{identifier}", "no identifier from search")
# ── Wikimedia Commons ──
hit("GET", "/commons/search?q=moon+landing&limit=2", "Commons", lambda d: n(d["query"]["pages"], "video files"))
# ── Cross-Reference (fans out to several upstreams) ──
hit("GET", "/cross-reference/company/apple", "CrossRef",
    lambda d: f"{text(d['company']['name'])}, revenue {d['financials']['latest']['val']:,} "
              f"(FY to {d['financials']['latest']['end']})", timeout=90)
hit("GET", "/cross-reference/politician/pelosi", "CrossRef",
    lambda d: f"{n(d['house_trades'], 'House filings')}, {len(d['campaign_finance'])} FEC matches"
              + (f" (errors: {', '.join(d['errors'])})" if d.get("errors") else ""), timeout=90)
# ── Admin ──
hit("POST", "/admin/clear-cache", "Admin", lambda d: text(d["status"]))
# ── Contract: error handling end to end ──
expect("GET", "/house-disclosures/pdf?path=http://169.254.169.254/latest/meta-data/", "Contract", 400,
       "SSRF refused")
expect("GET", "/fred/GDP?limit=abc", "Contract", 422, "validation error is an error envelope")
expect("GET", "/no/such/route", "Contract", 404, "unknown route is an error envelope")
expect("GET", "/nasdaq/quote/NOTATICKERX", "Contract", 400, "Nasdaq in-body rCode surfaced")
expect("GET", "/nasdaq/financials/NVDA?frequency=weekly", "Contract", 400, "bad frequency refused")
expect("GET", "/fred", "Contract", 401, "missing key", headers={"X-API-Key": ""})

# ── Report ──
icons = {"PASS": "✓", "NO-DATA": "∅", "FAIL": "✗", "CONFIG": "⚙", "LIMIT": "⏳", "BLOCKED": "⊘",
         "EXP-ERR": "~", "SKIP": "-"}
print(f"\nTarget: {BASE}\n" + "=" * 100)
current = None
for group, label, code, verdict, note in rows:
    if group != current:
        current = group
        print(f"\n## {group}")
    print(f"  {icons[verdict]} {str(code):>4}  {label:48} {' '.join(str(note).split())[:78]}")
counts = {k: sum(1 for r in rows if r[3] == k) for k in icons}
print("\n" + "=" * 100)
print("   ".join(f"{k} {v}" for k, v in counts.items()) + f"   / {len(rows)} checks")
failed = counts["FAIL"] + counts["NO-DATA"]
print("RESULT:", "every reachable endpoint returned data" if not failed else f"{failed} endpoint(s) failed")
sys.exit(1 if failed else 0)
