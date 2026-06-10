# DataGod — API Guide

Find the right endpoint for the information you need, then call it.

- **Base URL:** `https://datagod.example.com`
- **Auth:** every call needs the header `X-API-Key: <your-key>` — only `GET /health` is public.
- **Response:** read the payload from the `data` field of the `{meta, data, error}` envelope.
- **Drill down:** each source below has a rich description, its endpoint paths, and a link to its detail doc. Per-endpoint **parameters** live in `docs/endpoints.csv` (flat, greppable); full response **schemas** via `GET /openapi.json` (HTTP Basic: user `datagod`, password = your key) or `/docs`.
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


## Sources

A keyword-rich description per source, so you can tell at a glance whether a source has what you need. Endpoint **parameters** are in `docs/endpoints.csv` (flat, greppable); **deep detail and quirks** are in each source's linked doc. Load only the source(s) you need.

### Health

Service utility: API index (`/`) and a public liveness probe (`/health`). Not a data source.

- **Endpoints:** `/` · `/health`
- **params:** `docs/endpoints.csv`

### FRED

US macroeconomic time series (800K+). GDP, inflation and consumer prices (CPI, PCE), unemployment rate, interest rates (Fed funds, Treasury yields), money supply (M1/M2), exchange rates, housing, industrial production, S&P 500, recession indicators. The default for any national economic indicator over time.

- **Keywords:** economy, economic indicators, GDP, inflation, CPI, consumer prices, PCE, deflator, unemployment rate, interest rates, Fed funds rate, Treasury yields, 10-year yield, money supply, M1, M2, exchange rates, housing, industrial production, S&P 500, recession, macroeconomic, time series
- **Endpoints:** `/fred` · `/fred/{series_id}`
- **Detail:** `docs/GOV_APIS.md` · **params:** `docs/endpoints.csv`

### EDGAR

SEC corporate filings and financials. 10-K / 10-Q / 8-K filings, full XBRL financial statements (revenue, net income, assets, liabilities, EPS, cash flow), one-metric-across-all-public-companies comparisons, and full-text search inside filings. Use for any public-company financial data, SEC disclosures, or 'which companies mention X'.

- **Keywords:** SEC, public company, corporation, stock filings, 10-K, 10-Q, 8-K, annual report, quarterly report, financial statements, XBRL, revenue, earnings, net income, assets, liabilities, EPS, cash flow, CIK, ticker, full-text filing search, prospectus, IPO
- **Endpoints:** `/edgar/company/{cik}` · `/edgar/concept/{cik}/{concept}` · `/edgar/financials/{cik}` · `/edgar/frames/{concept}` · `/edgar/search`
- **Detail:** `docs/EDGAR_API.md` · **params:** `docs/endpoints.csv`

### Nasdaq

Stock-market quotes (Nasdaq.com, unofficial). Price, bid/ask, volume, market cap, sector, industry, P/E, 52-week range, dividends, and daily OHLCV history. Use for a quick quote or price snapshot of a listed ticker.

- **Keywords:** stocks, shares, equities, stock price, quote, ticker, symbol, market cap, sector, industry, P/E ratio, 52-week range, bid, ask, volume, dividends, OHLC, price history, real-time quote
- **Endpoints:** `/nasdaq/dividends/{ticker}` · `/nasdaq/history/{ticker}` · `/nasdaq/price/{ticker}` · `/nasdaq/quote/{ticker}`
- **Detail:** `docs/NASDAQ_API.md` · **params:** `docs/endpoints.csv`

### yfinance

Deep equity data (Yahoo Finance). ~140 fundamental fields, full income statement / balance sheet / cash flow, options chains, institutional and fund holders, analyst recommendations, news, and flexible price history. Use for thorough single-ticker analysis beyond a basic quote.

- **Keywords:** stocks, shares, equities, ticker, symbol, stock price, fundamentals, market cap, P/E, EPS, beta, profit margin, ROE, income statement, balance sheet, cash flow, financial statements, options, options chain, calls, puts, implied volatility, holders, ownership, institutional holders, analyst ratings, recommendations, price targets, dividends, earnings, news, OHLCV, history
- **Endpoints:** `/yfinance/dividends/{ticker}` · `/yfinance/financials/{ticker}` · `/yfinance/history/{ticker}` · `/yfinance/holders/{ticker}` · `/yfinance/info/{ticker}` · `/yfinance/news/{ticker}` · `/yfinance/options/{ticker}` · `/yfinance/recommendations/{ticker}`
- **Detail:** `docs/YFINANCE_API.md` · **params:** `docs/endpoints.csv`

### USAspending

US federal spending ($6T+/yr). Government contracts and grants, recipients and contractors, award amounts, and agency spending totals. Use for who received federal money, defense/agency contracts, or grant awards.

- **Keywords:** federal spending, government contracts, grants, awards, contractors, recipients, vendors, procurement, award amount, agency spending, defense spending, federal money, subawards
- **Endpoints:** `/usaspending/agencies` · `/usaspending/by-agency` · `/usaspending/search`
- **Detail:** `docs/GOV_APIS.md` · **params:** `docs/endpoints.csv`

