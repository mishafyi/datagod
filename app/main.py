"""
DataGod — one API over 40 free US-government, global, markets, research, media, and trending data sources.

One API, all the data. Free.
"""

from fastapi import Depends, FastAPI, Query, Request, Response
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from .auth import UnauthorizedError, require_api_key, require_docs_auth
from .cache import clear_cache
from .clients import (
    arxiv,
    bls,
    census,
    cia,
    clinicaltrials,
    commons,
    comtrade,
    congress_gov as congress,
    cross_reference,
    ecb,
    edgar,
    eia,
    eonet,
    eurostat,
    fas,
    fec,
    federal_register,
    fema,
    fda,
    fred,
    frus,
    house_fd,
    imf,
    internetarchive,
    # jefs,  # disabled 2026-06-11 — see the JEFS route block below
    nara,
    nasa_images,
    nasdaq,
    newsnow,
    nsarchive,
    nws,
    scholar,
    smithsonian,
    tna,
    treasury,
    ucdp,
    usaspending,
    usgs,
    vault,
    wikipedia,
    # wilson,  # disabled 2026-07-02 — see the Wilson route block below
    worldbank,
    yfin,
)
from .middleware import ResponseEnvelopeMiddleware

API_DESCRIPTION = """\
**DataGod** unifies 40 free US-government, global, markets, research, media, and trending
data sources (plus a cross-reference aggregator) behind one HTTP API. Routes are
thin pass-throughs — each returns the upstream's JSON unchanged, wrapped in a
standard envelope.

## Authentication
Every data endpoint requires your API key in the **`X-API-Key`** header:

```bash
curl -H "X-API-Key: <your-key>" https://<your-datagod-host>/fred/GDP
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
    {"name": "CIA", "description": "CIA FOIA Electronic Reading Room — declassified CIA documents read from the Wayback Machine mirror (cia.gov blocks server-side clients); curated collections + single-document fetch, no full-text search."},
    {"name": "FRUS", "description": "Foreign Relations of the United States (history.state.gov) — the official documentary record of US foreign policy; full-text search + single documents."},
    {"name": "TNA", "description": "UK National Archives Discovery — catalog search of British government records."},
    {"name": "Vault", "description": "FBI Vault (vault.fbi.gov) — the FBI's FOIA library; curated famous subjects + page fetch."},
    {"name": "FAS", "description": "FAS Intelligence Resource Program (irp.fas.org) — mirrored intelligence-community documents: agency pages, programs, official documents."},
    {"name": "Smithsonian", "description": "Smithsonian Open Access (EDAN) — 11M+ museum/library/archive records."},
    # {"name": "Wilson Center", "description": "Wilson Center Digital Archive — local mirror of 16,756 declassified documents."},  # disabled 2026-07-02
    {"name": "arXiv", "description": "arXiv.org — full-text search of 2M+ scientific preprints (physics, math, CS/ML, biology, economics, statistics)."},
    {"name": "Scholar", "description": "Google Scholar via the vendored sort-google-scholar — citation-ranked paper search. Brittle: Google blocks scraping (CAPTCHA/429)."},
    {"name": "Trending", "description": "NewsNow (self-hosted) — ~50 trending/hot boards: Hacker News, GitHub trending, Product Hunt, plus Weibo/Zhihu/Douyin hot searches and CN finance wires. Ranked title+URL items."},
    {"name": "World Bank", "description": "World Bank Open Data — development indicators for every country (GDP, population, poverty, trade)."},
    {"name": "IMF", "description": "IMF SDMX-JSON — macroeconomic time series (IFS, DOT, BOP…). Upstream is slow and flaky."},
    {"name": "Eurostat", "description": "Eurostat — official EU statistics (JSON-stat); dimension filters pass through."},
    {"name": "ECB", "description": "ECB Data Portal — euro-area exchange rates, inflation, and interest rates via SDMX."},
    {"name": "Comtrade", "description": "UN Comtrade — global goods-trade flows (keyless public preview, ≤500 records, rate-limited)."},
    {"name": "UCDP", "description": "Uppsala Conflict Data Program — georeferenced armed-conflict events worldwide."},
    {"name": "USGS", "description": "USGS Earthquake Hazards — worldwide earthquake catalog (GeoJSON)."},
    {"name": "NWS", "description": "US National Weather Service — active weather alerts (keyless, User-Agent required)."},
    {"name": "EONET", "description": "NASA EONET — global natural events: wildfires, severe storms, volcanoes."},
    {"name": "Wikipedia", "description": "Wikipedia — page summaries, full-text search, and pageview statistics."},
    {"name": "NASA Images", "description": "NASA Image and Video Library — public-domain space/science videos, images, and audio with direct downloadable renditions (incl. mp4)."},
    {"name": "Internet Archive", "description": "Internet Archive — keyless item search (movies by default) + per-item file metadata with direct download paths. License is per item (licenseurl)."},
    {"name": "Commons", "description": "Wikimedia Commons — video-file search with direct file URLs and per-file license metadata (CC-BY / CC-BY-SA / PD)."},
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
        "sources": 35,
        "endpoints": {
            "economy": ["/fred", "/bls", "/treasury"],
            "economy_global": ["/worldbank", "/imf", "/eurostat", "/ecb", "/comtrade"],
            "markets": ["/edgar", "/nasdaq", "/yfinance"],
            "spending": ["/usaspending"],
            "politics": ["/fec", "/congress", "/house-disclosures"],
            "demographics": ["/census"],
            "health": ["/fda", "/clinical-trials"],
            "energy": ["/eia"],
            "disasters": ["/fema"],
            "conflicts_disasters": ["/ucdp", "/usgs", "/nws", "/eonet"],
            "regulations": ["/federal-register"],
            # "history": ["/wilson"],  # Wilson disabled 2026-07-02
            "museums": ["/smithsonian"],
            "archives": ["/nara", "/nsarchive", "/cia", "/frus", "/tna", "/vault", "/fas"],
            "reference": ["/wikipedia"],
            "video": ["/nasa", "/archive", "/commons"],
            "trending": ["/trending"],
            "cross_reference": ["/cross-reference/company", "/cross-reference/politician"],
        },
    }


@app.get("/health", tags=["Health"], summary="Liveness probe (public, no API key)")
async def health():
    """Public liveness probe (no API key required)."""
    return {"status": "ok"}


# ── FRED ─────────────────────────────────────────────────────────

@app.get("/fred/series/{series_id}", tags=["FRED"], summary="Fetch FRED series metadata")
async def fred_series_info(series_id: str):
    """Metadata for a FRED series (title, units, frequency, dates) — not observations."""
    return await fred.series_info(series_id)


@app.get("/fred/{series_id}", tags=["FRED"], summary="Fetch a FRED economic time series")
async def fred_series(series_id: str, limit: int = Query(10, le=1000),
                      offset: int = Query(0, ge=0),
                      sort_order: str = Query("asc", pattern="^(asc|desc)$"),
                      observation_start: str | None = Query(None, description="YYYY-MM-DD lower bound"),
                      observation_end: str | None = Query(None, description="YYYY-MM-DD upper bound")):
    return await fred.get_series(series_id, limit, offset, sort_order,
                                 observation_start, observation_end)


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
async def edgar_frames(concept: str, unit: str = "USD",
                        period: str = Query(..., description="e.g. CY2023, CY2023Q1, CY2023Q4I"),
                        taxonomy: str = "us-gaap"):
    """Cross-company comparison. One concept for ALL companies."""
    return await edgar.frames(concept=concept, period=period, unit=unit, taxonomy=taxonomy)


@app.get("/edgar/search", tags=["EDGAR"], summary="Full-text search inside filing documents")
async def edgar_search(q: str, forms: str = "", startdt: str = "", enddt: str = "",
                       offset: int = Query(0, ge=0, le=9900, alias="from"),
                       date_range: str = Query("", alias="dateRange"),
                       size: int | None = Query(None)):
    """Full-text search inside filing documents (thin pass-through to SEC EFTS). The
    SEC returns a fixed 100 hits per page and ignores page size; paginate with `from`
    in steps of 100 (0, 100, 200 … max 9900 — the SEC caps results at 10,000). Optional
    `forms` and `startdt`/`enddt` (YYYY-MM-DD), e.g.
    ?q=Ukraine&forms=10-Q&startdt=2026-01-01&enddt=2026-12-31&from=100."""
    params: dict = {"q": q, "from": offset}
    if forms:
        params["forms"] = forms
    if startdt:
        params["startdt"] = startdt
    if enddt:
        params["enddt"] = enddt
    if date_range:
        params["dateRange"] = date_range
    if size is not None:
        params["size"] = size
    return await edgar.search_filings(params)


@app.get("/edgar/submissions/{filename}", tags=["EDGAR"], summary="Submissions overflow file (1000+ filers)")
async def edgar_submissions_overflow(filename: str):
    """Overflow filings file for large filers, e.g. CIK0000320193-submissions-001.json
    (from the company route's filings.files[].name)."""
    return await edgar.submissions_overflow(filename)


@app.get("/edgar/document/{cik}/{accession}/{document:path}", tags=["EDGAR"], summary="Raw filing document bytes")
async def edgar_document(cik: str, accession: str, document: str):
    """Raw filing document from the EDGAR archives. `accession` is dashless
    (e.g. 000032019324000123); `document` is the primaryDocument (e.g. aapl-20240928.htm)."""
    result = await edgar.filing_document(cik, accession, document)
    if isinstance(result, dict):  # error-dict -> let the envelope wrap it
        return result
    return Response(content=result.content,
                    media_type=result.headers.get("content-type", "application/octet-stream"))


@app.get("/edgar/cik/{ticker}", tags=["EDGAR"], summary="Resolve a ticker to its CIK")
async def edgar_cik(ticker: str):
    """Resolve a ticker symbol to its zero-padded CIK, e.g. AAPL -> 0000320193."""
    return await edgar.ticker_to_cik(ticker)


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


@app.get("/nasdaq/financials/{ticker}", tags=["Nasdaq"], summary="Income statement, balance sheet, cash flow")
async def nasdaq_financials(ticker: str, frequency: str = "A"):
    """Financial statements. frequency: 'A' annual, 'Q' quarterly."""
    return await nasdaq.financials(ticker, frequency)


@app.get("/nasdaq/insider-trades/{ticker}", tags=["Nasdaq"], summary="Recent insider (Form 4) transactions")
async def nasdaq_insider_trades(ticker: str, limit: int = Query(15, le=100)):
    """Recent insider (Form 4) buy/sell transactions."""
    return await nasdaq.insider_trades(ticker, limit)


@app.get("/nasdaq/earnings-surprise/{ticker}", tags=["Nasdaq"], summary="Reported vs consensus EPS surprises")
async def nasdaq_earnings_surprise(ticker: str, limit: int = Query(15, le=100)):
    """Historical reported-vs-consensus EPS surprises."""
    return await nasdaq.earnings_surprise(ticker, limit)


@app.get("/nasdaq/calendar/earnings", tags=["Nasdaq"], summary="Companies reporting earnings on a date")
async def nasdaq_calendar_earnings(date: str):
    """Companies reporting earnings on a given day (YYYY-MM-DD, required)."""
    return await nasdaq.calendar_earnings(date)


@app.get("/nasdaq/calendar/ipo", tags=["Nasdaq"], summary="IPOs priced/expected on a date")
async def nasdaq_calendar_ipo(date: str):
    """IPOs priced/expected on a given day (YYYY-MM-DD, required)."""
    return await nasdaq.calendar_ipo(date)


@app.get("/nasdaq/screener", tags=["Nasdaq"], summary="Full stock-screener output")
async def nasdaq_screener(limit: int = Query(25, le=1000)):
    """Full stock-screener output (table rows)."""
    return await nasdaq.screener(limit)


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


@app.get("/yfinance/earnings/{ticker}", tags=["yfinance"], summary="Earnings history + next-earnings calendar")
async def yf_earnings(ticker: str, limit: int = Query(12, ge=1, le=100)):
    """Past/upcoming earnings dates (EPS estimate, reported EPS, surprise %) + next-earnings calendar."""
    return await yfin.earnings(ticker, limit)


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
                              limit: int = Query(10, le=100), page: int = Query(1, ge=1),
                              sort: str = "Award Amount", order: str = "desc",
                              award_type_codes: str = ""):
    """Search federal awards by keyword. award_type_codes: CSV (e.g. 'A,B,C,D,02,03,04,05');
    empty => contracts + grants default."""
    return await usaspending.search_awards([q], start_date=start_date, end_date=end_date,
                                           limit=limit, page=page, sort=sort, order=order,
                                           award_type_codes=award_type_codes)


