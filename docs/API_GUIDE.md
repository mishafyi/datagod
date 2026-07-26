# DataGod — API Guide

Find the right endpoint for the information you need, then call it.

- **Base URL:** your DataGod deployment's origin — the examples below use `$DATAGOD_URL`.
- **Auth:** every call needs the header `X-API-Key: <your-key>` — only `GET /health` is public. The key is whatever the deployment's `.env` sets as `DATAGOD_API_KEY`.
- **Response:** read the payload from the `data` field of the `{meta, data, error}` envelope.
- **Drill down:** each source below has a rich description, its endpoint paths, and a link to its detail doc. Per-endpoint **parameters** live in `docs/endpoints.csv` (flat, greppable); full response **schemas** via `GET /openapi.json` (HTTP Basic: user `datagod`, password = your key) or `/docs`.
- **Limits:** a valid key has **no per-key usage or rate limit** on DataGod itself. Caveats: each endpoint's `limit` query param caps results **per call** (paginate for more), SEC EDGAR is throttled to ~10 req/sec (SEC's rule, shared across callers), and each upstream enforces its own rate limits (the DEMO_KEY-backed FEC / Congress / EIA / Smithsonian are low) — DataGod passes those through.


## Example call

```bash
curl -H "X-API-Key: $DATAGOD_API_KEY" "$DATAGOD_URL/fred/GDP?limit=2"
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
| US National Archives catalog records | NARA | `GET /nara/search` |
| Declassified national-security documents | NSArchive | `GET /nsarchive/search` |
| Museum / library / archive objects | Smithsonian | `GET /smithsonian/search` |
| Scientific preprints / research papers | arXiv | `GET /arxiv/search` |
| Academic papers ranked by citations | Scholar | `GET /scholar/search` (brittle — Google blocks) |
| One company or politician across several sources | Cross-Reference | `GET /cross-reference/company/{name}` |


## Sources

A keyword-rich description per source, so you can tell at a glance whether a source has what you need. Endpoint **parameters** are in `docs/endpoints.csv` (flat, greppable); **deep detail and quirks** are in each source's linked doc. Load only the source(s) you need.

### Health

Service utility: API index (`/`) and a public liveness probe (`/health`). Not a data source.

- **Endpoints:** `/` · `/health`
- **params:** `docs/endpoints.csv`

### FRED

US economy and macroeconomic time series (800K+) — GDP, inflation and consumer prices (CPI, PCE), unemployment rate, interest rates (Fed funds, Treasury yields, 10-year), money supply (M1/M2), exchange rates, housing, industrial production, S&P 500, recession indicators. The default for any national economic indicator over time.

- **Endpoints:** `/fred` · `/fred/series/{series_id}` · `/fred/{series_id}`
- **Detail:** `docs/FRED.md` · **params:** `docs/endpoints.csv`

### EDGAR

SEC filings and financials for public companies and corporations — 10-K, 10-Q, 8-K annual and quarterly reports, full XBRL financial statements (revenue, earnings, net income, assets, liabilities, EPS, cash flow), one-metric-across-all-companies comparisons, and full-text search inside filings (by CIK or ticker). Use for any public-company financial data, SEC disclosures, or 'which companies mention X'.

- **Endpoints:** `/edgar/cik/{ticker}` · `/edgar/company/{cik}` · `/edgar/concept/{cik}/{concept}` · `/edgar/document/{cik}/{accession}/{document}` · `/edgar/financials/{cik}` · `/edgar/frames/{concept}` · `/edgar/search` · `/edgar/submissions/{filename}`
- **Detail:** `docs/EDGAR_API.md` · **params:** `docs/endpoints.csv`

### Nasdaq

Stock-market quotes for stocks, shares, and equities (Nasdaq.com, unofficial) — price, quote, bid/ask, volume, market cap, sector, industry, P/E, 52-week range, dividends, and daily OHLCV price history by ticker/symbol. Use for a quick quote or price snapshot of a listed ticker.

- **Endpoints:** `/nasdaq/calendar/earnings` · `/nasdaq/calendar/ipo` · `/nasdaq/dividends/{ticker}` · `/nasdaq/earnings-surprise/{ticker}` · `/nasdaq/financials/{ticker}` · `/nasdaq/history/{ticker}` · `/nasdaq/insider-trades/{ticker}` · `/nasdaq/price/{ticker}` · `/nasdaq/quote/{ticker}` · `/nasdaq/screener`
- **Detail:** `docs/NASDAQ_API.md` · **params:** `docs/endpoints.csv`

### yfinance

Deep data for stocks, shares, and equities (Yahoo Finance) by ticker/symbol — ~140 fundamental fields (market cap, P/E, EPS, beta, margins, ROE), full financial statements (income statement, balance sheet, cash flow), options chains (calls, puts, implied volatility), institutional and fund holders/ownership, analyst recommendations and price targets, dividends, earnings, news, and OHLCV price history. Use for thorough single-ticker stock analysis beyond a basic quote.

- **Endpoints:** `/yfinance/dividends/{ticker}` · `/yfinance/earnings/{ticker}` · `/yfinance/financials/{ticker}` · `/yfinance/history/{ticker}` · `/yfinance/holders/{ticker}` · `/yfinance/info/{ticker}` · `/yfinance/news/{ticker}` · `/yfinance/options/{ticker}` · `/yfinance/recommendations/{ticker}`
- **Detail:** `docs/YFINANCE_API.md` · **params:** `docs/endpoints.csv`

### USAspending

US federal spending ($6T+/yr) — government contracts, grants, and awards; recipients, contractors, and vendors; award amounts; agency and defense spending totals; subawards. Use for who received federal money, federal contracts, or grant awards.

- **Endpoints:** `/usaspending/agencies` · `/usaspending/by-agency` · `/usaspending/search`
- **Detail:** `docs/USASPENDING.md` · **params:** `docs/endpoints.csv`

### Census

US demographics from the Census Bureau / American Community Survey (ACS) — population, median household income, race and ethnicity, age, sex, education, poverty, housing and rent, commute, employment — by state, county, or census tract. Use for any US demographic or socioeconomic statistic.

- **Endpoints:** `/census/acs` · `/census/income` · `/census/population`
- **Detail:** `docs/CENSUS.md` · **params:** `docs/endpoints.csv`

### BLS

US labor statistics and jobs data (Bureau of Labor Statistics) — unemployment rate, employment and nonfarm payrolls, wages and average hourly earnings, job openings, CPI inflation and consumer prices, PPI producer prices, productivity, by series. Use for the labor market, jobs, or price indexes.

- **Endpoints:** `/bls/batch` · `/bls/{series_id}`
- **Detail:** `docs/BLS.md` · **params:** `docs/endpoints.csv`

### Treasury

US federal fiscal data (Treasury) — the national / public debt (debt to the penny, debt held by the public, intragovernmental), federal deficit context, average interest rates and yields on Treasury securities, and government exchange rates. Use for the size of the national debt or US borrowing costs.

- **Endpoints:** `/treasury/debt` · `/treasury/exchange` · `/treasury/rates`
- **Detail:** `docs/TREASURY.md` · **params:** `docs/endpoints.csv`

### FEC

Federal campaign finance and elections (FEC) — candidates (presidential, Senate, House), itemized contributions and donors, PAC and super PAC money, and candidate fundraising totals (receipts, disbursements). Use for election money: who is running, who donated, how much was raised or spent.

- **Endpoints:** `/fec/candidates` · `/fec/contributions` · `/fec/totals`
- **Detail:** `docs/FEC.md` · **params:** `docs/endpoints.csv`

### Congress

US legislation and Congress (Congress.gov) — bills and laws with status, sponsors and cosponsors, and actions; members of Congress (representatives, senators); committees; and roll-call votes. Use for tracking laws, what Congress is doing, or how members voted.

- **Endpoints:** `/congress/bill/{congress_num}/{bill_type}/{number}` · `/congress/bills` · `/congress/members` · `/congress/votes`
- **Detail:** `docs/CONGRESS.md` · **params:** `docs/endpoints.csv`

### FDA

Drug and food safety (openFDA) — drug adverse-event and side-effect reports (FAERS), drug recalls, and food recalls (contamination, allergens), for medications and pharmaceuticals. Use for medication safety, adverse reactions, or recalled products.

- **Endpoints:** `/fda/drug-events` · `/fda/drug-recalls` · `/fda/food-recalls`
- **Detail:** `docs/FDA.md` · **params:** `docs/endpoints.csv`

### Clinical Trials

Clinical and medical trials (ClinicalTrials.gov, 500K+ studies) — searchable by condition or disease, intervention / drug or treatment, and status (recruiting, completed), by NCT id. Use for clinical or drug trials on a disease or treatment.

- **Endpoints:** `/clinical-trials` · `/clinical-trials/{nct_id}`
- **Detail:** `docs/CLINICAL_TRIALS.md` · **params:** `docs/endpoints.csv`

### EIA

US energy data (Energy Information Administration) — gasoline and fuel prices, crude oil and petroleum, natural gas, electricity (generation, sales, prices), coal, renewables (solar, wind), CO2 emissions, and energy consumption. Use for energy prices or production.

- **Endpoints:** `/eia` · `/eia/electricity` · `/eia/gas-prices` · `/eia/{route}`
- **Detail:** `docs/EIA.md` · **params:** `docs/endpoints.csv`

### FEMA

Disasters and emergency management (OpenFEMA) — federal disaster declarations (hurricanes, floods, wildfires / fires, storms, earthquakes, emergencies), FEMA grants and assistance, and NFIP flood-insurance claims. Use for disaster events or federal disaster aid.

- **Endpoints:** `/fema/disasters` · `/fema/flood-claims` · `/fema/grants`
- **Detail:** `docs/FEMA.md` · **params:** `docs/endpoints.csv`

### Federal Register

US federal regulations (Federal Register) — proposed and final rules and rulemaking, agency notices, executive orders, and presidential documents, by type and agency. Use for regulations, rules, or executive orders.

- **Endpoints:** `/federal-register` · `/federal-register/{doc_number}`
- **Detail:** `docs/FEDERAL_REGISTER.md` · **params:** `docs/endpoints.csv`

### House Disclosures

US House financial disclosures and congressional stock trades — representatives' and candidates' stock trades, holdings, and periodic transaction reports (PTRs). Use for politicians' or members of Congress' stock transactions in the House.

- **Endpoints:** `/house-disclosures/candidates` · `/house-disclosures/members` · `/house-disclosures/pdf`
- **Detail:** `docs/HOUSE_FD_API.md` · **params:** `docs/endpoints.csv`

### NARA

US National Archives catalog — historical federal and government records, primary sources, and declassified documents across all record groups and the 14 presidential libraries. Use for archival US government documents, historical records, or presidential materials.

- **Endpoints:** `/nara/record/{na_id}` · `/nara/search`
- **Detail:** `docs/NARA_API.md` · **params:** `docs/endpoints.csv`

### NSArchive

Declassified national-security documents (National Security Archive — a GWU NGO, not NARA) — foreign policy, intelligence (CIA), military, and Cold War cables, memos, and FOIA releases. Use for declassified Cold War or foreign-policy documents.

- **Endpoints:** `/nsarchive/document/{doc_id}` · `/nsarchive/search`
- **Detail:** `docs/NSARCHIVE_API.md` · **params:** `docs/endpoints.csv`

### Smithsonian

Museum and archive collections (Smithsonian Open Access, 11M+ objects) — art and artwork, artifacts, history, science specimens, and photographs / images with metadata and category / term browsing. Use for museum objects, cultural heritage, or collection metadata.

- **Endpoints:** `/smithsonian/category/{category}/search` · `/smithsonian/object/{object_id}` · `/smithsonian/search` · `/smithsonian/stats` · `/smithsonian/terms/{category}`
- **Detail:** `docs/SMITHSONIAN_API.md` · **params:** `docs/endpoints.csv`

### arXiv

Scientific preprints from arXiv.org — full-text search of 2M+ open-access papers in physics, math, computer science, machine learning and AI, quantitative biology, economics, and statistics; by topic, author, title, or arXiv id, with abstracts, authors, categories, and PDF links. Use for academic papers, research preprints, or scientific literature.

- **Endpoints:** `/arxiv/search` · `/arxiv/{arxiv_id}`
- **Detail:** `docs/ARXIV_API.md` · **params:** `docs/endpoints.csv`

### Scholar

Academic papers ranked by citations from Google Scholar (via the vendored sort-google-scholar). Search scholarly literature across all publishers and journals (not just arXiv) and rank by citation count, with title, authors, year, venue, and cites/year. BRITTLE: Google aggressively blocks scraping (CAPTCHA / HTTP 429 / IP block), so this often returns an error rather than data.

- **Endpoints:** `/scholar/search`
- **Detail:** `docs/SCHOLAR_API.md` · **params:** `docs/endpoints.csv`

### Trending

NewsNow (self-hosted) — ~50 trending/hot boards: Hacker News, GitHub trending, Product Hunt, plus Weibo/Zhihu/Douyin hot searches and CN finance wires. Ranked title+URL items.

- **Endpoints:** `/trending` · `/trending/{source_id}`
- **params:** `docs/endpoints.csv`

### World Bank

World Bank Open Data — development indicators for every country (GDP, population, poverty, trade).

- **Endpoints:** `/worldbank/countries` · `/worldbank/{indicator}`
- **params:** `docs/endpoints.csv`

### IMF

IMF SDMX-JSON — macroeconomic time series (IFS, DOT, BOP…). Upstream is slow and flaky.

- **Endpoints:** `/imf/structure/{dataset}` · `/imf/{dataset}/{key}`
- **params:** `docs/endpoints.csv`

### Eurostat

Eurostat — official EU statistics (JSON-stat); dimension filters pass through.

- **Endpoints:** `/eurostat/{dataset}`
- **params:** `docs/endpoints.csv`

### ECB

ECB Data Portal — euro-area exchange rates, inflation, and interest rates via SDMX.

- **Endpoints:** `/ecb/{flow_ref}/{key}`
- **params:** `docs/endpoints.csv`

### Comtrade

UN Comtrade — global goods-trade flows (keyless public preview, ≤500 records, rate-limited).

- **Endpoints:** `/comtrade`
- **params:** `docs/endpoints.csv`

### UCDP

Uppsala Conflict Data Program — georeferenced armed-conflict events worldwide.

- **Endpoints:** `/ucdp/gedevents`
- **params:** `docs/endpoints.csv`

### USGS

USGS Earthquake Hazards — worldwide earthquake catalog (GeoJSON).

- **Endpoints:** `/usgs/earthquakes`
- **params:** `docs/endpoints.csv`

### NWS

US National Weather Service — active weather alerts (keyless, User-Agent required).

- **Endpoints:** `/nws/alerts`
- **params:** `docs/endpoints.csv`

### EONET

NASA EONET — global natural events: wildfires, severe storms, volcanoes.

- **Endpoints:** `/eonet/categories` · `/eonet/events`
- **params:** `docs/endpoints.csv`

### Wikipedia

Wikipedia — page summaries, full-text search, and pageview statistics.

- **Endpoints:** `/wikipedia/pageviews/{title}` · `/wikipedia/search` · `/wikipedia/summary/{title}`
- **params:** `docs/endpoints.csv`

### Cross-Reference

Aggregators that combine several sources in one call — a company profile (SEC filings + federal contracts + political contributions) or a politician profile (House stock disclosures + campaign finance). Use to cross-reference a company or politician across sources at once.

- **Endpoints:** `/cross-reference/company/{name}` · `/cross-reference/politician/{last_name}`
- **params:** `docs/endpoints.csv`

### Admin

Operational endpoints (cache management). Not a data source.

- **Endpoints:** `/admin/clear-cache`
- **params:** `docs/endpoints.csv`

## Also

Researched but **not wired** (no endpoint yet): `docs/UNWIRED_RESEARCH.md` (SAM.gov, PatentsView) · `docs/SENATE_EFD_API.md` (Senate financial disclosures).
