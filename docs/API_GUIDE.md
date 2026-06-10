# DataGod — API Guide

Find the right endpoint for the information you need, then call it.

- **Base URL:** `https://datagod.example.com`
- **Auth:** every call needs the header `X-API-Key: <your-key>` — only `GET /health` is public.
- **Response:** read the payload from the `data` field of the `{meta, data, error}` envelope.
- **Each entry below lists its parameters.** For full response schemas use `GET /openapi.json` (HTTP Basic: user `datagod`, password = your key) or the Swagger UI at `/docs`. `docs/endpoints.csv` has the same list, flat.
- **Limits:** a valid key has **no per-key usage or rate limit** on DataGod itself. Caveats: each endpoint's `limit` query param caps results **per call** (paginate for more), SEC EDGAR is throttled to ~10 req/sec (SEC's rule, shared across callers), and each upstream enforces its own rate limits (the DEMO_KEY-backed FEC / Congress / EIA / Smithsonian are low) — DataGod passes those through.


## Example call

```bash
curl -H "X-API-Key: $DATAGOD_API_KEY" "https://datagod.example.com/fred/GDP?limit=2"
```

Returns the standard envelope — read the payload from `data`:

```json
{
  "meta": { "source": "fred", "endpoint": "/fred/GDP", "timestamp": "2026-06-10T12:00:00Z", "status": "success" },
  "data": {
    "units": "lin",
    "observations": [
      { "date": "2026-01-01", "value": "31819.464" },
      { "date": "2025-10-01", "value": "31422.526" }
    ]
  },
  "error": null
}
```

No key (or a wrong one) returns `401`; an upstream failure returns `meta.status: "error"` with the message in `error` (HTTP 4xx passed through, 5xx/timeout → 502).


## Which source for which information

| You need... | Source | Start with |
|-------------|--------|------------|
| Economic indicators: GDP, inflation/CPI, interest rates, money supply | FRED | `GET /fred/{series_id}` (e.g. `GDP`, `CPIAUCSL`, `FEDFUNDS`) |
| Jobs, unemployment, wages, detailed CPI/PPI | BLS | `GET /bls/{series_id}` |
| US national debt, Treasury yields, exchange rates | Treasury | `GET /treasury/debt` |
| SEC filings & XBRL financials for a company | EDGAR | `GET /edgar/financials/{cik}` |
| One financial metric across ALL public companies | EDGAR | `GET /edgar/frames/{concept}` |
| Stock quote / price | Nasdaq | `GET /nasdaq/quote/{ticker}` |
| Deep stock fundamentals, options, holders, news | yfinance | `GET /yfinance/info/{ticker}` |
| Federal contracts, grants, who got paid | USAspending | `GET /usaspending/search` |
| Population, income, demographics (ACS) | Census | `GET /census/acs` |
| Campaign finance: candidates, contributions, totals | FEC | `GET /fec/candidates` |
| Legislation: bills, members, votes | Congress | `GET /congress/bills` |
| Drug adverse events, drug & food recalls | FDA | `GET /fda/drug-recalls` |
| Clinical trials | Clinical Trials | `GET /clinical-trials` |
| Energy prices, electricity, gasoline | EIA | `GET /eia/gas-prices` |
| Disaster declarations, FEMA grants, flood claims | FEMA | `GET /fema/disasters` |
| Federal rules, notices, executive orders | Federal Register | `GET /federal-register` |
| US House members' stock trades | House Disclosures | `GET /house-disclosures/members` |
| Federal judges' financial disclosures | JEFS | `GET /jefs/search` (needs session) |
| US National Archives catalog records | NARA | `GET /nara/search` |
| Declassified national-security documents | NSArchive / Wilson Center | `GET /nsarchive/search`, `GET /wilson/documents` |
| Museum / library / archive objects | Smithsonian | `GET /smithsonian/search` |
| One company or politician across several sources | Cross-Reference | `GET /cross-reference/company/{name}` |


## All endpoints by source

### Health

_Liveness probe. `GET /health` is public (no key required)._

- **`GET /`** — Service index: lists every data source and its endpoint groups. Use to discover what is available.
  - _params:_ none
- **`GET /health`** — Health / liveness check. Public, no key. Use for uptime monitoring and readiness probes.
  - _params:_ none

### FRED

_Federal Reserve Economic Data — 800K+ economic time series._