@app.get("/usaspending/by-agency", tags=["USAspending"], summary="Spending totals by agency (fiscal year)")
async def usaspending_by_agency(fy: str, quarter: str = "1"):
    return await usaspending.spending_by_agency(fy, quarter)


# ── Census ───────────────────────────────────────────────────────

@app.get("/census/population", tags=["Census"], summary="Population by state")
async def census_population(year: int):
    return await census.population_by_state(year)


@app.get("/census/income", tags=["Census"], summary="Median household income by state")
async def census_income(year: int):
    return await census.income_by_state(year)


@app.get("/census/acs", tags=["Census"], summary="Raw ACS query (any variables and geography)")
async def census_acs(year: int, variables: str = "NAME,B01001_001E",
                      geo_for: str = "state:*", geo_in: str = "",
                      dataset: str = Query("acs5", pattern="^(acs1|acs5)$")):
    """Raw ACS query. variables: comma-separated ACS variable codes.
    dataset: acs5 (5-year, supports tracts) or acs1 (1-year, 65k+ population)."""
    return await census.acs(year=year, variables=variables, geo_for=geo_for,
                            geo_in=geo_in, dataset=dataset)


# ── BLS ──────────────────────────────────────────────────────────

class BlsBatch(BaseModel):
    series_ids: list[str]
    start_year: int
    end_year: int


