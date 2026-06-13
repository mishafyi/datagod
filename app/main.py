"""
DataGod — Unified API for 15 US Government data sources + Nasdaq.com.

One API, all the data. Free.
"""

from fastapi import Depends, FastAPI, Query, Request
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse

from .auth import UnauthorizedError, require_api_key, require_docs_auth
from .cache import clear_cache
from .clients import (
    bls,
    census,
    clinicaltrials,
    congress_gov as congress,
    cross_reference,
    edgar,
    eia,
    fec,
    federal_register,
    fema,
    fda,
    fred,
    house_fd,
    # jefs,  # disabled 2026-06-11 — see the JEFS route block below
    nara,
    nasdaq,
    nsarchive,
    smithsonian,
    treasury,
    usaspending,
    wilson,
    yfin,
)
from .middleware import ResponseEnvelopeMiddleware

API_DESCRIPTION = """\
**DataGod** unifies 21 free US-government and markets data sources (plus a
cross-reference aggregator) behind one HTTP API. Routes are thin pass-throughs —
each returns the upstream's JSON unchanged, wrapped in a standard envelope.

## Authentication
Every data endpoint requires your API key in the **`X-API-Key`** header:

```bash
curl -H "X-API-Key: <your-key>" https://datagod.example.com/fred/GDP
```

A missing or wrong key returns **401**. `GET /health` is the only public route.
These interactive docs are protected separately by HTTP Basic auth.

## Response envelope
Every response is wrapped:

```json
{
  "meta": { "source": "fred", "endpoint": "/fred/GDP", "timestamp": "...Z", "status": "success" },
  "data": { "...": "upstream payload, unchanged" },
  "error": null
}
```

On failure `meta.status` is `"error"`, `error` carries the message, and the HTTP
status mirrors the upstream: 4xx pass through, while 5xx / timeouts / connect
errors become **502**.

## Tip
Click **Authorize** (top right), paste your key once, and every "Try it out" call
sends the `X-API-Key` header for you.
"""

API_TAGS = [
    {"name": "Health", "description": "Liveness probe. `GET /health` is public (no key required)."},
    {"name": "FRED", "description": "Federal Reserve Economic Data — 800K+ economic time series."},
    {"name": "EDGAR", "description": "SEC EDGAR — corporate filings, XBRL financials, full-text search. The Frames endpoint compares one concept across all filers in a single call."},
    {"name": "Nasdaq", "description": "Nasdaq.com (unofficial) — quote, price, history, dividends."},
    {"name": "yfinance", "description": "Yahoo Finance via the yfinance library — fundamentals, news, options, holders."},
    {"name": "USAspending", "description": "USAspending.gov — federal contracts and grants ($6T+/yr)."},
    {"name": "Census", "description": "US Census Bureau — population, income, and raw ACS queries."},
    {"name": "BLS", "description": "Bureau of Labor Statistics — employment, wages, CPI."},
    {"name": "Treasury", "description": "Treasury Fiscal Data — debt, interest rates, exchange rates."},
    {"name": "FEC", "description": "Federal Election Commission — candidates, contributions, totals."},
    {"name": "Congress", "description": "Congress.gov — bills, members, votes."},
    {"name": "FDA", "description": "openFDA — drug adverse events, drug recalls, food recalls."},
    {"name": "Clinical Trials", "description": "ClinicalTrials.gov — 500K+ registered trials."},
    {"name": "EIA", "description": "Energy Information Administration — gas prices, electricity, and generic dataset queries."},
    {"name": "FEMA", "description": "OpenFEMA — disaster declarations, grants, flood claims."},
    {"name": "Federal Register", "description": "Federal Register — rules, notices, executive orders."},
    # {"name": "JEFS", "description": "Judicial Financial Disclosures — session-based; needs Playwright registration + reCAPTCHA first."},  # disabled 2026-06-11

    {"name": "House Disclosures", "description": "US House financial disclosures (member/candidate stock trades)."},
    {"name": "NARA", "description": "US National Archives Catalog — all record groups plus the 14 presidential libraries."},
    {"name": "NSArchive", "description": "National Security Archive (GWU NGO, not NARA) — Virtual Reading Room declassified docs (HTML scrape)."},
    {"name": "Smithsonian", "description": "Smithsonian Open Access (EDAN) — 11M+ museum/library/archive records."},
    {"name": "Wilson Center", "description": "Wilson Center Digital Archive — local mirror of 16,756 declassified documents."},
    {"name": "Cross-Reference", "description": "Aggregators that join several sources for one company or politician."},
    {"name": "Admin", "description": "Operational endpoints (cache management)."},
]