- **`GET /fred`** — Keyword search across FRED's 800K-series catalog; returns series IDs to fetch above. Use when you don't know the exact series ID.
  - _params:_ `q` (query, string) · `limit` (query, integer, default 10, max 100)
- **`GET /fred/{series_id}`** — One US macroeconomic time series by FRED series ID. Use for: GDP, inflation, consumer prices/CPI (CPIAUCSL), unemployment rate (UNRATE), Fed funds / interest rates (FEDFUNDS), Treasury yields (DGS10), money supply (M2), S&P 500 (SP500), industrial production, recession indicators — any US macro indicator.
  - _params:_ `series_id` (path, string, required) · `limit` (query, integer, default 10, max 1000)

### EDGAR

_SEC EDGAR — corporate filings, XBRL financials, full-text search. The Frames endpoint compares one concept across all filers in a single call._

- **`GET /edgar/company/{cik}`** — SEC company profile and filing history (10-K, 10-Q, 8-K, S-1, etc.) by CIK or ticker (e.g. AAPL). Use for: company metadata, recent filings, fiscal year end, SIC industry, exchange, addresses, former names.
  - _params:_ `cik` (path, string, required)
- **`GET /edgar/concept/{cik}/{concept}`** — History of one XBRL concept for one company (e.g. Revenues, NetIncomeLoss, Assets, CashAndCashEquivalents). Use to track a single financial metric over time.
  - _params:_ `cik` (path, string, required) · `concept` (path, string, required) · `taxonomy` (query, string, default us-gaap)
- **`GET /edgar/financials/{cik}`** — All XBRL financial facts for a company across years. Use for: revenue, net income, assets, liabilities, cash, equity, EPS, R&D spend — the full financial-statement dataset.
  - _params:_ `cik` (path, string, required)
- **`GET /edgar/frames/{concept}`** — One financial concept across ALL public companies for a period — cross-company comparison in a single call. Use to rank or compare revenue / assets / net income across thousands of filers.
  - _params:_ `concept` (path, string, required) · `unit` (query, string, default USD) · `period` (query, string, default CY2023) · `taxonomy` (query, string, default us-gaap)
- **`GET /edgar/search`** — Full-text search inside SEC filing documents. Use for: which companies mention a topic (AI, climate risk, layoffs, a competitor, a product) in their filings; filter by form type.
  - _params:_ `q` (query, string, required) · `forms` (query, string) · `limit` (query, integer, default 10, max 100)

### Nasdaq

_Nasdaq.com (unofficial) — quote, price, history, dividends._

- **`GET /nasdaq/dividends/{ticker}`** — Dividend payment history (ex-date and amount) for a ticker.
  - _params:_ `ticker` (path, string, required) · `asset_class` (query, string, default stocks)
- **`GET /nasdaq/history/{ticker}`** — Daily OHLCV price history (open, high, low, close, volume) between two dates.
  - _params:_ `ticker` (path, string, required) · `fromdate` (query, string, required) · `todate` (query, string, required) · `limit` (query, integer, default 30, max 260) · `asset_class` (query, string, default stocks)
- **`GET /nasdaq/price/{ticker}`** — Current price, bid/ask, day volume, and percent change for a ticker.
  - _params:_ `ticker` (path, string, required) · `asset_class` (query, string, default stocks)
- **`GET /nasdaq/quote/{ticker}`** — Stock quote summary: market cap, sector, industry, P/E, dividend yield, 52-week high/low. Quick snapshot of a listed company.
  - _params:_ `ticker` (path, string, required) · `asset_class` (query, string, default stocks)

### yfinance

_Yahoo Finance via the yfinance library — fundamentals, news, options, holders._

- **`GET /yfinance/dividends/{ticker}`** — Dividend payment history (amounts and dates).
  - _params:_ `ticker` (path, string, required)
- **`GET /yfinance/financials/{ticker}`** — Income statement, balance sheet, and cash-flow statement (annual + quarterly).
  - _params:_ `ticker` (path, string, required)
- **`GET /yfinance/history/{ticker}`** — OHLCV price history with flexible period (1d..max) and interval (1m..1mo). Use for charts, returns, volatility.
  - _params:_ `ticker` (path, string, required) · `period` (query, string, default 1mo) · `interval` (query, string, default 1d)