@app.post("/bls/batch", tags=["BLS"], summary="BLS multi-series batch (POST, registrationkey added when set)")
async def bls_multiple(body: BlsBatch):
    """Batch-fetch multiple BLS series in one call. Each id may be a shortcut
    (unemployment, cpi, nonfarm_employment, ppi, hourly_earnings) or a raw BLS id."""
    return await bls.multiple(body.series_ids, body.start_year, body.end_year)


@app.get("/bls/{series_id}", tags=["BLS"], summary="BLS series (CPI, unemployment, wages, PPI)")
async def bls_series(series_id: str, start_year: int, end_year: int):
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
async def fec_candidates(office: str = "", state: str = "", limit: int = Query(10, le=100),
                          page: int = Query(1, ge=1)):
    """Search candidates. office: P, S, H."""
    return await fec.candidates(office, state, limit, page)


@app.get("/fec/contributions", tags=["FEC"], summary="Campaign contributions")
async def fec_contributions(name: str = "", candidate_id: str = "",
                             limit: int = Query(10, le=100), page: int = Query(1, ge=1)):
    return await fec.contributions(name, candidate_id, limit, page)


@app.get("/fec/totals", tags=["FEC"], summary="Candidate financial totals by receipts")
async def fec_totals(year: int = Query(..., description="election year"), office: str = "P",
                      limit: int = Query(10, le=100), page: int = Query(1, ge=1)):
    """Candidate financial totals by receipts."""
    return await fec.candidate_totals(election_year=year, office=office,
                                      per_page=limit, page=page)


