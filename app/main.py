"""
DataGod — Unified API for 15 US Government data sources + Nasdaq.com.

One API, all the data. Free.
"""

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse

from .auth import UnauthorizedError, require_api_key
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
    jefs,
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

app = FastAPI(
    title="DataGod",
    description="Unified API for 15 US Government data sources + Nasdaq quotes",
    version="0.1.0",
    dependencies=[Depends(require_api_key)],
)

app.add_middleware(ResponseEnvelopeMiddleware)


@app.exception_handler(UnauthorizedError)
async def unauthorized_handler(request: Request, exc: UnauthorizedError) -> JSONResponse:
    """Render auth failures in DataGod's standard error-envelope shape (HTTP 401)."""
    return JSONResponse(
        status_code=401,
        content={"error": True, "source": "auth", "upstream_status": 401, "message": str(exc)},
    )


# ── Health ───────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {
        "name": "DataGod",
        "version": "0.1.0",
        "sources": 19,
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


@app.get("/health", tags=["Health"])
async def health():
    """Public liveness probe (no API key required)."""
    return {"status": "ok"}


# ── FRED ─────────────────────────────────────────────────────────

@app.get("/fred/{series_id}", tags=["FRED"])
async def fred_series(series_id: str, limit: int = Query(10, le=1000)):
    return await fred.get_series(series_id, limit)


@app.get("/fred", tags=["FRED"])
async def fred_search(q: str = Query("", description="Search series by keyword"),
                      limit: int = Query(10, le=100)):
    if q:
        return await fred.search(q, limit)
    return {"hint": "Use /fred/{series_id} or /fred?q=keyword",
            "common_series": {"GDP": "Gross Domestic Product", "UNRATE": "Unemployment Rate",
                               "CPIAUCSL": "CPI", "FEDFUNDS": "Fed Funds Rate",
                               "DGS10": "10Y Treasury", "SP500": "S&P 500"}}


# ── EDGAR ────────────────────────────────────────────────────────

@app.get("/edgar/company/{cik}", tags=["EDGAR"])
async def edgar_company(cik: str):
    """Company metadata + filing history. Accepts CIK number or ticker (e.g., AAPL)."""
    return await edgar.company(cik)


@app.get("/edgar/financials/{cik}", tags=["EDGAR"])
async def edgar_financials(cik: str):
    """All XBRL financial facts for a company."""
    return await edgar.financials(cik)


@app.get("/edgar/concept/{cik}/{concept}", tags=["EDGAR"])
async def edgar_concept(cik: str, concept: str, taxonomy: str = "us-gaap"):
    """One concept's history (e.g., Revenues, Assets, NetIncomeLoss)."""
    return await edgar.concept(cik, concept, taxonomy)


@app.get("/edgar/frames/{concept}", tags=["EDGAR"])
async def edgar_frames(concept: str, unit: str = "USD", period: str = "CY2023",
                        taxonomy: str = "us-gaap"):
    """Cross-company comparison. One concept for ALL companies."""
    return await edgar.frames(concept, unit, period, taxonomy)


@app.get("/edgar/search", tags=["EDGAR"])
async def edgar_search(q: str, forms: str = "", limit: int = Query(10, le=100)):
    """Full-text search inside filing documents."""
    return await edgar.search_filings(q, forms, limit)


# ── Nasdaq ───────────────────────────────────────────────────────

@app.get("/nasdaq/quote/{ticker}", tags=["Nasdaq"])
async def nasdaq_quote(ticker: str, asset_class: str = "stocks"):
    """Market cap, sector, industry, P/E, dividend, 52-week range."""
    return await nasdaq.summary(ticker, asset_class)


@app.get("/nasdaq/price/{ticker}", tags=["Nasdaq"])
async def nasdaq_price(ticker: str, asset_class: str = "stocks"):
    """Real-time price, bid/ask, volume, percent change."""
    return await nasdaq.info(ticker, asset_class)


@app.get("/nasdaq/history/{ticker}", tags=["Nasdaq"])
async def nasdaq_history(ticker: str, fromdate: str, todate: str,
                          limit: int = Query(30, le=260),
                          asset_class: str = "stocks"):
    """Daily OHLCV between two dates (YYYY-MM-DD). Newest row first."""
    return await nasdaq.historical(ticker, fromdate, todate, limit, asset_class)


@app.get("/nasdaq/dividends/{ticker}", tags=["Nasdaq"])
async def nasdaq_dividends(ticker: str, asset_class: str = "stocks"):
    """Dividend history."""
    return await nasdaq.dividends(ticker, asset_class)


# ── yfinance (Yahoo Finance) ─────────────────────────────────────