- **`GET /yfinance/holders/{ticker}`** — Ownership: major holders, institutional holders, and mutual-fund holders.
  - _params:_ `ticker` (path, string, required)
- **`GET /yfinance/info/{ticker}`** — Deepest single-call company profile (~140 fields): market cap, P/E, EPS, beta, profit margins, ROE, debt, free cash flow, analyst price targets, sector, employees, business summary.
  - _params:_ `ticker` (path, string, required)
- **`GET /yfinance/news/{ticker}`** — Recent news headlines and article links tied to a ticker.
  - _params:_ `ticker` (path, string, required)
- **`GET /yfinance/options/{ticker}`** — Options chain: expiry dates, calls and puts, strikes, implied volatility, open interest.
  - _params:_ `ticker` (path, string, required) · `expiry` (query, string)
- **`GET /yfinance/recommendations/{ticker}`** — Analyst recommendation history (buy / hold / sell ratings over time).
  - _params:_ `ticker` (path, string, required)

### USAspending

_USAspending.gov — federal contracts and grants ($6T+/yr)._

- **`GET /usaspending/agencies`** — List of federal agencies (names and IDs) for filtering spending queries.
  - _params:_ none
- **`GET /usaspending/by-agency`** — Federal spending totals grouped by agency for a fiscal year / quarter.
  - _params:_ `fy` (query, string, default 2025) · `quarter` (query, string, default 1)
- **`GET /usaspending/search`** — Search federal awards (contracts and grants) by keyword. Use for: who received federal money, contractors/recipients, award amounts, defense or agency spending.
  - _params:_ `q` (query, string, required) · `start_date` (query, string) · `end_date` (query, string) · `limit` (query, integer, default 10, max 100)

### Census

_US Census Bureau — population, income, and raw ACS queries._

- **`GET /census/acs`** — Raw American Community Survey query — any ACS variables and geography (state / county / tract). Use for: demographics, race, age, sex, education, income, poverty, housing, commute — any ACS table by variable code.
  - _params:_ `variables` (query, string, default NAME,B01001_001E) · `year` (query, integer, default 2022) · `geo_for` (query, string, default state:*) · `geo_in` (query, string)
- **`GET /census/income`** — Median household income by US state.
  - _params:_ `year` (query, integer, default 2022)
- **`GET /census/population`** — Population by US state.
  - _params:_ `year` (query, integer, default 2022)

### BLS

_Bureau of Labor Statistics — employment, wages, CPI._

- **`GET /bls/{series_id}`** — US labor statistics series by ID. Use for: unemployment rate, nonfarm payroll employment, CPI inflation, PPI, average hourly earnings. Shortcut IDs: unemployment, cpi, nonfarm_employment, ppi, hourly_earnings.
  - _params:_ `series_id` (path, string, required) · `start_year` (query, integer, default 2024) · `end_year` (query, integer, default 2026)

### Treasury

_Treasury Fiscal Data — debt, interest rates, exchange rates._

- **`GET /treasury/debt`** — US national / public debt (debt to the penny): total outstanding, debt held by the public, intragovernmental holdings, by date.
  - _params:_ `limit` (query, integer, default 5, max 100)
- **`GET /treasury/exchange`** — US Treasury reporting exchange rates (foreign-currency conversion rates used by the government).
  - _params:_ `limit` (query, integer, default 5, max 100)
- **`GET /treasury/rates`** — Average interest rates on outstanding US Treasury securities.
  - _params:_ `limit` (query, integer, default 5, max 100)

### FEC

_Federal Election Commission — candidates, contributions, totals._

- **`GET /fec/candidates`** — Search federal candidates (President, Senate, House) by office and state. Campaign finance.
  - _params:_ `office` (query, string) · `state` (query, string) · `limit` (query, integer, default 10, max 100)
- **`GET /fec/contributions`** — Campaign contributions — itemized donations by or for a candidate or donor name.
  - _params:_ `name` (query, string) · `candidate_id` (query, string) · `limit` (query, integer, default 10, max 100)
- **`GET /fec/totals`** — Candidate financial totals (money raised / receipts), ranked, by office and election year.
  - _params:_ `office` (query, string, default P) · `year` (query, integer, default 2024) · `limit` (query, integer, default 10, max 100)

### Congress

_Congress.gov — bills, members, votes._