# ── Congress ─────────────────────────────────────────────────────

@app.get("/congress/bills", tags=["Congress"], summary="Recent bills")
async def congress_bills(limit: int = Query(10, le=250), congress_num: int = 0,
                          offset: int = Query(0, ge=0)):
    return await congress.bills(limit, congress_num, offset)


@app.get("/congress/bill/{congress_num}/{bill_type}/{number}", tags=["Congress"], summary="Single bill detail")
async def congress_bill(congress_num: int, bill_type: str, number: int):
    return await congress.bill_detail(congress_num, bill_type, number)


@app.get("/congress/members", tags=["Congress"], summary="Members of Congress")
async def congress_members(limit: int = Query(10, le=250), offset: int = Query(0, ge=0)):
    return await congress.members(limit, offset)


@app.get("/congress/votes", tags=["Congress"], summary="Recent House roll-call votes")
async def congress_votes(congress_session: int = 118, limit: int = Query(10, le=250),
                          offset: int = Query(0, ge=0)):
    return await congress.votes(congress_session, limit, offset)


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
async def eia_electricity(limit: int = Query(10, le=100), data_field: str = "revenue",
                           frequency: str = "annual"):
    """Electricity retail data. data_field: revenue, sales, price, customers."""
    return await eia.electricity(limit, data_field, frequency)


@app.get("/eia/{route:path}", tags=["EIA"], summary="Generic EIA dataset query by route")
async def eia_query(route: str, frequency: str = "annual", data: str = "value",
                     limit: int = Query(10, le=5000), offset: int = Query(0, ge=0),
                     sort_col: str = "period", sort_dir: str = "desc"):
    return await eia.query(route, frequency=frequency, data_field=data, length=limit,
                           offset=offset, sort_col=sort_col, sort_dir=sort_dir)


# ── FEMA ─────────────────────────────────────────────────────────

@app.get("/fema/disasters", tags=["FEMA"], summary="Disaster declarations")
async def fema_disasters(limit: int = Query(10, le=1000),
                          state: str = Query("", description="Two-letter USPS state code, e.g. CA"),
                          declared_since: str = Query("", description="ISO date, e.g. 2024-01-01; filters declarationDate >=")):
    return await fema.disasters(limit, state, declared_since)


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


@app.get("/house-disclosures/pdf", tags=["House Disclosures"], summary="Fetch a disclosure PDF by path")
async def house_pdf(path: str):
    """Fetch a member/candidate disclosure PDF by its `pdf_url`-style path
    (e.g. public_disc/ptr-pdfs/2024/20024542.pdf). Returns raw application/pdf bytes."""
    result = await house_fd.fetch_pdf(path)
    if isinstance(result, dict):  # error-dict -> let the envelope wrap it
        return result
    return Response(content=result, media_type="application/pdf")


# ── NARA (US National Archives Catalog) ──────────────────────────

@app.get("/nara/search", tags=["NARA"], summary="Search the National Archives Catalog")
async def nara_search(q: str = "", page: int = 1, available_online: bool = False,
                       type_of_materials: str = "", level_of_description: str = ""):
    """Search the National Archives Catalog (all record groups + the 14 presidential libraries). 20 results/page."""
    return await nara.search(q, page, available_online, type_of_materials, level_of_description)