app = FastAPI(
    title="DataGod",
    description=API_DESCRIPTION,
    version="1.0.0",
    openapi_tags=API_TAGS,
    contact={"name": "DataGod (source)", "url": "https://github.com/mishafyi/datagod"},
    dependencies=[Depends(require_api_key)],
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(ResponseEnvelopeMiddleware)


# ── Interactive docs — re-served behind HTTP Basic (see app/auth.py) ──────
# The built-in docs are disabled above (docs_url/redoc_url/openapi_url=None) and
# re-served here behind require_docs_auth so the API surface isn't public. The
# X-API-Key check skips these paths (auth.DOCS_PATHS); Basic auth guards them.

@app.get("/openapi.json", include_in_schema=False, dependencies=[Depends(require_docs_auth)])
async def protected_openapi() -> JSONResponse:
    return JSONResponse(app.openapi())


@app.get("/docs", include_in_schema=False, dependencies=[Depends(require_docs_auth)])
async def protected_swagger() -> HTMLResponse:
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="DataGod API — Swagger UI",
        oauth2_redirect_url=None,
    )


@app.get("/redoc", include_in_schema=False, dependencies=[Depends(require_docs_auth)])
async def protected_redoc() -> HTMLResponse:
    return get_redoc_html(openapi_url="/openapi.json", title="DataGod API — ReDoc")


@app.exception_handler(UnauthorizedError)
async def unauthorized_handler(request: Request, exc: UnauthorizedError) -> JSONResponse:
    """Render auth failures in DataGod's standard error-envelope shape (HTTP 401)."""
    return JSONResponse(
        status_code=401,
        content={"error": True, "source": "auth", "upstream_status": 401, "message": str(exc)},
    )


# ── Health ───────────────────────────────────────────────────────

@app.get("/", tags=["Health"], summary="API index: sources and endpoint map")
async def root():
    return {
        "name": "DataGod",
        "version": "1.0.0",
        "sources": 21,
        "endpoints": {
            "economy": ["/fred", "/bls", "/treasury"],
            "markets": ["/edgar", "/nasdaq", "/yfinance"],
            "spending": ["/usaspending"],
            "politics": ["/fec", "/congress", "/house-disclosures"],
            "demographics": ["/census"],
            "health": ["/fda", "/clinical-trials"],
            "energy": ["/eia"],
            "disasters": ["/fema"],
            "regulations": ["/federal-register"],
            "history": ["/wilson"],
            "museums": ["/smithsonian"],
            "archives": ["/nara", "/nsarchive"],
            "cross_reference": ["/cross-reference/company", "/cross-reference/politician"],
        },
    }


@app.get("/health", tags=["Health"], summary="Liveness probe (public, no API key)")
async def health():
    """Public liveness probe (no API key required)."""
    return {"status": "ok"}


# ── FRED ─────────────────────────────────────────────────────────

@app.get("/fred/{series_id}", tags=["FRED"], summary="Fetch a FRED economic time series")
async def fred_series(series_id: str, limit: int = Query(10, le=1000)):
    return await fred.get_series(series_id, limit)


@app.get("/fred", tags=["FRED"], summary="Search FRED series by keyword")
async def fred_search(q: str = Query("", description="Search series by keyword"),
                      limit: int = Query(10, le=100)):
    if q:
        return await fred.search(q, limit)
    return {"hint": "Use /fred/{series_id} or /fred?q=keyword",
            "common_series": {"GDP": "Gross Domestic Product", "UNRATE": "Unemployment Rate",
                               "CPIAUCSL": "CPI", "FEDFUNDS": "Fed Funds Rate",
                               "DGS10": "10Y Treasury", "SP500": "S&P 500"}}