- **`GET /congress/bill/{congress_num}/{bill_type}/{number}`** — Full detail for one bill: sponsors, actions, latest status, summary.
  - _params:_ `congress_num` (path, integer, required) · `bill_type` (path, string, required) · `number` (path, integer, required)
- **`GET /congress/bills`** — Recent bills introduced in Congress. Legislation tracking.
  - _params:_ `limit` (query, integer, default 10, max 250) · `congress_num` (query, integer, default 0)
- **`GET /congress/members`** — Members of Congress (representatives and senators), with party and state.
  - _params:_ `limit` (query, integer, default 10, max 250)
- **`GET /congress/votes`** — Roll-call votes by chamber and session.
  - _params:_ `chamber` (query, string, default house) · `congress_session` (query, integer, default 118) · `limit` (query, integer, default 10, max 250)

### FDA

_openFDA — drug adverse events, drug recalls, food recalls._

- **`GET /fda/drug-events`** — Drug adverse-event reports (side effects, reactions) from openFDA / FAERS.
  - _params:_ `search` (query, string) · `limit` (query, integer, default 10, max 100)
- **`GET /fda/drug-recalls`** — Drug recall enforcement reports — recalled medications, reasons, recall class.
  - _params:_ `search` (query, string) · `limit` (query, integer, default 10, max 100)
- **`GET /fda/food-recalls`** — Food recall enforcement reports — recalled foods, contamination, allergens, reasons.
  - _params:_ `search` (query, string) · `limit` (query, integer, default 10, max 100)

### Clinical Trials

_ClinicalTrials.gov — 500K+ registered trials._

- **`GET /clinical-trials`** — Search ClinicalTrials.gov by condition, intervention, and status (recruiting, completed). Medical and drug trials.
  - _params:_ `condition` (query, string) · `intervention` (query, string) · `status` (query, string) · `limit` (query, integer, default 10, max 100)
- **`GET /clinical-trials/{nct_id}`** — Full record for one clinical trial by its NCT ID.
  - _params:_ `nct_id` (path, string, required)

### EIA

_Energy Information Administration — gas prices, electricity, and generic dataset queries._

- **`GET /eia`** — List the EIA energy datasets available to query.
  - _params:_ none
- **`GET /eia/electricity`** — Electricity data: generation, retail sales, and prices.
  - _params:_ `limit` (query, integer, default 10, max 100)
- **`GET /eia/gas-prices`** — Gasoline and fuel prices over time.
  - _params:_ `limit` (query, integer, default 10, max 100)
- **`GET /eia/{route}`** — Generic EIA dataset query by route path — any energy series (crude oil, natural gas, coal, renewables, CO2 emissions, consumption).
  - _params:_ `route` (path, string, required) · `frequency` (query, string, default annual) · `data` (query, string, default value) · `limit` (query, integer, default 10, max 1000)

### FEMA

_OpenFEMA — disaster declarations, grants, flood claims._

- **`GET /fema/disasters`** — Federal disaster declarations (hurricanes, floods, wildfires, severe storms) by date and state.
  - _params:_ `limit` (query, integer, default 10, max 1000)
- **`GET /fema/flood-claims`** — NFIP (National Flood Insurance Program) flood insurance claims data.
  - _params:_ `limit` (query, integer, default 10, max 1000)
- **`GET /fema/grants`** — FEMA grant and assistance awards.
  - _params:_ `limit` (query, integer, default 10, max 1000)

### Federal Register

_Federal Register — rules, notices, executive orders._

- **`GET /federal-register`** — Search the Federal Register: proposed and final rules, notices, executive orders, and presidential documents; filter by type and agency.
  - _params:_ `term` (query, string) · `doc_type` (query, string) · `agency` (query, string) · `limit` (query, integer, default 10, max 100)
- **`GET /federal-register/{doc_number}`** — One Federal Register document by its document number.
  - _params:_ `doc_number` (path, string, required)

### JEFS

_Judicial Financial Disclosures — session-based; needs Playwright registration + reCAPTCHA first._

- **`GET /jefs/facets`** — Available JEFS filters (years, courts, positions, report types). Requires an active session.
  - _params:_ none
- **`POST /jefs/register`** — Open a JEFS session for judicial financial disclosures — drives a Playwright browser through registration + reCAPTCHA. Requires a real name, occupation, and address.
  - _params:_ `name` (query, string, required) · `occupation` (query, string, required) · `address` (query, string, required) · `headed` (query, boolean, default True)