@app.get("/nara/record/{na_id}", tags=["NARA"], summary="Single catalog record by NAID")
async def nara_record(na_id: str):
    """A single catalog record by National Archives Identifier (NAID)."""
    return await nara.record(na_id)


# ── National Security Archive (NGO; VRR scrape) ──────────────────

@app.get("/nsarchive/search", tags=["NSArchive"], summary="Search the National Security Archive VRR")
async def nsarchive_search(q: str = "", page: int = 1, field_date_min: str = "",
                            field_date_max: str = "",
                            searched_fields: str = Query("", description='One of: All, Title, Source, "Document Text", Description')):
    """Search the National Security Archive Virtual Reading Room (empty q browses). 20/page.
    field_date_min/field_date_max are YYYY-MM-DD bounds."""
    return await nsarchive.search(q, page, field_date_min, field_date_max, searched_fields)


@app.get("/nsarchive/document/{doc_id}", tags=["NSArchive"], summary="Single VRR document by id-slug")
async def nsarchive_document(doc_id: str):
    """One VRR document by its '{id}-{slug}' path (from search results)."""
    return await nsarchive.document(doc_id)


# ── CIA FOIA Electronic Reading Room (via the Wayback mirror) ────

@app.get("/cia/collections", tags=["CIA"], summary="Famous reading-room collections (curated registry)")
async def cia_collections():
    """The curated registry of famous CIA reading-room collections (static)."""
    return await cia.collections()


@app.get("/cia/collection/{slug}", tags=["CIA"], summary="A reading-room collection's documents")
async def cia_collection(slug: str, page: int = 0):
    """One collection page via the Wayback mirror: description + document list.
    `page` forwards the site's 0-based listing pager."""
    return await cia.collection(slug, page)


@app.get("/cia/document/{doc_path}", tags=["CIA"], summary="Single reading-room document")
async def cia_document(doc_path: str):
    """One document by path segment (e.g. cia-rdp96-00788r001700210016-5):
    title, field metadata, body text, PDF URLs (original + archived)."""
    return await cia.document(doc_path)


# ── FRUS (Foreign Relations of the United States) ────────────────

@app.get("/frus/search", tags=["FRUS"], summary="Search FRUS (history.state.gov)")
async def frus_search(q: str, start: int = 1):
    """Full-text search across all FRUS volumes. `start` is the 1-based result
    offset (10/page; next page = start+10)."""
    return await frus.search(q, start)


@app.get("/frus/document/{volume}/{doc}", tags=["FRUS"], summary="Single FRUS document")
async def frus_document(volume: str, doc: int):
    """One FRUS document by volume id + doc number, e.g. frus1969-76v21 / 7."""
    return await frus.document(volume, doc)


# ── UK National Archives (Discovery) ─────────────────────────────

@app.get("/tna/search", tags=["TNA"], summary="Search UK National Archives Discovery")
async def tna_search(q: str, page: int = 1, per_page: int = Query(20, le=100),
                     series: str = Query("", description="Records series code, e.g. KV, HS, DEFE, CAB, PREM")):
    """Full-text search of Discovery record descriptions (32M+ records, official
    keyless API). `series` narrows to a series like KV (MI5) or HS (SOE)."""
    return await tna.search(q, page, per_page, series)


@app.get("/tna/record/{record_id}", tags=["TNA"], summary="Single Discovery record's details")
async def tna_record(record_id: str):
    """Full details for one record by Discovery id (from search results)."""
    return await tna.record(record_id)


# ── FAS Intelligence Resource Program (irp.fas.org) ──────────────

@app.get("/fas/sections", tags=["FAS"], summary="Verified IRP sections (curated registry)")
async def fas_sections():
    """The curated registry of verified FAS IRP sections (static)."""
    return await fas.sections()


@app.get("/fas/index/{path:path}", tags=["FAS"], summary="An IRP index page's links")
async def fas_index(path: str):
    """An IRP index page: title + same-site content links (nav filtered)."""
    return await fas.index(path)


@app.get("/fas/page/{path:path}", tags=["FAS"], summary="An IRP content page's full text")
async def fas_page(path: str):
    """An IRP content page: title, full text (capped) and PDF links."""
    return await fas.page(path)


# ── FBI Vault (via the Wayback mirror) ───────────────────────────

@app.get("/vault/subjects", tags=["Vault"], summary="Famous FBI Vault subjects (curated registry)")
async def vault_subjects():
    """The curated registry of famous FBI Vault subjects (static)."""
    return await vault.subjects()