# ── EDGAR ────────────────────────────────────────────────────────

@app.get("/edgar/company/{cik}", tags=["EDGAR"], summary="Company profile and filing history (CIK or ticker)")
async def edgar_company(cik: str):
    """Company metadata + filing history. Accepts CIK number or ticker (e.g., AAPL)."""
    return await edgar.company(cik)


@app.get("/edgar/financials/{cik}", tags=["EDGAR"], summary="All XBRL financial facts for a company")
async def edgar_financials(cik: str):
    """All XBRL financial facts for a company."""
    return await edgar.financials(cik)


@app.get("/edgar/concept/{cik}/{concept}", tags=["EDGAR"], summary="One XBRL concept's history for a company")
async def edgar_concept(cik: str, concept: str, taxonomy: str = "us-gaap"):
    """One concept's history (e.g., Revenues, Assets, NetIncomeLoss)."""
    return await edgar.concept(cik, concept, taxonomy)


@app.get("/edgar/frames/{concept}", tags=["EDGAR"], summary="One concept across all filers (cross-company)")
async def edgar_frames(concept: str, unit: str = "USD", period: str = "CY2023",
                        taxonomy: str = "us-gaap"):
    """Cross-company comparison. One concept for ALL companies."""
    return await edgar.frames(concept, unit, period, taxonomy)


@app.get("/edgar/search", tags=["EDGAR"], summary="Full-text search inside filing documents")
async def edgar_search(q: str, forms: str = "", limit: int = Query(10, le=100),
                       startdt: str = "", enddt: str = ""):
    """Full-text search inside filing documents. Optional `startdt`/`enddt`
    (YYYY-MM-DD) scope to a filing-date range, e.g. ?q=Ukraine&startdt=2026-01-01&enddt=2026-12-31."""
    return await edgar.search_filings(q, forms, limit, startdt, enddt)


# ── Nasdaq ───────────────────────────────────────────────────────

@app.get("/nasdaq/quote/{ticker}", tags=["Nasdaq"], summary="Quote summary: market cap, sector, P/E, 52-week")
async def nasdaq_quote(ticker: str, asset_class: str = "stocks"):
    """Market cap, sector, industry, P/E, dividend, 52-week range."""
    return await nasdaq.summary(ticker, asset_class)


@app.get("/nasdaq/price/{ticker}", tags=["Nasdaq"], summary="Real-time price, bid/ask, volume, change")
async def nasdaq_price(ticker: str, asset_class: str = "stocks"):
    """Real-time price, bid/ask, volume, percent change."""
    return await nasdaq.info(ticker, asset_class)


@app.get("/nasdaq/history/{ticker}", tags=["Nasdaq"], summary="Daily OHLCV between two dates")
async def nasdaq_history(ticker: str, fromdate: str, todate: str,
                          limit: int = Query(30, le=260),
                          asset_class: str = "stocks"):
    """Daily OHLCV between two dates (YYYY-MM-DD). Newest row first."""
    return await nasdaq.historical(ticker, fromdate, todate, limit, asset_class)


@app.get("/nasdaq/dividends/{ticker}", tags=["Nasdaq"], summary="Dividend history")
async def nasdaq_dividends(ticker: str, asset_class: str = "stocks"):
    """Dividend history."""
    return await nasdaq.dividends(ticker, asset_class)


# ── yfinance (Yahoo Finance) ─────────────────────────────────────

@app.get("/yfinance/info/{ticker}", tags=["yfinance"], summary="Full ticker fundamentals (~140 fields)")
async def yf_info(ticker: str):
    """Full ticker info: ~140 fields incl. market cap, P/E, EPS, beta, margins, ROE, analyst targets."""
    return await yfin.info(ticker)


@app.get("/yfinance/history/{ticker}", tags=["yfinance"], summary="OHLCV price history")
async def yf_history(ticker: str, period: str = "1mo", interval: str = "1d"):
    """OHLCV history. period: 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max. interval: 1m,5m,1h,1d,1wk,1mo."""
    return await yfin.history(ticker, period, interval)