- **`POST /jefs/reset`** — Clear the JEFS session; you must re-register before the next call.
  - _params:_ none
- **`GET /jefs/search`** — Search federal judges' financial disclosure reports. Requires an active session (call /jefs/register first).
  - _params:_ `q` (query, string) · `year` (query, string) · `court_type` (query, string) · `start` (query, integer, default 0)

### House Disclosures

_US House financial disclosures (member/candidate stock trades)._

- **`GET /house-disclosures/candidates`** — US House candidates' financial disclosures.
  - _params:_ `last_name` (query, string) · `year` (query, string) · `state` (query, string) · `district` (query, string)
- **`GET /house-disclosures/members`** — US House members' financial disclosures — congressional stock trades and holdings.
  - _params:_ `last_name` (query, string) · `year` (query, string) · `state` (query, string) · `district` (query, string)

### NARA

_US National Archives Catalog — all record groups plus the 14 presidential libraries._

- **`GET /nara/record/{na_id}`** — One National Archives catalog record by its National Archives Identifier (NAID).
  - _params:_ `na_id` (path, string, required)
- **`GET /nara/search`** — Search the US National Archives Catalog — historical government records across all record groups and the 14 presidential libraries.
  - _params:_ `q` (query, string) · `page` (query, integer, default 1)

### NSArchive

_National Security Archive (GWU NGO, not NARA) — Virtual Reading Room declassified docs (HTML scrape)._

- **`GET /nsarchive/document/{doc_id}`** — One declassified Virtual Reading Room document by its id-slug.
  - _params:_ `doc_id` (path, string, required)
- **`GET /nsarchive/search`** — Search the National Security Archive (GWU NGO) Virtual Reading Room — declassified documents on foreign policy, intelligence, and defense.
  - _params:_ `q` (query, string) · `page` (query, integer, default 1)

### Smithsonian

_Smithsonian Open Access (EDAN) — 11M+ museum/library/archive records._

- **`GET /smithsonian/category/{category}/search`** — Search within a Smithsonian category: art_design, history_culture, or science_technology.
  - _params:_ `category` (path, string, required) · `q` (query, string) · `start` (query, integer, default 0) · `rows` (query, integer, default 10, max 100)
- **`GET /smithsonian/object/{object_id}`** — Full metadata record for one Smithsonian object by EDAN id.
  - _params:_ `object_id` (path, string, required)
- **`GET /smithsonian/search`** — Search Smithsonian Open Access — 11M+ museum, library, and archive objects (art, history, science specimens, photographs).
  - _params:_ `q` (query, string) · `start` (query, integer, default 0) · `rows` (query, integer, default 10, max 100) · `sort` (query, string) · `obj_type` (query, string)
- **`GET /smithsonian/stats`** — Smithsonian Open Access dataset statistics (counts by unit, type, etc.).
  - _params:_ none
- **`GET /smithsonian/terms/{category}`** — Controlled-vocabulary terms for a facet: culture, topic, place, object_type, data_source, date, or name.
  - _params:_ `category` (path, string, required)

### Wilson Center

_Wilson Center Digital Archive — local mirror of 16,756 declassified documents._

- **`GET /wilson/document/{slug}`** — One Wilson Center document by slug: title, source, subjects, download availability.
  - _params:_ `slug` (path, string, required)
- **`GET /wilson/documents`** — Full-text search the Wilson Center Digital Archive (local mirror) — 16,756 declassified Cold War and international-history documents.
  - _params:_ `q` (query, string) · `page` (query, integer, default 1) · `items_per_page` (query, integer, default 10, max 100)

### Cross-Reference

_Aggregators that join several sources for one company or politician._

- **`GET /cross-reference/company/{name}`** — Aggregate a company across EDGAR + USAspending + FEC in one call: SEC filings + federal contracts + political contributions.
  - _params:_ `name` (path, string, required)
- **`GET /cross-reference/politician/{last_name}`** — Aggregate a politician across House disclosures + FEC: stock trades + campaign finance.
  - _params:_ `last_name` (path, string, required) · `first_name` (query, string)

### Admin

_Operational endpoints (cache management)._

- **`POST /admin/clear-cache`** — Clear the in-memory cache (operational endpoint).
  - _params:_ none