@app.get("/vault/page/{path:path}", tags=["Vault"], summary="One Vault page (subject, folder or file)")
async def vault_page(path: str):
    """One Vault page by path: title, description, sub-folders, file pages, PDFs.
    The Vault nests (subject → folders → files) — walk it page by page."""
    return await vault.page(path)


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
                               rows: int = Query(10, le=100), sort: str = "", obj_type: str = ""):
    """Search within art_design | history_culture | science_technology.
    sort: relevancy|newest|updated|random."""
    return await smithsonian.category_search(category, q, start, rows, sort, obj_type)


@app.get("/smithsonian/terms/{category}", tags=["Smithsonian"], summary="Controlled-vocabulary terms")
async def smithsonian_terms(category: str):
    """Controlled-vocab terms: culture, topic, place, object_type, data_source, date, name."""
    return await smithsonian.terms(category)


@app.get("/smithsonian/stats", tags=["Smithsonian"], summary="Open Access dataset statistics")
async def smithsonian_stats():
    """Open Access dataset statistics."""
    return await smithsonian.stats()


# ── Wilson Center Digital Archive (local mirror) — DISABLED 2026-07-02 ───
#
# The Wilson source serves a LOCAL SQLite mirror (data/wilson.db, 228 MB) that
# is not distributed with the repo, so the routes are off by default. To
# re-enable: provision data/wilson.db (see docs/WILSON_DIGITAL_ARCHIVE_API.md),
# then uncomment the block below, the `wilson` import near the top of this
# file, the Wilson entry in API_TAGS, and the "history" entry in the root
# endpoint map. The client stays in app/clients/wilson.py.

# @app.get("/wilson/documents", tags=["Wilson Center"], summary="Search the Wilson Center mirror")
# async def wilson_documents(q: str = "", page: int = 1,
#                            items_per_page: int = Query(10, le=100)):
#     """Full-text search the local Wilson Center mirror (16,756 declassified documents)."""
#     return await wilson.search_documents(q, page, items_per_page)


# @app.get("/wilson/document/{slug}", tags=["Wilson Center"], summary="Single Wilson document by slug")
# async def wilson_document(slug: str):
#     """Full record for one document by slug: title, source, subjects, download availability."""
#     return await wilson.document(slug)


# ── arXiv (scientific preprints) ─────────────────────────────────

@app.get("/arxiv/search", tags=["arXiv"], summary="Full-text search arXiv preprints")
async def arxiv_search(query: str, start: int = Query(0, ge=0),
                       max_results: int = Query(10, ge=1, le=100),
                       sort_by: str = "relevance", sort_order: str = "descending"):
    """Search arXiv (physics, math, CS/ML, bio, econ). sort_by: relevance|lastUpdatedDate|submittedDate."""
    return await arxiv.search(query, start, max_results, sort_by, sort_order)


@app.get("/arxiv/{arxiv_id}", tags=["arXiv"], summary="Fetch arXiv paper(s) by id")
async def arxiv_get(arxiv_id: str):
    """Fetch one or more arXiv papers by id (e.g. 2301.00001, or comma-separated ids)."""
    return await arxiv.get_by_id(arxiv_id)


# ── Scholar (Google Scholar — vendored sort-google-scholar) ──────

@app.get("/scholar/search", tags=["Scholar"], summary="Search Google Scholar, ranked by citations (brittle)")
async def scholar_search(keyword: str, nresults: int = Query(20, ge=1, le=100),
                         sort_by: str = "Citations", start_year: int | None = None,
                         end_year: int | None = None):
    """Citation-ranked Google Scholar search. Brittle: Google blocks scraping (CAPTCHA/429) → error-dict."""
    return await scholar.search(keyword, nresults, sort_by, start_year, end_year)


# ── Trending (NewsNow, self-hosted) ──────────────────────────────

@app.get("/trending", tags=["Trending"], summary="List available trending-board ids")
async def trending_boards():
    """Board ids servable by /trending/{source_id} (pinned newsnow release — see app/clients/newsnow.py)."""
    return {"sources": list(newsnow.SOURCES)}


@app.get("/trending/{source_id}", tags=["Trending"], summary="One trending board — ranked title+URL items")
async def trending_board(source_id: str, latest: bool = True):
    """Hot list for one board (ids: GET /trending). Rank = item position; latest=false accepts newsnow's cache."""
    return await newsnow.source(source_id, latest)


# ── World Bank ───────────────────────────────────────────────────

@app.get("/worldbank/countries", tags=["World Bank"], summary="List all countries (region, income level)")
async def worldbank_countries(per_page: int = Query(300, le=400)):
    """All countries/aggregates with region, income level, and ISO codes."""
    return await worldbank.countries(per_page)