@app.get("/yfinance/info/{ticker}", tags=["yfinance"])
async def yf_info(ticker: str):
    """Full ticker info: ~140 fields incl. market cap, P/E, EPS, beta, margins, ROE, analyst targets."""
    return await yfin.info(ticker)


@app.get("/yfinance/history/{ticker}", tags=["yfinance"])
async def yf_history(ticker: str, period: str = "1mo", interval: str = "1d"):
    """OHLCV history. period: 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max. interval: 1m,5m,1h,1d,1wk,1mo."""
    return await yfin.history(ticker, period, interval)


@app.get("/yfinance/news/{ticker}", tags=["yfinance"])
async def yf_news(ticker: str):
    """Recent news headlines linked to the ticker."""
    return await yfin.news(ticker)


@app.get("/yfinance/recommendations/{ticker}", tags=["yfinance"])
async def yf_recommendations(ticker: str):
    """Analyst recommendation history."""
    return await yfin.recommendations(ticker)


@app.get("/yfinance/holders/{ticker}", tags=["yfinance"])
async def yf_holders(ticker: str):
    """Major, institutional, and mutual-fund holders."""
    return await yfin.holders(ticker)


@app.get("/yfinance/financials/{ticker}", tags=["yfinance"])
async def yf_financials(ticker: str):
    """Annual + quarterly income statement, balance sheet, cash flow."""
    return await yfin.financials(ticker)


@app.get("/yfinance/dividends/{ticker}", tags=["yfinance"])
async def yf_dividends(ticker: str):
    """Dividend payment history."""
    return await yfin.dividends(ticker)


@app.get("/yfinance/options/{ticker}", tags=["yfinance"])
async def yf_options(ticker: str, expiry: str = ""):
    """Options chain. expiry blank → list expiries; else calls+puts for that date."""
    return await yfin.options(ticker, expiry)


# ── USAspending ──────────────────────────────────────────────────

@app.get("/usaspending/agencies", tags=["USAspending"])
async def usaspending_agencies():
    return await usaspending.agencies()


@app.get("/usaspending/search", tags=["USAspending"])
async def usaspending_search(q: str, start_date: str = "", end_date: str = "",
                              limit: int = Query(10, le=100)):
    """Search federal awards by keyword."""
    return await usaspending.search_awards([q], start_date, end_date, limit)


@app.get("/usaspending/by-agency", tags=["USAspending"])
async def usaspending_by_agency(fy: str = "2025", quarter: str = "1"):
    return await usaspending.spending_by_agency(fy, quarter)


# ── Census ───────────────────────────────────────────────────────

@app.get("/census/population", tags=["Census"])
async def census_population(year: int = 2022):
    return await census.population_by_state(year)


@app.get("/census/income", tags=["Census"])
async def census_income(year: int = 2022):
    return await census.income_by_state(year)


@app.get("/census/acs", tags=["Census"])
async def census_acs(variables: str = "NAME,B01001_001E", year: int = 2022,
                      geo_for: str = "state:*", geo_in: str = ""):
    """Raw ACS query. variables: comma-separated ACS variable codes."""
    return await census.acs(variables, year, geo_for, geo_in)


# ── BLS ──────────────────────────────────────────────────────────

@app.get("/bls/{series_id}", tags=["BLS"])
async def bls_series(series_id: str, start_year: int = 2024, end_year: int = 2026):
    """Get BLS series. Shortcuts: unemployment, cpi, nonfarm_employment, ppi, hourly_earnings."""
    return await bls.series(series_id, start_year, end_year)


# ── Treasury ─────────────────────────────────────────────────────

@app.get("/treasury/debt", tags=["Treasury"])
async def treasury_debt(limit: int = Query(5, le=100)):
    return await treasury.debt(limit)


@app.get("/treasury/rates", tags=["Treasury"])
async def treasury_rates(limit: int = Query(5, le=100)):
    return await treasury.interest_rates(limit)


@app.get("/treasury/exchange", tags=["Treasury"])
async def treasury_exchange(limit: int = Query(5, le=100)):
    return await treasury.exchange_rates(limit)


# ── FEC ──────────────────────────────────────────────────────────

@app.get("/fec/candidates", tags=["FEC"])
async def fec_candidates(office: str = "", state: str = "", limit: int = Query(10, le=100)):
    """Search candidates. office: P, S, H."""
    return await fec.candidates(office, state, limit)


@app.get("/fec/contributions", tags=["FEC"])
async def fec_contributions(name: str = "", candidate_id: str = "",
                             limit: int = Query(10, le=100)):
    return await fec.contributions(name, candidate_id, limit)


@app.get("/fec/totals", tags=["FEC"])
async def fec_totals(office: str = "P", year: int = 2024, limit: int = Query(10, le=100)):
    """Candidate financial totals by receipts."""
    return await fec.candidate_totals(office, year, limit)