@app.get("/yfinance/news/{ticker}", tags=["yfinance"], summary="Recent news headlines")
async def yf_news(ticker: str):
    """Recent news headlines linked to the ticker."""
    return await yfin.news(ticker)


@app.get("/yfinance/recommendations/{ticker}", tags=["yfinance"], summary="Analyst recommendation history")
async def yf_recommendations(ticker: str):
    """Analyst recommendation history."""
    return await yfin.recommendations(ticker)


@app.get("/yfinance/holders/{ticker}", tags=["yfinance"], summary="Major, institutional, and fund holders")
async def yf_holders(ticker: str):
    """Major, institutional, and mutual-fund holders."""
    return await yfin.holders(ticker)


@app.get("/yfinance/financials/{ticker}", tags=["yfinance"], summary="Income statement, balance sheet, cash flow")
async def yf_financials(ticker: str):
    """Annual + quarterly income statement, balance sheet, cash flow."""
    return await yfin.financials(ticker)


@app.get("/yfinance/dividends/{ticker}", tags=["yfinance"], summary="Dividend payment history")
async def yf_dividends(ticker: str):
    """Dividend payment history."""
    return await yfin.dividends(ticker)


@app.get("/yfinance/options/{ticker}", tags=["yfinance"], summary="Options chain (expiries or calls/puts)")
async def yf_options(ticker: str, expiry: str = ""):
    """Options chain. expiry blank → list expiries; else calls+puts for that date."""
    return await yfin.options(ticker, expiry)


# ── USAspending ──────────────────────────────────────────────────

@app.get("/usaspending/agencies", tags=["USAspending"], summary="List federal agencies")
async def usaspending_agencies():
    return await usaspending.agencies()


@app.get("/usaspending/search", tags=["USAspending"], summary="Search federal awards by keyword")
async def usaspending_search(q: str, start_date: str = "", end_date: str = "",
                              limit: int = Query(10, le=100)):
    """Search federal awards by keyword."""
    return await usaspending.search_awards([q], start_date, end_date, limit)


@app.get("/usaspending/by-agency", tags=["USAspending"], summary="Spending totals by agency (fiscal year)")
async def usaspending_by_agency(fy: str = "2025", quarter: str = "1"):
    return await usaspending.spending_by_agency(fy, quarter)


# ── Census ───────────────────────────────────────────────────────

@app.get("/census/population", tags=["Census"], summary="Population by state")
async def census_population(year: int = 2022):
    return await census.population_by_state(year)


@app.get("/census/income", tags=["Census"], summary="Median household income by state")
async def census_income(year: int = 2022):
    return await census.income_by_state(year)


@app.get("/census/acs", tags=["Census"], summary="Raw ACS query (any variables and geography)")
async def census_acs(variables: str = "NAME,B01001_001E", year: int = 2022,
                      geo_for: str = "state:*", geo_in: str = ""):
    """Raw ACS query. variables: comma-separated ACS variable codes."""
    return await census.acs(variables, year, geo_for, geo_in)


# ── BLS ──────────────────────────────────────────────────────────

@app.get("/bls/{series_id}", tags=["BLS"], summary="BLS series (CPI, unemployment, wages, PPI)")
async def bls_series(series_id: str, start_year: int = 2024, end_year: int = 2026):
    """Get BLS series. Shortcuts: unemployment, cpi, nonfarm_employment, ppi, hourly_earnings."""
    return await bls.series(series_id, start_year, end_year)


# ── Treasury ─────────────────────────────────────────────────────

@app.get("/treasury/debt", tags=["Treasury"], summary="US public debt (debt to the penny)")
async def treasury_debt(limit: int = Query(5, le=100)):
    return await treasury.debt(limit)


@app.get("/treasury/rates", tags=["Treasury"], summary="Average interest rates on US debt")
async def treasury_rates(limit: int = Query(5, le=100)):
    return await treasury.interest_rates(limit)


@app.get("/treasury/exchange", tags=["Treasury"], summary="Treasury exchange rates")
async def treasury_exchange(limit: int = Query(5, le=100)):
    return await treasury.exchange_rates(limit)


# ── FEC ──────────────────────────────────────────────────────────