@app.get("/worldbank/{indicator}", tags=["World Bank"], summary="One indicator across countries")
async def worldbank_indicator(indicator: str,
                              countries: str = Query("all", description='ISO2 codes joined with ";" (e.g. us;cn;fr) or "all"'),
                              date_range: str = Query("", description="Year bounds as YYYY:YYYY"),
                              per_page: int = Query(200, le=1000)):
    """Indicator series, e.g. NY.GDP.MKTP.CD (GDP, current US$), SP.POP.TOTL
    (population). Response is [paging-metadata, rows]."""
    return await worldbank.indicator(indicator, countries, date_range, per_page)


# ── IMF ──────────────────────────────────────────────────────────

@app.get("/imf/structure/{dataset}", tags=["IMF"], summary="IMF dataset metadata (dimensions + code lists)")
async def imf_structure(dataset: str):
    """Dimensions and code lists for an IMF dataset code (e.g. WEO, BOP)."""
    return await imf.structure(dataset)


@app.get("/imf/{dataset}/{key}", tags=["IMF"], summary="IMF time series (via DBnomics; latest vintage)")
async def imf_series(dataset: str, key: str, limit: int = 100):
    """Series from an IMF dataset, e.g. /imf/WEO/USA.NGDP_RPCH (US real GDP
    growth, %, incl. IMF forecast years). Transport is DBnomics — the IMF's
    own legacy SDMX host was decommissioned in 2026."""
    return await imf.series(dataset, key, limit)


# ── Eurostat ─────────────────────────────────────────────────────

@app.get("/eurostat/{dataset}", tags=["Eurostat"], summary="Eurostat dataset (JSON-stat) with dimension filters")
async def eurostat_dataset(dataset: str, request: Request):
    """One dataset (e.g. tps00001 = population). Every query param passes through
    as a dimension filter (?geo=EU27_2020&time=2024; a dimension may repeat).
    Unfiltered big datasets are rejected upstream."""
    return await eurostat.dataset(dataset, list(request.query_params.multi_items()))


# ── ECB ──────────────────────────────────────────────────────────

@app.get("/ecb/{flow_ref}/{key}", tags=["ECB"], summary="SDMX series from an ECB dataflow")
async def ecb_series(flow_ref: str, key: str, start_period: str = "", end_period: str = ""):
    """One series, e.g. /ecb/EXR/D.USD.EUR.SP00.A (daily USD/EUR reference rate).
    Periods are YYYY-MM-DD (or YYYY / YYYY-MM per frequency)."""
    return await ecb.series(flow_ref, key, start_period, end_period)


# ── Comtrade ─────────────────────────────────────────────────────

@app.get("/comtrade", tags=["Comtrade"], summary="Global goods-trade flows (keyless preview, ≤500 records)")
async def comtrade_preview(reporter_code: str = Query("", alias="reporterCode", description="UN M49 numeric, e.g. 842=USA, 156=China"),
                           period: str = Query("", description="Year, e.g. 2023"),
                           partner_code: str = Query("", alias="partnerCode", description="UN M49 numeric; 0=World"),
                           cmd_code: str = Query("", alias="cmdCode", description="HS code or TOTAL"),
                           flow_code: str = Query("", alias="flowCode", description="M=imports, X=exports")):
    """Annual HS goods trade (public preview: ≤500 records, rate-limited, no key)."""
    return await comtrade.preview(reporter_code, period, partner_code, cmd_code, flow_code)


# ── UCDP ─────────────────────────────────────────────────────────

@app.get("/ucdp/gedevents", tags=["UCDP"], summary="Georeferenced conflict events (GED)")
async def ucdp_gedevents(country: str = Query("", description="Gleditsch-Ward numeric id(s), comma-separated (369=Ukraine, 365=Russia)"),
                         start_date: str = Query("", description="YYYY-MM-DD lower bound"),
                         end_date: str = Query("", description="YYYY-MM-DD upper bound"),
                         pagesize: int = Query(10, le=1000), page: int = Query(0, ge=0),
                         version: str = "24.1"):
    """Organized-violence events with locations, actors, and fatality estimates."""
    return await ucdp.gedevents(country, start_date, end_date, pagesize, page, version)


# ── USGS ─────────────────────────────────────────────────────────

@app.get("/usgs/earthquakes", tags=["USGS"], summary="Worldwide earthquake catalog (GeoJSON)")
async def usgs_earthquakes(starttime: str = Query("", description="YYYY-MM-DD (default: last 30 days)"),
                           endtime: str = Query("", description="YYYY-MM-DD"),
                           minmagnitude: float = Query(0.0, ge=0),
                           orderby: str = Query("time", pattern="^(time|time-asc|magnitude|magnitude-asc)$"),
                           limit: int = Query(10, le=1000)):
    """Earthquakes as GeoJSON features (magnitude, place, time, coordinates)."""
    return await usgs.earthquakes(starttime, endtime, minmagnitude, orderby, limit)