# ── Congress ─────────────────────────────────────────────────────

@app.get("/congress/bills", tags=["Congress"])
async def congress_bills(limit: int = Query(10, le=250), congress_num: int = 0):
    return await congress.bills(limit, congress_num)


@app.get("/congress/bill/{congress_num}/{bill_type}/{number}", tags=["Congress"])
async def congress_bill(congress_num: int, bill_type: str, number: int):
    return await congress.bill_detail(congress_num, bill_type, number)


@app.get("/congress/members", tags=["Congress"])
async def congress_members(limit: int = Query(10, le=250)):
    return await congress.members(limit)


@app.get("/congress/votes", tags=["Congress"])
async def congress_votes(chamber: str = "house", congress_session: int = 118, limit: int = Query(10, le=250)):
    return await congress.votes(chamber, congress_session, limit)


# ── FDA ──────────────────────────────────────────────────────────

@app.get("/fda/drug-events", tags=["FDA"])
async def fda_drug_events(search: str = "", limit: int = Query(10, le=100)):
    return await fda.drug_events(search, limit)


@app.get("/fda/drug-recalls", tags=["FDA"])
async def fda_drug_recalls(search: str = "", limit: int = Query(10, le=100)):
    return await fda.drug_recalls(search, limit)


@app.get("/fda/food-recalls", tags=["FDA"])
async def fda_food_recalls(search: str = "", limit: int = Query(10, le=100)):
    return await fda.food_recalls(search, limit)


# ── Clinical Trials ──────────────────────────────────────────────

@app.get("/clinical-trials", tags=["Clinical Trials"])
async def clinical_trials_search(condition: str = "", intervention: str = "",
                                  status: str = "", limit: int = Query(10, le=100)):
    return await clinicaltrials.search(condition, intervention, status, limit)


@app.get("/clinical-trials/{nct_id}", tags=["Clinical Trials"])
async def clinical_trial(nct_id: str):
    return await clinicaltrials.study(nct_id)


# ── EIA ──────────────────────────────────────────────────────────

@app.get("/eia", tags=["EIA"])
async def eia_datasets():
    return await eia.datasets()


@app.get("/eia/gas-prices", tags=["EIA"])
async def eia_gas(limit: int = Query(10, le=100)):
    return await eia.gas_prices(limit)


@app.get("/eia/electricity", tags=["EIA"])
async def eia_electricity(limit: int = Query(10, le=100)):
    return await eia.electricity(limit)


@app.get("/eia/{route:path}", tags=["EIA"])
async def eia_query(route: str, frequency: str = "annual", data: str = "value",
                     limit: int = Query(10, le=1000)):
    return await eia.query(route, frequency, data, limit)


# ── FEMA ─────────────────────────────────────────────────────────

@app.get("/fema/disasters", tags=["FEMA"])
async def fema_disasters(limit: int = Query(10, le=1000)):
    return await fema.disasters(limit)


@app.get("/fema/grants", tags=["FEMA"])
async def fema_grants(limit: int = Query(10, le=1000)):
    return await fema.grants(limit)


@app.get("/fema/flood-claims", tags=["FEMA"])
async def fema_flood_claims(limit: int = Query(10, le=1000)):
    return await fema.flood_claims(limit)


# ── Federal Register ────────────────────────────────────────────

@app.get("/federal-register", tags=["Federal Register"])
async def fed_register(term: str = "", doc_type: str = "", agency: str = "",
                        limit: int = Query(10, le=100)):
    """Search Federal Register. doc_type: RULE, PRORULE, NOTICE, PRESDOCU."""
    return await federal_register.documents(limit, doc_type, agency, term)


@app.get("/federal-register/{doc_number}", tags=["Federal Register"])
async def fed_register_doc(doc_number: str):
    return await federal_register.document(doc_number)


# ── JEFS (Judicial Financial Disclosures) ────────────────────────

@app.post("/jefs/register", tags=["JEFS"])
async def jefs_register(name: str, occupation: str, address: str, headed: bool = True):
    """Open a Playwright browser to register a JEFS session.
    Required: real name, occupation, address (under penalty of perjury per JEFS terms).
    The browser opens headed; user solves reCAPTCHA + submits user-agreement."""
    return await jefs.register(name, occupation, address, headed)


@app.get("/jefs/facets", tags=["JEFS"])
async def jefs_get_facets():
    """Get filter dropdowns (years, courts, positions, report types). Requires active session."""
    return await jefs.get_facets()


@app.get("/jefs/search", tags=["JEFS"])
async def jefs_search(q: str = "", year: str = "", court_type: str = "",
                       start: int = 0):
    """Search judicial financial disclosures. Requires active session."""
    facets = {}
    if year: facets["operating_year_s"] = [year]
    if court_type: facets["court_type_s"] = [court_type]
    return await jefs.search(q, facets, start=start)