@app.get("/fec/candidates", tags=["FEC"], summary="Search federal candidates")
async def fec_candidates(office: str = "", state: str = "", limit: int = Query(10, le=100)):
    """Search candidates. office: P, S, H."""
    return await fec.candidates(office, state, limit)


@app.get("/fec/contributions", tags=["FEC"], summary="Campaign contributions")
async def fec_contributions(name: str = "", candidate_id: str = "",
                             limit: int = Query(10, le=100)):
    return await fec.contributions(name, candidate_id, limit)


@app.get("/fec/totals", tags=["FEC"], summary="Candidate financial totals by receipts")
async def fec_totals(office: str = "P", year: int = 2024, limit: int = Query(10, le=100)):
    """Candidate financial totals by receipts."""
    return await fec.candidate_totals(office, year, limit)


# ── Congress ─────────────────────────────────────────────────────

@app.get("/congress/bills", tags=["Congress"], summary="Recent bills")
async def congress_bills(limit: int = Query(10, le=250), congress_num: int = 0):
    return await congress.bills(limit, congress_num)


@app.get("/congress/bill/{congress_num}/{bill_type}/{number}", tags=["Congress"], summary="Single bill detail")
async def congress_bill(congress_num: int, bill_type: str, number: int):
    return await congress.bill_detail(congress_num, bill_type, number)


@app.get("/congress/members", tags=["Congress"], summary="Members of Congress")
async def congress_members(limit: int = Query(10, le=250)):
    return await congress.members(limit)


@app.get("/congress/votes", tags=["Congress"], summary="Roll-call votes by chamber")
async def congress_votes(chamber: str = "house", congress_session: int = 118, limit: int = Query(10, le=250)):
    return await congress.votes(chamber, congress_session, limit)


# ── FDA ──────────────────────────────────────────────────────────

@app.get("/fda/drug-events", tags=["FDA"], summary="Drug adverse-event reports")
async def fda_drug_events(search: str = "", limit: int = Query(10, le=100)):
    return await fda.drug_events(search, limit)


@app.get("/fda/drug-recalls", tags=["FDA"], summary="Drug recall enforcement reports")
async def fda_drug_recalls(search: str = "", limit: int = Query(10, le=100)):
    return await fda.drug_recalls(search, limit)


@app.get("/fda/food-recalls", tags=["FDA"], summary="Food recall enforcement reports")
async def fda_food_recalls(search: str = "", limit: int = Query(10, le=100)):
    return await fda.food_recalls(search, limit)


# ── Clinical Trials ──────────────────────────────────────────────

@app.get("/clinical-trials", tags=["Clinical Trials"], summary="Search ClinicalTrials.gov")
async def clinical_trials_search(condition: str = "", intervention: str = "",
                                  status: str = "", limit: int = Query(10, le=100)):
    return await clinicaltrials.search(condition, intervention, status, limit)


@app.get("/clinical-trials/{nct_id}", tags=["Clinical Trials"], summary="Single trial by NCT ID")
async def clinical_trial(nct_id: str):
    return await clinicaltrials.study(nct_id)


# ── EIA ──────────────────────────────────────────────────────────

@app.get("/eia", tags=["EIA"], summary="List available EIA datasets")
async def eia_datasets():
    return await eia.datasets()


@app.get("/eia/gas-prices", tags=["EIA"], summary="Gasoline prices")
async def eia_gas(limit: int = Query(10, le=100)):
    return await eia.gas_prices(limit)


@app.get("/eia/electricity", tags=["EIA"], summary="Electricity generation and retail data")
async def eia_electricity(limit: int = Query(10, le=100)):
    return await eia.electricity(limit)


@app.get("/eia/{route:path}", tags=["EIA"], summary="Generic EIA dataset query by route")
async def eia_query(route: str, frequency: str = "annual", data: str = "value",
                     limit: int = Query(10, le=1000)):
    return await eia.query(route, frequency, data, limit)


# ── FEMA ─────────────────────────────────────────────────────────

@app.get("/fema/disasters", tags=["FEMA"], summary="Disaster declarations")
async def fema_disasters(limit: int = Query(10, le=1000)):
    return await fema.disasters(limit)