# ── NWS ──────────────────────────────────────────────────────────

@app.get("/nws/alerts", tags=["NWS"], summary="Active US weather alerts")
async def nws_alerts(area: str = Query("", description="Two-letter state/marine code, e.g. CA"),
                     severity: str = Query("", description="Extreme, Severe, Moderate, Minor, Unknown")):
    """Active alerts (GeoJSON features with headline, severity, areas)."""
    return await nws.alerts(area, severity)


# ── EONET ────────────────────────────────────────────────────────

@app.get("/eonet/events", tags=["EONET"], summary="Global natural events (wildfires, storms, volcanoes)")
async def eonet_events(category: str = Query("", description="e.g. wildfires, severeStorms, volcanoes — see /eonet/categories"),
                       status: str = Query("open", pattern="^(open|closed|all)$"),
                       limit: int = Query(10, le=1000), days: int = Query(0, ge=0)):
    """Natural events with geometry and source links. days=N limits to the last N days."""
    return await eonet.events(category, status, limit, days)


@app.get("/eonet/categories", tags=["EONET"], summary="EONET event categories")
async def eonet_categories():
    """All event categories with ids and descriptions."""
    return await eonet.categories()


# ── Wikipedia ────────────────────────────────────────────────────

@app.get("/wikipedia/summary/{title}", tags=["Wikipedia"], summary="Page summary (lead section)")
async def wikipedia_summary(title: str):
    """Lead-section summary. Use underscores in the title, e.g. Albert_Einstein."""
    return await wikipedia.summary(title)


@app.get("/wikipedia/search", tags=["Wikipedia"], summary="Full-text article search")
async def wikipedia_search(q: str, limit: int = Query(10, ge=1, le=50)):
    """Full-text search of English Wikipedia; hits under query.search."""
    return await wikipedia.search(q, limit)


@app.get("/wikipedia/pageviews/{title}", tags=["Wikipedia"], summary="Daily pageview counts for an article")
async def wikipedia_pageviews(title: str,
                              start: str = Query(..., description="YYYYMMDD"),
                              end: str = Query(..., description="YYYYMMDD")):
    """Daily pageviews (all access, all agents) between start and end, inclusive."""
    return await wikipedia.pageviews(title, start, end)


# ── NASA Image and Video Library ─────────────────────────────────

@app.get("/nasa/search", tags=["NASA Images"], summary="Search NASA's image/video/audio library (public domain)")
async def nasa_search(q: str, media_type: str = Query("video", pattern="^(video|image|audio)$"),
                      year_start: str = Query("", description="YYYY lower bound"),
                      year_end: str = Query("", description="YYYY upper bound"),
                      page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100)):
    """Search images.nasa.gov. Hits under collection.items[]; each item's
    data[0].nasa_id feeds /nasa/asset. All content is public domain (credit "NASA")."""
    return await nasa_images.search(q, media_type, year_start, year_end, page, page_size)


@app.get("/nasa/asset/{nasa_id}", tags=["NASA Images"], summary="Direct file URLs (incl. mp4 renditions) for one asset")
async def nasa_asset(nasa_id: str):
    """All downloadable renditions for a nasa_id — direct URLs under collection.items[].href."""
    return await nasa_images.asset(nasa_id)


# ── Internet Archive ─────────────────────────────────────────────

@app.get("/archive/search", tags=["Internet Archive"], summary="Search Internet Archive items (movies by default)")
async def archive_search(q: str, rows: int = Query(10, ge=1, le=50), page: int = Query(1, ge=1)):
    """Advanced search; hits under response.docs[] with identifier/title/year/licenseurl/mediatype.
    Free-text q is scoped to mediatype:movies unless q already sets mediatype:. Check licenseurl
    per item — public-domain collections (prelinger, newsreels) are the harvest target."""
    return await internetarchive.search(q, rows, page)


@app.get("/archive/item/{identifier}", tags=["Internet Archive"], summary="Item metadata + files with download paths")
async def archive_item(identifier: str):
    """Full item metadata incl. files[]; download a file as
    https://archive.org/download/{identifier}/{file.name}. License in metadata.licenseurl."""
    return await internetarchive.item(identifier)


# ── Wikimedia Commons ────────────────────────────────────────────

@app.get("/commons/search", tags=["Commons"], summary="Search Wikimedia Commons video files")
async def commons_search(q: str, limit: int = Query(10, ge=1, le=50)):
    """Video-file search; pages carry imageinfo[0].url (direct file URL) + extmetadata.
    License varies per file (CC-BY / CC-BY-SA / PD) — read extmetadata.LicenseShortName
    and Artist, and credit accordingly."""
    return await commons.search(q, limit)


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
