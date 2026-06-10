# DataGod — API Guide

Pick the right endpoint for the information you need.

- **Base URL:** `https://datagod.example.com`
- **Auth:** every call needs the header `X-API-Key: <your-key>` — only `GET /health` is public.
- **Response:** read the payload from the `data` field of the `{meta, data, error}` envelope.
- **Full parameters & schemas:** `GET /openapi.json` (HTTP Basic: user `datagod`, password = your key) or the Swagger UI at `/docs`. A flat machine-readable list is in `docs/endpoints.csv`.


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

- `GET /` — API index: sources and endpoint map
- `GET /health` — Liveness probe (public, no API key)

### FRED

_Federal Reserve Economic Data — 800K+ economic time series._

- `GET /fred` — Search FRED series by keyword
- `GET /fred/{series_id}` — Fetch a FRED economic time series

### EDGAR

_SEC EDGAR — corporate filings, XBRL financials, full-text search. The Frames endpoint compares one concept across all filers in a single call._

- `GET /edgar/company/{cik}` — Company profile and filing history (CIK or ticker)
- `GET /edgar/concept/{cik}/{concept}` — One XBRL concept's history for a company
- `GET /edgar/financials/{cik}` — All XBRL financial facts for a company
- `GET /edgar/frames/{concept}` — One concept across all filers (cross-company)
- `GET /edgar/search` — Full-text search inside filing documents

### Nasdaq

_Nasdaq.com (unofficial) — quote, price, history, dividends._

- `GET /nasdaq/dividends/{ticker}` — Dividend history
- `GET /nasdaq/history/{ticker}` — Daily OHLCV between two dates
- `GET /nasdaq/price/{ticker}` — Real-time price, bid/ask, volume, change
- `GET /nasdaq/quote/{ticker}` — Quote summary: market cap, sector, P/E, 52-week

### yfinance

_Yahoo Finance via the yfinance library — fundamentals, news, options, holders._

- `GET /yfinance/dividends/{ticker}` — Dividend payment history
- `GET /yfinance/financials/{ticker}` — Income statement, balance sheet, cash flow
- `GET /yfinance/history/{ticker}` — OHLCV price history
- `GET /yfinance/holders/{ticker}` — Major, institutional, and fund holders
- `GET /yfinance/info/{ticker}` — Full ticker fundamentals (~140 fields)
- `GET /yfinance/news/{ticker}` — Recent news headlines
- `GET /yfinance/options/{ticker}` — Options chain (expiries or calls/puts)
- `GET /yfinance/recommendations/{ticker}` — Analyst recommendation history

### USAspending

_USAspending.gov — federal contracts and grants ($6T+/yr)._

- `GET /usaspending/agencies` — List federal agencies
- `GET /usaspending/by-agency` — Spending totals by agency (fiscal year)
- `GET /usaspending/search` — Search federal awards by keyword

### Census

_US Census Bureau — population, income, and raw ACS queries._

- `GET /census/acs` — Raw ACS query (any variables and geography)
- `GET /census/income` — Median household income by state
- `GET /census/population` — Population by state

### BLS

_Bureau of Labor Statistics — employment, wages, CPI._

- `GET /bls/{series_id}` — BLS series (CPI, unemployment, wages, PPI)

### Treasury

_Treasury Fiscal Data — debt, interest rates, exchange rates._

- `GET /treasury/debt` — US public debt (debt to the penny)
- `GET /treasury/exchange` — Treasury exchange rates
- `GET /treasury/rates` — Average interest rates on US debt

### FEC

_Federal Election Commission — candidates, contributions, totals._

- `GET /fec/candidates` — Search federal candidates
- `GET /fec/contributions` — Campaign contributions
- `GET /fec/totals` — Candidate financial totals by receipts

### Congress

_Congress.gov — bills, members, votes._

- `GET /congress/bill/{congress_num}/{bill_type}/{number}` — Single bill detail
- `GET /congress/bills` — Recent bills
- `GET /congress/members` — Members of Congress
- `GET /congress/votes` — Roll-call votes by chamber

### FDA

_openFDA — drug adverse events, drug recalls, food recalls._

- `GET /fda/drug-events` — Drug adverse-event reports
- `GET /fda/drug-recalls` — Drug recall enforcement reports
- `GET /fda/food-recalls` — Food recall enforcement reports

### Clinical Trials

_ClinicalTrials.gov — 500K+ registered trials._

- `GET /clinical-trials` — Search ClinicalTrials.gov
- `GET /clinical-trials/{nct_id}` — Single trial by NCT ID

### EIA

_Energy Information Administration — gas prices, electricity, and generic dataset queries._

- `GET /eia` — List available EIA datasets
- `GET /eia/electricity` — Electricity generation and retail data
- `GET /eia/gas-prices` — Gasoline prices
- `GET /eia/{route}` — Generic EIA dataset query by route

### FEMA

_OpenFEMA — disaster declarations, grants, flood claims._

- `GET /fema/disasters` — Disaster declarations
- `GET /fema/flood-claims` — NFIP flood insurance claims
- `GET /fema/grants` — FEMA grant awards

### Federal Register

_Federal Register — rules, notices, executive orders._

- `GET /federal-register` — Search the Federal Register
- `GET /federal-register/{doc_number}` — Single Federal Register document

### JEFS

_Judicial Financial Disclosures — session-based; needs Playwright registration + reCAPTCHA first._

- `GET /jefs/facets` — JEFS filter facets (needs session)
- `POST /jefs/register` — Open a JEFS session (Playwright + reCAPTCHA)
- `POST /jefs/reset` — Clear the JEFS session
- `GET /jefs/search` — Search judicial disclosures (needs session)

### House Disclosures

_US House financial disclosures (member/candidate stock trades)._

- `GET /house-disclosures/candidates` — House candidate financial disclosures
- `GET /house-disclosures/members` — House member financial disclosures

### NARA

_US National Archives Catalog — all record groups plus the 14 presidential libraries._

- `GET /nara/record/{na_id}` — Single catalog record by NAID
- `GET /nara/search` — Search the National Archives Catalog

### NSArchive

_National Security Archive (GWU NGO, not NARA) — Virtual Reading Room declassified docs (HTML scrape)._

- `GET /nsarchive/document/{doc_id}` — Single VRR document by id-slug
- `GET /nsarchive/search` — Search the National Security Archive VRR

### Smithsonian

_Smithsonian Open Access (EDAN) — 11M+ museum/library/archive records._

- `GET /smithsonian/category/{category}/search` — Search within a Smithsonian category
- `GET /smithsonian/object/{object_id}` — Full object record by EDAN id
- `GET /smithsonian/search` — Search Smithsonian Open Access
- `GET /smithsonian/stats` — Open Access dataset statistics
- `GET /smithsonian/terms/{category}` — Controlled-vocabulary terms

### Wilson Center

_Wilson Center Digital Archive — local mirror of 16,756 declassified documents._

- `GET /wilson/document/{slug}` — Single Wilson document by slug
- `GET /wilson/documents` — Search the Wilson Center mirror

### Cross-Reference

_Aggregators that join several sources for one company or politician._

- `GET /cross-reference/company/{name}` — Company across EDGAR + USAspending + FEC
- `GET /cross-reference/politician/{last_name}` — Politician across House disclosures + FEC

### Admin

_Operational endpoints (cache management)._

- `POST /admin/clear-cache` — Clear the in-memory cache