### Census

US demographics (Census Bureau / American Community Survey). Population, median household income, and raw ACS queries — race, age, sex, education, poverty, housing, commute — by state, county, or tract. Use for any US demographic or socioeconomic statistic.

- **Keywords:** demographics, population, household income, median income, ACS, American Community Survey, race, ethnicity, age, sex, gender, education, poverty, housing, rent, commute, employment, state, county, census tract
- **Endpoints:** `/census/acs` · `/census/income` · `/census/population`
- **Detail:** `docs/GOV_APIS.md` · **params:** `docs/endpoints.csv`

### BLS

US labor statistics (Bureau of Labor Statistics). Unemployment rate, nonfarm payroll jobs, wages and average hourly earnings, CPI inflation, PPI producer prices, productivity. Use for the labor market, employment, or price indexes by series.

- **Keywords:** jobs, employment, unemployment rate, labor market, nonfarm payrolls, payroll, wages, earnings, hourly earnings, salary, CPI, inflation, consumer prices, PPI, producer prices, productivity, job openings, labor statistics
- **Endpoints:** `/bls/{series_id}`
- **Detail:** `docs/GOV_APIS.md` · **params:** `docs/endpoints.csv`

### Treasury

US federal fiscal data (Treasury Fiscal Data). National debt (debt to the penny, debt held by the public, intragovernmental), average interest rates on Treasury securities, and government exchange rates. Use for the size of the national debt or US borrowing costs.

- **Keywords:** national debt, public debt, debt to the penny, federal debt, deficit, Treasury, interest rates, yields, borrowing costs, exchange rates, fiscal data
- **Endpoints:** `/treasury/debt` · `/treasury/exchange` · `/treasury/rates`
- **Detail:** `docs/GOV_APIS.md` · **params:** `docs/endpoints.csv`

### FEC

Federal campaign finance (Federal Election Commission). Candidates (President / Senate / House), itemized contributions and donors, and candidate fundraising totals. Use for elections money: who is running, who donated, how much was raised or spent.

- **Keywords:** campaign finance, elections, candidates, presidential candidates, donors, donations, contributions, PAC, super PAC, fundraising, money raised, receipts, disbursements, spending, election money
- **Endpoints:** `/fec/candidates` · `/fec/contributions` · `/fec/totals`
- **Detail:** `docs/GOV_APIS.md` · **params:** `docs/endpoints.csv`

### Congress

US legislation (Congress.gov). Bills with status, sponsors, and actions; members of Congress; and roll-call votes. Use for tracking laws, what Congress is doing, or how members voted.

- **Keywords:** legislation, bills, laws, Congress, House, Senate, representatives, senators, members of Congress, votes, roll call, sponsors, cosponsors, committees
- **Endpoints:** `/congress/bill/{congress_num}/{bill_type}/{number}` · `/congress/bills` · `/congress/members` · `/congress/votes`
- **Detail:** `docs/GOV_APIS.md` · **params:** `docs/endpoints.csv`

### FDA

Drug and food safety (openFDA). Drug adverse-event / side-effect reports (FAERS), drug recalls, and food recalls (contamination, allergens). Use for medication safety, adverse reactions, or recalled products.

- **Keywords:** drugs, medications, adverse events, side effects, reactions, drug safety, drug recalls, food recalls, recalls, contamination, allergens, openFDA, FAERS, pharmaceuticals
- **Endpoints:** `/fda/drug-events` · `/fda/drug-recalls` · `/fda/food-recalls`
- **Detail:** `docs/GOV_APIS.md` · **params:** `docs/endpoints.csv`

### Clinical Trials

Medical research trials (ClinicalTrials.gov, 500K+ studies). Search by condition or disease, intervention or drug, and status (recruiting, completed). Use for clinical trials on a disease or treatment.

- **Keywords:** clinical trials, medical trials, studies, drug trials, condition, disease, intervention, treatment, recruiting, NCT, research studies, sponsors
- **Endpoints:** `/clinical-trials` · `/clinical-trials/{nct_id}`
- **Detail:** `docs/GOV_APIS.md` · **params:** `docs/endpoints.csv`

### EIA

US energy data (Energy Information Administration). Gasoline and fuel prices, electricity generation / sales / prices, and any energy series — crude oil, natural gas, coal, renewables, CO2 emissions, consumption. Use for energy prices or production.

- **Keywords:** energy, gasoline prices, gas prices, fuel prices, oil, crude oil, petroleum, natural gas, electricity, power, generation, coal, renewables, solar, wind, emissions, CO2, energy consumption
- **Endpoints:** `/eia` · `/eia/electricity` · `/eia/gas-prices` · `/eia/{route}`
- **Detail:** `docs/GOV_APIS.md` · **params:** `docs/endpoints.csv`

### FEMA

