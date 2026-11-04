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
| Declassified CIA documents & famous collections | CIA | `GET /cia/collections` |
| Official US diplomatic record (FRUS volumes) | FRUS | `GET /frus/search` |
| UK government records catalog | TNA | `GET /tna/search` |
| FBI FOIA files on famous subjects | Vault | `GET /vault/subjects` |
| Mirrored intelligence-community documents (IRP) | FAS | `GET /fas/sections` |
| Translated Soviet-bloc / Cold War documents (16,756-doc local mirror) | Wilson Center | `GET /wilson/documents` |
| Museum / library / archive objects | Smithsonian | `GET /smithsonian/search` |
| Scientific preprints / research papers | arXiv | `GET /arxiv/search` |
| Academic papers ranked by citations | Scholar | `GET /scholar/search` (brittle — Google blocks) |
| Public-domain space/science video & imagery | NASA Images | `GET /nasa/search` |
| Archival / public-domain footage (newsreels, Prelinger) | Internet Archive | `GET /archive/search` |
| CC-licensed video files with direct URLs | Commons | `GET /commons/search` |
| Cross-country development indicators: GDP, population, poverty | World Bank | `GET /worldbank/{indicator}` (e.g. `NY.GDP.MKTP.CD`) |
| IMF forecasts (World Economic Outlook), monthly CPI, balance of payments | IMF | `GET /imf/WEO/USA.NGDP_RPCH.A` |
| Official EU statistics: population, HICP inflation, unemployment | Eurostat | `GET /eurostat/{dataset}` (e.g. `tps00001?geo=DE`) |
| Euro exchange rates and euro-area monetary data | ECB | `GET /ecb/EXR/D.USD.EUR.SP00.A` |
| Goods trade between two countries (imports/exports by HS code) | Comtrade | `GET /comtrade?reporterCode=842&partnerCode=156` |
| Armed-conflict events and fatalities worldwide | UCDP | `GET /ucdp/gedevents` (needs `UCDP_ACCESS_TOKEN`) |
| Earthquakes worldwide | USGS | `GET /usgs/earthquakes` |
| Active US weather alerts | NWS | `GET /nws/alerts?area=CA` |
| Ongoing wildfires, storms, volcanoes worldwide | EONET | `GET /eonet/events?category=wildfires` |
| Encyclopedic background, whole article text, pageviews | Wikipedia | `GET /wikipedia/summary/{title}` |
| What's trending now: Hacker News, GitHub, Weibo, Zhihu… | Trending | `GET /trending/{source_id}` (ids: `GET /trending`) |
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

### CIA