@app.get("/fema/grants", tags=["FEMA"], summary="FEMA grant awards")
async def fema_grants(limit: int = Query(10, le=1000)):
    return await fema.grants(limit)


@app.get("/fema/flood-claims", tags=["FEMA"], summary="NFIP flood insurance claims")
async def fema_flood_claims(limit: int = Query(10, le=1000)):
    return await fema.flood_claims(limit)


# ── Federal Register ────────────────────────────────────────────

@app.get("/federal-register", tags=["Federal Register"], summary="Search the Federal Register")
async def fed_register(term: str = "", doc_type: str = "", agency: str = "",
                        limit: int = Query(10, le=100)):
    """Search Federal Register. doc_type: RULE, PRORULE, NOTICE, PRESDOCU."""
    return await federal_register.documents(limit, doc_type, agency, term)


@app.get("/federal-register/{doc_number}", tags=["Federal Register"], summary="Single Federal Register document")
async def fed_register_doc(doc_number: str):
    return await federal_register.document(doc_number)


# ── JEFS (Judicial Financial Disclosures) — DISABLED 2026-06-11 ───
# Temporarily removed from the API. Registration needs a headed browser plus a
# human-solved reCAPTCHA, so it can never run on the headless server, and the
# search/facets routes are useless without a session. To re-enable: uncomment
# the block below, the `jefs` import near the top of this file, and the JEFS
# entry in API_TAGS. The client + full flow stay in app/clients/jefs.py and
# docs/JEFS_API.md.
#
# @app.post("/jefs/register", tags=["JEFS"], summary="Open a JEFS session (Playwright + reCAPTCHA)")
# async def jefs_register(name: str, occupation: str, email: str, phone: str,
#                         address_line1: str, city: str, state: str, postalcode: str,
#                         address_line2: str = "", representing: str = "Self",
#                         representing_address: str = "", headed: bool = True):
#     """Open a Playwright browser to register a JEFS session. Fills the registration
#     form with your real name, occupation, email, phone, and mailing address (and who
#     you're requesting on behalf of — "Self" by default); you then solve the reCAPTCHA
#     and click "Enter Database", certifying under penalty of perjury (28 U.S.C. § 1746).
#     Needs a visible browser — run DataGod locally, not on a headless server. The browser
#     opens headed by default."""
#     return await jefs.register(name, occupation, email, phone, address_line1,
#                                address_line2, city, state, postalcode, representing,
#                                representing_address, headed)
#
#
# @app.get("/jefs/facets", tags=["JEFS"], summary="JEFS filter facets (needs session)")
# async def jefs_get_facets():
#     """Get filter dropdowns (years, courts, positions, report types). Requires active session."""
#     return await jefs.get_facets()
#
#
# @app.get("/jefs/search", tags=["JEFS"], summary="Search judicial disclosures (needs session)")
# async def jefs_search(q: str = "", year: str = "", court_type: str = "",
#                        start: int = 0):
#     """Search judicial financial disclosures. Requires active session."""
#     facets = {}
#     if year: facets["operating_year_s"] = [year]
#     if court_type: facets["court_type_s"] = [court_type]
#     return await jefs.search(q, facets, start=start)
#
#
# @app.post("/jefs/reset", tags=["JEFS"], summary="Clear the JEFS session")
# async def jefs_reset():
#     """Clear JEFS session. Must re-register before next call."""
#     return await jefs.reset()


# ── House Financial Disclosures ──────────────────────────────────

@app.get("/house-disclosures/members", tags=["House Disclosures"], summary="House member financial disclosures")
async def house_members(last_name: str = "", year: str = "", state: str = "",
                         district: str = ""):
    """Search House member financial disclosures (stock trades)."""
    return await house_fd.search_members(last_name, year, state, district)


@app.get("/house-disclosures/candidates", tags=["House Disclosures"], summary="House candidate financial disclosures")
async def house_candidates(last_name: str = "", year: str = "", state: str = "",
                            district: str = ""):
    return await house_fd.search_candidates(last_name, year, state, district)


# ── NARA (US National Archives Catalog) ──────────────────────────