Disasters and emergency management (OpenFEMA). Federal disaster declarations (hurricanes, floods, wildfires, severe storms), FEMA grants and assistance, and NFIP flood-insurance claims. Use for disaster events or federal disaster aid.

- **Keywords:** disasters, disaster declarations, hurricanes, floods, wildfires, fires, storms, earthquakes, emergencies, disaster relief, grants, assistance, flood insurance, NFIP, flood claims
- **Endpoints:** `/fema/disasters` · `/fema/flood-claims` · `/fema/grants`
- **Detail:** `docs/GOV_APIS.md` · **params:** `docs/endpoints.csv`

### Federal Register

US federal regulations (Federal Register). Proposed and final rules, agency notices, executive orders, and presidential documents — searchable by type and agency. Use for rulemaking, regulations, or executive orders.

- **Keywords:** regulations, rules, rulemaking, proposed rules, final rules, notices, executive orders, presidential documents, agencies, federal regulations
- **Endpoints:** `/federal-register` · `/federal-register/{doc_number}`
- **Detail:** `docs/GOV_APIS.md` · **params:** `docs/endpoints.csv`

### JEFS

Federal judges' financial disclosures (Judicial). Disclosure reports for federal judges — session-based, requires Playwright registration + reCAPTCHA first. Use for the finances or holdings of federal judges.

- **Keywords:** federal judges, judicial, judges financial disclosures, judiciary, court, judge holdings, financial disclosure reports
- **Endpoints:** `/jefs/facets` · `/jefs/register` · `/jefs/reset` · `/jefs/search`
- **Detail:** `docs/JEFS_API.md` · **params:** `docs/endpoints.csv`

### House Disclosures

US House financial disclosures. Representatives' and candidates' stock trades and holdings (congressional trading / periodic transaction reports). Use for politicians' stock transactions in the House.

- **Keywords:** congressional stock trades, stock trades, politician trading, House members, representatives, financial disclosures, holdings, periodic transaction reports, PTR, congressional trading
- **Endpoints:** `/house-disclosures/candidates` · `/house-disclosures/members`
- **Detail:** `docs/HOUSE_FD_API.md` · **params:** `docs/endpoints.csv`

### NARA

US National Archives catalog. Historical federal records across all record groups and the 14 presidential libraries. Use for archival US government documents, historical records, or presidential materials.

- **Keywords:** National Archives, archives, historical records, government records, presidential libraries, primary sources, declassified, catalog, historical documents
- **Endpoints:** `/nara/record/{na_id}` · `/nara/search`
- **Detail:** `docs/NARA_API.md` · **params:** `docs/endpoints.csv`

### NSArchive

Declassified national-security documents (National Security Archive — a GWU NGO, not NARA). Virtual Reading Room: foreign policy, intelligence, military, declassified cables and memos. Use for declassified Cold War or foreign-policy documents.

- **Keywords:** declassified, national security, intelligence, CIA, foreign policy, Cold War, cables, memos, FOIA, classified documents, diplomacy
- **Endpoints:** `/nsarchive/document/{doc_id}` · `/nsarchive/search`
- **Detail:** `docs/NSARCHIVE_API.md` · **params:** `docs/endpoints.csv`

### Smithsonian

Museum and archive collections (Smithsonian Open Access, 11M+ objects). Art, history, science specimens, and photographs with metadata, plus category and controlled-term browsing. Use for museum objects, cultural artifacts, or collection metadata.

- **Keywords:** museum, museums, art, artwork, paintings, artifacts, collections, history, science, specimens, photographs, images, cultural heritage, open access, objects
- **Endpoints:** `/smithsonian/category/{category}/search` · `/smithsonian/object/{object_id}` · `/smithsonian/search` · `/smithsonian/stats` · `/smithsonian/terms/{category}`
- **Detail:** `docs/SMITHSONIAN_API.md` · **params:** `docs/endpoints.csv`

### Wilson Center

Cold War and international-history documents (Wilson Center Digital Archive, local mirror). 16,756 declassified primary-source documents on diplomacy and international relations. Use for primary-source Cold War and foreign-relations documents.

- **Keywords:** Cold War, diplomacy, international relations, foreign policy, declassified documents, primary sources, history, digital archive, telegrams
- **Endpoints:** `/wilson/document/{slug}` · `/wilson/documents`
- **Detail:** `docs/WILSON_DIGITAL_ARCHIVE_API.md` · **params:** `docs/endpoints.csv`

### Cross-Reference

Aggregators that join several sources in one call. Company -> SEC filings + federal contracts + political contributions; politician -> House stock disclosures + campaign finance. Use to profile a company or politician across sources at once.

- **Keywords:** company profile, politician profile, aggregate, combined, cross-reference, multi-source
- **Endpoints:** `/cross-reference/company/{name}` · `/cross-reference/politician/{last_name}`
- **params:** `docs/endpoints.csv`

### Admin

Operational endpoints (cache management). Not a data source.

- **Endpoints:** `/admin/clear-cache`
- **params:** `docs/endpoints.csv`