Declassified CIA documents (CIA FOIA Electronic Reading Room, read through the Wayback Machine mirror because cia.gov blocks server clients) — famous collections (STARGATE, UFOs, Bay of Pigs, President's Daily Brief, Vietnam, Berlin Tunnel, Soviet Navy, Warsaw Pact) and single documents by CREST number with body text and PDF. No full-text search: browse collections or arrive with a document number from NSArchive, NARA or FRUS.

- **Endpoints:** `/cia/collection/{slug}` · `/cia/collections` · `/cia/document/{doc_path}`
- **Detail:** `docs/CIA_API.md` · **params:** `docs/endpoints.csv`

### FRUS

Foreign Relations of the United States (history.state.gov) — the official State Department documentary record of US foreign policy: 500+ volumes of declassified cables, memos, meeting minutes and covert-action documents (Iran 1953, Guatemala, Congo, Chile, the intelligence community). Full-text search plus single documents with archival source notes.

- **Endpoints:** `/frus/document/{volume}/{doc}` · `/frus/search`
- **Detail:** `docs/FRUS_API.md` · **params:** `docs/endpoints.csv`

### TNA

UK National Archives (Discovery catalog, 32M+ record descriptions) — British government records including declassified intelligence and military files: MI5 Security Service (KV), Special Operations Executive (HS), Cabinet Office / JIC (CAB), Ministry of Defence (DEFE), Prime Minister's Office (PREM), Foreign Office (FO). Use for UK historical and intelligence records.

- **Endpoints:** `/tna/record/{record_id}` · `/tna/search`
- **Detail:** `docs/TNA_API.md` · **params:** `docs/endpoints.csv`

### Vault

FBI Vault (vault.fbi.gov, via the Wayback mirror) — the FBI's FOIA library of released files on famous subjects: COINTELPRO, Roswell and UFOs, Majestic 12, Watergate, VENONA, the Rosenbergs, Alger Hiss, Martin Luther King Jr., the KKK. Browse subject → folders → files → PDFs.

- **Endpoints:** `/vault/page/{path}` · `/vault/subjects`
- **Detail:** `docs/VAULT_API.md` · **params:** `docs/endpoints.csv`

### FAS

FAS Intelligence Resource Program (irp.fas.org) — the Federation of American Scientists' mirror of US intelligence and military documents: NSA, CIA and DIA agency pages, surveillance and collection programs, official documents, DoD directives, congressional oversight, foreign intelligence services. Full-text pages plus PDF links.

- **Endpoints:** `/fas/index/{path}` · `/fas/page/{path}` · `/fas/sections`
- **Detail:** `docs/FAS_API.md` · **params:** `docs/endpoints.csv`

### Smithsonian

Museum and archive collections (Smithsonian Open Access, 11M+ objects) — art and artwork, artifacts, history, science specimens, and photographs / images with metadata and category / term browsing. Use for museum objects, cultural heritage, or collection metadata.

- **Endpoints:** `/smithsonian/category/{category}/search` · `/smithsonian/object/{object_id}` · `/smithsonian/search` · `/smithsonian/stats` · `/smithsonian/terms/{category}`
- **Detail:** `docs/SMITHSONIAN_API.md` · **params:** `docs/endpoints.csv`

### Wilson Center

Cold War and international-history primary sources (Wilson Center Digital Archive, local mirror) — 16,756 declassified documents on diplomacy, foreign policy, and international relations (cables, telegrams). Use for primary-source Cold War and foreign-relations documents.

- **Endpoints:** `/wilson/document/{slug}` · `/wilson/documents`
- **Detail:** `docs/WILSON_DIGITAL_ARCHIVE_API.md` · **params:** `docs/endpoints.csv`

### arXiv

Scientific preprints from arXiv.org — full-text search of 2M+ open-access papers in physics, math, computer science, machine learning and AI, quantitative biology, economics, and statistics; by topic, author, title, or arXiv id, with abstracts, authors, categories, and PDF links. Use for academic papers, research preprints, or scientific literature.

- **Endpoints:** `/arxiv/search` · `/arxiv/{arxiv_id}`
- **Detail:** `docs/ARXIV_API.md` · **params:** `docs/endpoints.csv`

### Scholar

Academic papers ranked by citations from Google Scholar (via the vendored sort-google-scholar). Search scholarly literature across all publishers and journals (not just arXiv) and rank by citation count, with title, authors, year, venue, and cites/year. BRITTLE: Google aggressively blocks scraping (CAPTCHA / HTTP 429 / IP block), so this often returns an error rather than data.

- **Endpoints:** `/scholar/search`
- **Detail:** `docs/SCHOLAR_API.md` · **params:** `docs/endpoints.csv`

### Trending

What's trending right now (self-hosted NewsNow, ~50 boards) — Hacker News, Product Hunt, GitHub trending, V2EX, plus Chinese hot lists (Weibo, Zhihu, Douyin, Baidu, Bilibili, Toutiao) and CN finance wires (Wallstreetcn, CLS, Xueqiu). Ranked titles and URLs. Use for current tech, social and news buzz.

- **Endpoints:** `/trending` · `/trending/{source_id}`
- **Detail:** `docs/NEWSNOW_API.md` · **params:** `docs/endpoints.csv`

### World Bank

World Bank Open Data — 16K+ development indicators for every country and aggregate: GDP, population, poverty, trade, education, health, energy. Use for cross-country macro/development comparisons and long historical series.

- **Endpoints:** `/worldbank/countries` · `/worldbank/{indicator}`
- **Detail:** `docs/WORLDBANK.md` · **params:** `docs/endpoints.csv`

### IMF

IMF macroeconomic data from the IMF's own SDMX API — World Economic Outlook (WEO) history and forecasts (real GDP growth, inflation, unemployment, government debt, current account by country, ~5 years ahead), monthly CPI, balance of payments, trade (IMTS), Fiscal Monitor. Use for IMF projections and cross-country macro series.

- **Endpoints:** `/imf/structure/{dataset}` · `/imf/{dataset}/{key}`
- **Detail:** `docs/IMF.md` · **params:** `docs/endpoints.csv`

### Eurostat

Eurostat — official EU statistics: population, GDP, inflation (HICP), unemployment, energy, trade for EU members and aggregates. Use for any EU/euro-area country statistic.

- **Endpoints:** `/eurostat/{dataset}`
- **Detail:** `docs/EUROSTAT.md` · **params:** `docs/endpoints.csv`

### ECB

ECB Data Portal — euro-area statistics via SDMX: EXR daily reference exchange rates (USD/EUR and all pairs), ICP inflation, interest rates, money supply. Use for euro FX rates and euro-area monetary data.

- **Endpoints:** `/ecb/{flow_ref}/{key}`
- **Detail:** `docs/ECB.md` · **params:** `docs/endpoints.csv`

### Comtrade

UN Comtrade — global goods-trade flows between countries: annual imports/exports by HS commodity code, reporter and partner country. Use for bilateral trade values and commodity-level trade.

- **Endpoints:** `/comtrade`
- **Detail:** `docs/COMTRADE.md` · **params:** `docs/endpoints.csv`

### UCDP

UCDP — Uppsala Conflict Data Program georeferenced event dataset (GED): individual organized-violence events worldwide with location, date, actors, and fatality estimates. Use for armed-conflict and political-violence data.

- **Endpoints:** `/ucdp/gedevents`
- **Detail:** `docs/UCDP.md` · **params:** `docs/endpoints.csv`

### USGS

USGS Earthquake Hazards — worldwide earthquake catalog: magnitude, place, time, coordinates, depth for recent and historical quakes. Use for any earthquake query, global.

- **Endpoints:** `/usgs/earthquakes`
- **Detail:** `docs/USGS.md` · **params:** `docs/endpoints.csv`

### NWS

US National Weather Service — active weather alerts (warnings, watches, advisories) by state: severe storms, floods, heat, fire weather. Use for current US weather hazards.

- **Endpoints:** `/nws/alerts`
- **Detail:** `docs/NWS.md` · **params:** `docs/endpoints.csv`

### EONET

NASA EONET — global natural-event tracker: open wildfires, severe storms, volcanoes, floods, sea ice, with coordinates and source links. Use for currently-burning wildfires and other ongoing natural events worldwide.

- **Endpoints:** `/eonet/categories` · `/eonet/events`
- **Detail:** `docs/EONET.md` · **params:** `docs/endpoints.csv`

### Wikipedia

Wikipedia — page summaries (lead section + thumbnail), whole articles as plain text, full-text article search, and daily pageview counts (attention/popularity over time). Use for encyclopedic lookups, background research, and gauging public attention on a topic.

- **Endpoints:** `/wikipedia/article/{title}` · `/wikipedia/pageviews/{title}` · `/wikipedia/search` · `/wikipedia/summary/{title}`
- **Detail:** `docs/WIKIPEDIA.md` · **params:** `docs/endpoints.csv`

### NASA Images

Public-domain space and science media (NASA Image and Video Library, images.nasa.gov) — videos, images, and audio of launches, missions (Apollo, Artemis, ISS, Mars rovers), astronauts, planets, and Earth observation, with direct downloadable mp4 renditions per asset. Everything is public domain (credit 'NASA'). Use for keyless space/science footage.

- **Endpoints:** `/nasa/asset/{nasa_id}` · `/nasa/search`
- **Detail:** `docs/NASA_IMAGES_API.md` · **params:** `docs/endpoints.csv`

### Internet Archive

Archival video and film (Internet Archive, archive.org) — newsreels, public-domain footage (prelinger archives), historical broadcasts, old movies and TV, searchable by keyword with per-item file lists and direct download paths. License is per item (licenseurl) — the public-domain collections are the harvest target. Use for historical or public-domain footage.

- **Endpoints:** `/archive/item/{identifier}` · `/archive/search`
- **Detail:** `docs/INTERNET_ARCHIVE_API.md` · **params:** `docs/endpoints.csv`

### Commons

Free-licensed video files (Wikimedia Commons) — CC-BY / CC-BY-SA / public-domain clips of nature, cities, events, science, and people, each with a direct file URL, size, mime type, and per-file license + author metadata (extmetadata). Use for reusable CC video clips; credit per file.

- **Endpoints:** `/commons/search`
- **Detail:** `docs/COMMONS_API.md` · **params:** `docs/endpoints.csv`

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