@app.post("/jefs/reset", tags=["JEFS"])
async def jefs_reset():
    """Clear JEFS session. Must re-register before next call."""
    return await jefs.reset()


# ── House Financial Disclosures ──────────────────────────────────

@app.get("/house-disclosures/members", tags=["House Disclosures"])
async def house_members(last_name: str = "", year: str = "", state: str = "",
                         district: str = ""):
    """Search House member financial disclosures (stock trades)."""
    return await house_fd.search_members(last_name, year, state, district)


@app.get("/house-disclosures/candidates", tags=["House Disclosures"])
async def house_candidates(last_name: str = "", year: str = "", state: str = "",
                            district: str = ""):
    return await house_fd.search_candidates(last_name, year, state, district)


# ── NARA (US National Archives Catalog) ──────────────────────────

@app.get("/nara/search", tags=["NARA"])
async def nara_search(q: str = "", page: int = 1):
    """Search the National Archives Catalog (all record groups + the 14 presidential libraries). 20 results/page."""
    return await nara.search(q, page)


@app.get("/nara/record/{na_id}", tags=["NARA"])
async def nara_record(na_id: str):
    """A single catalog record by National Archives Identifier (NAID)."""
    return await nara.record(na_id)


# ── National Security Archive (NGO; VRR scrape) ──────────────────

@app.get("/nsarchive/search", tags=["NSArchive"])
async def nsarchive_search(q: str = "", page: int = 1):
    """Search the National Security Archive Virtual Reading Room (empty q browses). 20/page."""
    return await nsarchive.search(q, page)


@app.get("/nsarchive/document/{doc_id}", tags=["NSArchive"])
async def nsarchive_document(doc_id: str):
    """One VRR document by its '{id}-{slug}' path (from search results)."""
    return await nsarchive.document(doc_id)


# ── Smithsonian Open Access ──────────────────────────────────────

@app.get("/smithsonian/search", tags=["Smithsonian"])
async def smithsonian_search(q: str = "", start: int = 0, rows: int = Query(10, le=100),
                             sort: str = "", obj_type: str = ""):
    """Search 11M+ Open Access records. sort: relevancy|newest|updated|random."""
    return await smithsonian.search(q, start, rows, sort, obj_type)


@app.get("/smithsonian/object/{object_id:path}", tags=["Smithsonian"])
async def smithsonian_object(object_id: str):
    """Full metadata record by EDAN id."""
    return await smithsonian.content(object_id)


@app.get("/smithsonian/category/{category}/search", tags=["Smithsonian"])
async def smithsonian_category(category: str, q: str = "", start: int = 0,
                               rows: int = Query(10, le=100)):
    """Search within art_design | history_culture | science_technology."""
    return await smithsonian.category_search(category, q, start, rows)


@app.get("/smithsonian/terms/{category}", tags=["Smithsonian"])
async def smithsonian_terms(category: str):
    """Controlled-vocab terms: culture, topic, place, object_type, data_source, date, name."""
    return await smithsonian.terms(category)


@app.get("/smithsonian/stats", tags=["Smithsonian"])
async def smithsonian_stats():
    """Open Access dataset statistics."""
    return await smithsonian.stats()


# ── Wilson Center Digital Archive (local mirror) ─────────────────

@app.get("/wilson/documents", tags=["Wilson Center"])
async def wilson_documents(q: str = "", page: int = 1,
                           items_per_page: int = Query(10, le=100)):
    """Full-text search the local Wilson Center mirror (16,756 declassified documents)."""
    return await wilson.search_documents(q, page, items_per_page)


@app.get("/wilson/document/{slug}", tags=["Wilson Center"])
async def wilson_document(slug: str):
    """Full record for one document by slug: title, source, subjects, download availability."""
    return await wilson.document(slug)


# ── Cross-Reference ──────────────────────────────────────────────

@app.get("/cross-reference/company/{name}", tags=["Cross-Reference"])
async def xref_company(name: str):
    """Cross-reference a company across EDGAR + USAspending + FEC."""
    return await cross_reference.company_profile(name)


@app.get("/cross-reference/politician/{last_name}", tags=["Cross-Reference"])
async def xref_politician(last_name: str, first_name: str = ""):
    """Cross-reference a politician across House disclosures + FEC."""
    return await cross_reference.politician_profile(last_name, first_name)


# ── Cache Management ─────────────────────────────────────────────

@app.post("/admin/clear-cache", tags=["Admin"])
async def admin_clear_cache():
    clear_cache()
    return {"status": "cache cleared"}