@app.get("/nara/search", tags=["NARA"], summary="Search the National Archives Catalog")
async def nara_search(q: str = "", page: int = 1):
    """Search the National Archives Catalog (all record groups + the 14 presidential libraries). 20 results/page."""
    return await nara.search(q, page)


@app.get("/nara/record/{na_id}", tags=["NARA"], summary="Single catalog record by NAID")
async def nara_record(na_id: str):
    """A single catalog record by National Archives Identifier (NAID)."""
    return await nara.record(na_id)


# ── National Security Archive (NGO; VRR scrape) ──────────────────

@app.get("/nsarchive/search", tags=["NSArchive"], summary="Search the National Security Archive VRR")
async def nsarchive_search(q: str = "", page: int = 1):
    """Search the National Security Archive Virtual Reading Room (empty q browses). 20/page."""
    return await nsarchive.search(q, page)


@app.get("/nsarchive/document/{doc_id}", tags=["NSArchive"], summary="Single VRR document by id-slug")
async def nsarchive_document(doc_id: str):
    """One VRR document by its '{id}-{slug}' path (from search results)."""
    return await nsarchive.document(doc_id)


# ── Smithsonian Open Access ──────────────────────────────────────

@app.get("/smithsonian/search", tags=["Smithsonian"], summary="Search Smithsonian Open Access")
async def smithsonian_search(q: str = "", start: int = 0, rows: int = Query(10, le=100),
                             sort: str = "", obj_type: str = ""):
    """Search 11M+ Open Access records. sort: relevancy|newest|updated|random."""
    return await smithsonian.search(q, start, rows, sort, obj_type)


@app.get("/smithsonian/object/{object_id:path}", tags=["Smithsonian"], summary="Full object record by EDAN id")
async def smithsonian_object(object_id: str):
    """Full metadata record by EDAN id."""
    return await smithsonian.content(object_id)


@app.get("/smithsonian/category/{category}/search", tags=["Smithsonian"], summary="Search within a Smithsonian category")
async def smithsonian_category(category: str, q: str = "", start: int = 0,
                               rows: int = Query(10, le=100)):
    """Search within art_design | history_culture | science_technology."""
    return await smithsonian.category_search(category, q, start, rows)


@app.get("/smithsonian/terms/{category}", tags=["Smithsonian"], summary="Controlled-vocabulary terms")
async def smithsonian_terms(category: str):
    """Controlled-vocab terms: culture, topic, place, object_type, data_source, date, name."""
    return await smithsonian.terms(category)


@app.get("/smithsonian/stats", tags=["Smithsonian"], summary="Open Access dataset statistics")
async def smithsonian_stats():
    """Open Access dataset statistics."""
    return await smithsonian.stats()


# ── Wilson Center Digital Archive (local mirror) ─────────────────

@app.get("/wilson/documents", tags=["Wilson Center"], summary="Search the Wilson Center mirror")
async def wilson_documents(q: str = "", page: int = 1,
                           items_per_page: int = Query(10, le=100)):
    """Full-text search the local Wilson Center mirror (16,756 declassified documents)."""
    return await wilson.search_documents(q, page, items_per_page)


@app.get("/wilson/document/{slug}", tags=["Wilson Center"], summary="Single Wilson document by slug")
async def wilson_document(slug: str):
    """Full record for one document by slug: title, source, subjects, download availability."""
    return await wilson.document(slug)


# ── Cross-Reference ──────────────────────────────────────────────

@app.get("/cross-reference/company/{name}", tags=["Cross-Reference"], summary="Company across EDGAR + USAspending + FEC")
async def xref_company(name: str):
    """Cross-reference a company across EDGAR + USAspending + FEC."""
    return await cross_reference.company_profile(name)


@app.get("/cross-reference/politician/{last_name}", tags=["Cross-Reference"], summary="Politician across House disclosures + FEC")
async def xref_politician(last_name: str, first_name: str = ""):
    """Cross-reference a politician across House disclosures + FEC."""
    return await cross_reference.politician_profile(last_name, first_name)


# ── Cache Management ─────────────────────────────────────────────

@app.post("/admin/clear-cache", tags=["Admin"], summary="Clear the in-memory cache")
async def admin_clear_cache():
    clear_cache()
    return {"status": "cache cleared"}
