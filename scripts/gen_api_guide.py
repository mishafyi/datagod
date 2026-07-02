#!/usr/bin/env python3
"""Generate the agent-facing API guide: docs/API_GUIDE.md + docs/endpoints.csv.

Run from the project root after route changes:

    .venv/bin/python -m scripts.gen_api_guide

The guide answers "which endpoint for which information": a routing map, plus a
keyword-rich description and the parameters for every endpoint, so an agent can
both find AND call an endpoint without a second lookup. Parameters come from the
live OpenAPI schema; the keyword descriptions are curated in DESCRIPTIONS below
(fall back to the OpenAPI summary if missing). endpoints.csv is the same data,
flat, for grep/tooling. /openapi.json (Basic auth) remains the source of truth
for full response schemas.
"""

import csv
from pathlib import Path

from app.main import app

HEADER = """\
# DataGod — API Guide

Find the right endpoint for the information you need, then call it.

- **Base URL:** `https://datagod.example.com`
- **Auth:** every call needs the header `X-API-Key: <your-key>` — only `GET /health` is public. On this machine the key is in `.env` as `DATAGOD_API_KEY`; see `docs/AGENT_QUICKSTART.md` for copy-paste setup.
- **Response:** read the payload from the `data` field of the `{meta, data, error}` envelope.
- **Drill down:** each source below has a rich description, its endpoint paths, and a link to its detail doc. Per-endpoint **parameters** live in `docs/endpoints.csv` (flat, greppable); full response **schemas** via `GET /openapi.json` (HTTP Basic: user `datagod`, password = your key) or `/docs`.
- **Limits:** a valid key has **no per-key usage or rate limit** on DataGod itself. Caveats: each endpoint's `limit` query param caps results **per call** (paginate for more), SEC EDGAR is throttled to ~10 req/sec (SEC's rule, shared across callers), and each upstream enforces its own rate limits (the DEMO_KEY-backed FEC / Congress / EIA / Smithsonian are low) — DataGod passes those through.
"""

EXAMPLE = """\
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
"""

# NOTE: JEFS (2026-06-11) and Wilson Center (2026-07-02) routes are disabled in
# app/main.py, so both auto-drop from the route-driven Sources section +
# endpoints.csv. Their entries in the dicts below are kept for easy re-enable
# (they don't render while the routes are off). If you re-enable one, also
# restore its row in the QUICK_INDEX table here.
QUICK_INDEX = """\
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
"""

# Curated keyword-rich descriptions, keyed by route path. These power agent
# routing — pack in synonyms and the concrete things each endpoint returns.
DESCRIPTIONS = {
    "/": "Service index: lists every data source and its endpoint groups. Use to discover what is available.",
    "/health": "Health / liveness check. Public, no key. Use for uptime monitoring and readiness probes.",
    "/fred/{series_id}": "One US macroeconomic time series by FRED series ID. Use for: GDP, inflation, consumer prices/CPI (CPIAUCSL), unemployment rate (UNRATE), Fed funds / interest rates (FEDFUNDS), Treasury yields (DGS10), money supply (M2), S&P 500 (SP500), industrial production, recession indicators — any US macro indicator.",
    "/fred": "Keyword search across FRED's 800K-series catalog; returns series IDs to fetch above. Use when you don't know the exact series ID.",
    "/edgar/company/{cik}": "SEC company profile and filing history (10-K, 10-Q, 8-K, S-1, etc.) by CIK or ticker (e.g. AAPL). Use for: company metadata, recent filings, fiscal year end, SIC industry, exchange, addresses, former names.",
    "/edgar/financials/{cik}": "All XBRL financial facts for a company across years. Use for: revenue, net income, assets, liabilities, cash, equity, EPS, R&D spend — the full financial-statement dataset.",
    "/edgar/concept/{cik}/{concept}": "History of one XBRL concept for one company (e.g. Revenues, NetIncomeLoss, Assets, CashAndCashEquivalents). Use to track a single financial metric over time.",
    "/edgar/frames/{concept}": "One financial concept across ALL public companies for a period — cross-company comparison in a single call. Use to rank or compare revenue / assets / net income across thousands of filers.",
    "/edgar/search": "Full-text search inside SEC filing documents. Use for: which companies mention a topic (AI, climate risk, layoffs, a competitor, a country like Ukraine, a product) in their filings; filter by form type (forms=) and filing-date range (startdt/enddt, YYYY-MM-DD, covers 2001+). Returns a fixed 100 hits/page; paginate with from (0,100,200… max 9900 — the SEC caps results at 10,000).",
    "/nasdaq/quote/{ticker}": "Stock quote summary: market cap, sector, industry, P/E, dividend yield, 52-week high/low. Quick snapshot of a listed company.",
    "/nasdaq/price/{ticker}": "Current price, bid/ask, day volume, and percent change for a ticker.",
    "/nasdaq/history/{ticker}": "Daily OHLCV price history (open, high, low, close, volume) between two dates.",
    "/nasdaq/dividends/{ticker}": "Dividend payment history (ex-date and amount) for a ticker.",
    "/yfinance/info/{ticker}": "Deepest single-call company profile (~140 fields): market cap, P/E, EPS, beta, profit margins, ROE, debt, free cash flow, analyst price targets, sector, employees, business summary.",
    "/yfinance/history/{ticker}": "OHLCV price history with flexible period (1d..max) and interval (1m..1mo). Use for charts, returns, volatility.",
    "/yfinance/news/{ticker}": "Recent news headlines and article links tied to a ticker.",
    "/yfinance/recommendations/{ticker}": "Analyst recommendation history (buy / hold / sell ratings over time).",
    "/yfinance/holders/{ticker}": "Ownership: major holders, institutional holders, and mutual-fund holders.",
    "/yfinance/financials/{ticker}": "Income statement, balance sheet, and cash-flow statement (annual + quarterly).",
    "/yfinance/dividends/{ticker}": "Dividend payment history (amounts and dates).",
    "/yfinance/options/{ticker}": "Options chain: expiry dates, calls and puts, strikes, implied volatility, open interest.",
    "/usaspending/agencies": "List of federal agencies (names and IDs) for filtering spending queries.",
    "/usaspending/search": "Search federal awards (contracts and grants) by keyword. Use for: who received federal money, contractors/recipients, award amounts, defense or agency spending.",
    "/usaspending/by-agency": "Federal spending totals grouped by agency for a fiscal year / quarter.",
    "/census/population": "Population by US state.",
    "/census/income": "Median household income by US state.",
    "/census/acs": "Raw American Community Survey query — any ACS variables and geography (state / county / tract). Use for: demographics, race, age, sex, education, income, poverty, housing, commute — any ACS table by variable code.",
    "/bls/{series_id}": "US labor statistics series by ID. Use for: unemployment rate, nonfarm payroll employment, CPI inflation, PPI, average hourly earnings. Shortcut IDs: unemployment, cpi, nonfarm_employment, ppi, hourly_earnings.",
    "/treasury/debt": "US national / public debt (debt to the penny): total outstanding, debt held by the public, intragovernmental holdings, by date.",
    "/treasury/rates": "Average interest rates on outstanding US Treasury securities.",
    "/treasury/exchange": "US Treasury reporting exchange rates (foreign-currency conversion rates used by the government).",
    "/fec/candidates": "Search federal candidates (President, Senate, House) by office and state. Campaign finance.",
    "/fec/contributions": "Campaign contributions — itemized donations by or for a candidate or donor name.",
    "/fec/totals": "Candidate financial totals (money raised / receipts), ranked, by office and election year.",
    "/congress/bills": "Recent bills introduced in Congress. Legislation tracking.",
    "/congress/bill/{congress_num}/{bill_type}/{number}": "Full detail for one bill: sponsors, actions, latest status, summary.",
    "/congress/members": "Members of Congress (representatives and senators), with party and state.",
    "/congress/votes": "Roll-call votes by chamber and session.",
    "/fda/drug-events": "Drug adverse-event reports (side effects, reactions) from openFDA / FAERS.",
    "/fda/drug-recalls": "Drug recall enforcement reports — recalled medications, reasons, recall class.",
    "/fda/food-recalls": "Food recall enforcement reports — recalled foods, contamination, allergens, reasons.",
    "/clinical-trials": "Search ClinicalTrials.gov by condition, intervention, and status (recruiting, completed). Medical and drug trials.",
    "/clinical-trials/{nct_id}": "Full record for one clinical trial by its NCT ID.",
    "/eia": "List the EIA energy datasets available to query.",
    "/eia/gas-prices": "Gasoline and fuel prices over time.",
    "/eia/electricity": "Electricity data: generation, retail sales, and prices.",
    "/eia/{route}": "Generic EIA dataset query by route path — any energy series (crude oil, natural gas, coal, renewables, CO2 emissions, consumption).",
    "/fema/disasters": "Federal disaster declarations (hurricanes, floods, wildfires, severe storms) by date and state.",
    "/fema/grants": "FEMA grant and assistance awards.",
    "/fema/flood-claims": "NFIP (National Flood Insurance Program) flood insurance claims data.",
    "/federal-register": "Search the Federal Register: proposed and final rules, notices, executive orders, and presidential documents; filter by type and agency.",
    "/federal-register/{doc_number}": "One Federal Register document by its document number.",
    "/jefs/register": "Open a JEFS session for judicial financial disclosures — drives a Playwright browser through registration + reCAPTCHA. Requires a real name, occupation, and address.",
    "/jefs/facets": "Available JEFS filters (years, courts, positions, report types). Requires an active session.",
    "/jefs/search": "Search federal judges' financial disclosure reports. Requires an active session (call /jefs/register first).",
    "/jefs/reset": "Clear the JEFS session; you must re-register before the next call.",
    "/house-disclosures/members": "US House members' financial disclosures — congressional stock trades and holdings.",
    "/house-disclosures/candidates": "US House candidates' financial disclosures.",
    "/nara/search": "Search the US National Archives Catalog — historical government records across all record groups and the 14 presidential libraries.",
    "/nara/record/{na_id}": "One National Archives catalog record by its National Archives Identifier (NAID).",
    "/nsarchive/search": "Search the National Security Archive (GWU NGO) Virtual Reading Room — declassified documents on foreign policy, intelligence, and defense.",
    "/nsarchive/document/{doc_id}": "One declassified Virtual Reading Room document by its id-slug.",
    "/smithsonian/search": "Search Smithsonian Open Access — 11M+ museum, library, and archive objects (art, history, science specimens, photographs).",
    "/smithsonian/object/{object_id}": "Full metadata record for one Smithsonian object by EDAN id.",
    "/smithsonian/category/{category}/search": "Search within a Smithsonian category: art_design, history_culture, or science_technology.",
    "/smithsonian/terms/{category}": "Controlled-vocabulary terms for a facet: culture, topic, place, object_type, data_source, date, or name.",
    "/smithsonian/stats": "Smithsonian Open Access dataset statistics (counts by unit, type, etc.).",
    "/wilson/documents": "Full-text search the Wilson Center Digital Archive (local mirror) — 16,756 declassified Cold War and international-history documents.",
    "/wilson/document/{slug}": "One Wilson Center document by slug: title, source, subjects, download availability.",
    "/arxiv/search": "Full-text search arXiv.org scientific preprints (physics, math, computer science, machine learning/AI, quantitative biology, economics, statistics). Use for: academic papers, research preprints, scientific literature by topic/author/title. sort_by relevance|lastUpdatedDate|submittedDate; page with start (max_results le 100).",
    "/arxiv/{arxiv_id}": "Fetch one or more arXiv papers by arXiv id (e.g. 2301.00001; comma-separated for several): title, authors, abstract, categories, PDF link, DOI.",
    "/scholar/search": "Search Google Scholar and rank papers by citation count (scholarly literature across all publishers, not just arXiv). Use for: most-cited papers on a topic, citation counts, academic impact. BRITTLE — Google blocks automated access (CAPTCHA/429), so this often returns an error rather than data.",
    "/cross-reference/company/{name}": "Aggregate a company across EDGAR + USAspending + FEC in one call: SEC filings + federal contracts + political contributions.",
    "/cross-reference/politician/{last_name}": "Aggregate a politician across House disclosures + FEC: stock trades + campaign finance.",
    "/admin/clear-cache": "Clear the in-memory cache (operational endpoint).",
}

# Keyword-rich per-source descriptions — the recall layer. The keywords are woven
# INTO the prose (literal search terms like "stocks"/"shares", not only "equity",
# plus the names of the main datasets) so an LLM or grep matches the source.
SOURCE_DESC = {
    "Health": "Service utility: API index (`/`) and a public liveness probe (`/health`). Not a data source.",
    "FRED": "US economy and macroeconomic time series (800K+) — GDP, inflation and consumer prices (CPI, PCE), unemployment rate, interest rates (Fed funds, Treasury yields, 10-year), money supply (M1/M2), exchange rates, housing, industrial production, S&P 500, recession indicators. The default for any national economic indicator over time.",
    "EDGAR": "SEC filings and financials for public companies and corporations — 10-K, 10-Q, 8-K annual and quarterly reports, full XBRL financial statements (revenue, earnings, net income, assets, liabilities, EPS, cash flow), one-metric-across-all-companies comparisons, and full-text search inside filings (by CIK or ticker). Use for any public-company financial data, SEC disclosures, or 'which companies mention X'.",
    "Nasdaq": "Stock-market quotes for stocks, shares, and equities (Nasdaq.com, unofficial) — price, quote, bid/ask, volume, market cap, sector, industry, P/E, 52-week range, dividends, and daily OHLCV price history by ticker/symbol. Use for a quick quote or price snapshot of a listed ticker.",
    "yfinance": "Deep data for stocks, shares, and equities (Yahoo Finance) by ticker/symbol — ~140 fundamental fields (market cap, P/E, EPS, beta, margins, ROE), full financial statements (income statement, balance sheet, cash flow), options chains (calls, puts, implied volatility), institutional and fund holders/ownership, analyst recommendations and price targets, dividends, earnings, news, and OHLCV price history. Use for thorough single-ticker stock analysis beyond a basic quote.",
    "USAspending": "US federal spending ($6T+/yr) — government contracts, grants, and awards; recipients, contractors, and vendors; award amounts; agency and defense spending totals; subawards. Use for who received federal money, federal contracts, or grant awards.",
    "Census": "US demographics from the Census Bureau / American Community Survey (ACS) — population, median household income, race and ethnicity, age, sex, education, poverty, housing and rent, commute, employment — by state, county, or census tract. Use for any US demographic or socioeconomic statistic.",
    "BLS": "US labor statistics and jobs data (Bureau of Labor Statistics) — unemployment rate, employment and nonfarm payrolls, wages and average hourly earnings, job openings, CPI inflation and consumer prices, PPI producer prices, productivity, by series. Use for the labor market, jobs, or price indexes.",
    "Treasury": "US federal fiscal data (Treasury) — the national / public debt (debt to the penny, debt held by the public, intragovernmental), federal deficit context, average interest rates and yields on Treasury securities, and government exchange rates. Use for the size of the national debt or US borrowing costs.",
    "FEC": "Federal campaign finance and elections (FEC) — candidates (presidential, Senate, House), itemized contributions and donors, PAC and super PAC money, and candidate fundraising totals (receipts, disbursements). Use for election money: who is running, who donated, how much was raised or spent.",
    "Congress": "US legislation and Congress (Congress.gov) — bills and laws with status, sponsors and cosponsors, and actions; members of Congress (representatives, senators); committees; and roll-call votes. Use for tracking laws, what Congress is doing, or how members voted.",
    "FDA": "Drug and food safety (openFDA) — drug adverse-event and side-effect reports (FAERS), drug recalls, and food recalls (contamination, allergens), for medications and pharmaceuticals. Use for medication safety, adverse reactions, or recalled products.",
    "Clinical Trials": "Clinical and medical trials (ClinicalTrials.gov, 500K+ studies) — searchable by condition or disease, intervention / drug or treatment, and status (recruiting, completed), by NCT id. Use for clinical or drug trials on a disease or treatment.",
    "EIA": "US energy data (Energy Information Administration) — gasoline and fuel prices, crude oil and petroleum, natural gas, electricity (generation, sales, prices), coal, renewables (solar, wind), CO2 emissions, and energy consumption. Use for energy prices or production.",
    "FEMA": "Disasters and emergency management (OpenFEMA) — federal disaster declarations (hurricanes, floods, wildfires / fires, storms, earthquakes, emergencies), FEMA grants and assistance, and NFIP flood-insurance claims. Use for disaster events or federal disaster aid.",
    "Federal Register": "US federal regulations (Federal Register) — proposed and final rules and rulemaking, agency notices, executive orders, and presidential documents, by type and agency. Use for regulations, rules, or executive orders.",
    "JEFS": "Financial disclosures of federal judges (Judicial) — judges' financial disclosure reports and holdings. Session-based: requires Playwright registration + reCAPTCHA first. Use for the finances or holdings of federal judges and the judiciary.",
    "House Disclosures": "US House financial disclosures and congressional stock trades — representatives' and candidates' stock trades, holdings, and periodic transaction reports (PTRs). Use for politicians' or members of Congress' stock transactions in the House.",
    "NARA": "US National Archives catalog — historical federal and government records, primary sources, and declassified documents across all record groups and the 14 presidential libraries. Use for archival US government documents, historical records, or presidential materials.",
    "NSArchive": "Declassified national-security documents (National Security Archive — a GWU NGO, not NARA) — foreign policy, intelligence (CIA), military, and Cold War cables, memos, and FOIA releases. Use for declassified Cold War or foreign-policy documents.",
    "Smithsonian": "Museum and archive collections (Smithsonian Open Access, 11M+ objects) — art and artwork, artifacts, history, science specimens, and photographs / images with metadata and category / term browsing. Use for museum objects, cultural heritage, or collection metadata.",
    "Wilson Center": "Cold War and international-history primary sources (Wilson Center Digital Archive, local mirror) — 16,756 declassified documents on diplomacy, foreign policy, and international relations (cables, telegrams). Use for primary-source Cold War and foreign-relations documents.",
    "arXiv": "Scientific preprints from arXiv.org — full-text search of 2M+ open-access papers in physics, math, computer science, machine learning and AI, quantitative biology, economics, and statistics; by topic, author, title, or arXiv id, with abstracts, authors, categories, and PDF links. Use for academic papers, research preprints, or scientific literature.",
    "Scholar": "Academic papers ranked by citations from Google Scholar (via the vendored sort-google-scholar). Search scholarly literature across all publishers and journals (not just arXiv) and rank by citation count, with title, authors, year, venue, and cites/year. BRITTLE: Google aggressively blocks scraping (CAPTCHA / HTTP 429 / IP block), so this often returns an error rather than data.",
    "Cross-Reference": "Aggregators that combine several sources in one call — a company profile (SEC filings + federal contracts + political contributions) or a politician profile (House stock disclosures + campaign finance). Use to cross-reference a company or politician across sources at once.",
    "Admin": "Operational endpoints (cache management). Not a data source.",
}

# Where each source's deep-detail doc lives (empty = no dedicated doc yet).
SOURCE_DOC = {
    "FRED": "docs/FRED.md", "BLS": "docs/BLS.md", "Census": "docs/CENSUS.md",
    "Treasury": "docs/TREASURY.md", "FEC": "docs/FEC.md", "Congress": "docs/CONGRESS.md",
    "FDA": "docs/FDA.md", "Clinical Trials": "docs/CLINICAL_TRIALS.md", "EIA": "docs/EIA.md",
    "FEMA": "docs/FEMA.md", "Federal Register": "docs/FEDERAL_REGISTER.md", "USAspending": "docs/USASPENDING.md",
    "EDGAR": "docs/EDGAR_API.md", "Nasdaq": "docs/NASDAQ_API.md", "yfinance": "docs/YFINANCE_API.md",
    "House Disclosures": "docs/HOUSE_FD_API.md", "JEFS": "docs/JEFS_API.md", "NARA": "docs/NARA_API.md",
    "NSArchive": "docs/NSARCHIVE_API.md", "Smithsonian": "docs/SMITHSONIAN_API.md",
    "Wilson Center": "docs/WILSON_DIGITAL_ARCHIVE_API.md",
    "arXiv": "docs/ARXIV_API.md", "Scholar": "docs/SCHOLAR_API.md",
}

# Literal search terms per source — the grep/recall index. Include the obvious
# words a user would search (e.g. "stocks", not only "equity") plus the names of
# the main datasets each source returns.
SOURCE_KEYWORDS = {
    "FRED": "economy, economic indicators, GDP, inflation, CPI, consumer prices, PCE, deflator, unemployment rate, interest rates, Fed funds rate, Treasury yields, 10-year yield, money supply, M1, M2, exchange rates, housing, industrial production, S&P 500, recession, macroeconomic, time series",
    "EDGAR": "SEC, public company, corporation, stock filings, 10-K, 10-Q, 8-K, annual report, quarterly report, financial statements, XBRL, revenue, earnings, net income, assets, liabilities, EPS, cash flow, CIK, ticker, full-text filing search, prospectus, IPO",
    "Nasdaq": "stocks, shares, equities, stock price, quote, ticker, symbol, market cap, sector, industry, P/E ratio, 52-week range, bid, ask, volume, dividends, OHLC, price history, real-time quote",
    "yfinance": "stocks, shares, equities, ticker, symbol, stock price, fundamentals, market cap, P/E, EPS, beta, profit margin, ROE, income statement, balance sheet, cash flow, financial statements, options, options chain, calls, puts, implied volatility, holders, ownership, institutional holders, analyst ratings, recommendations, price targets, dividends, earnings, news, OHLCV, history",
    "USAspending": "federal spending, government contracts, grants, awards, contractors, recipients, vendors, procurement, award amount, agency spending, defense spending, federal money, subawards",
    "Census": "demographics, population, household income, median income, ACS, American Community Survey, race, ethnicity, age, sex, gender, education, poverty, housing, rent, commute, employment, state, county, census tract",
    "BLS": "jobs, employment, unemployment rate, labor market, nonfarm payrolls, payroll, wages, earnings, hourly earnings, salary, CPI, inflation, consumer prices, PPI, producer prices, productivity, job openings, labor statistics",
    "Treasury": "national debt, public debt, debt to the penny, federal debt, deficit, Treasury, interest rates, yields, borrowing costs, exchange rates, fiscal data",
    "FEC": "campaign finance, elections, candidates, presidential candidates, donors, donations, contributions, PAC, super PAC, fundraising, money raised, receipts, disbursements, spending, election money",
    "Congress": "legislation, bills, laws, Congress, House, Senate, representatives, senators, members of Congress, votes, roll call, sponsors, cosponsors, committees",
    "FDA": "drugs, medications, adverse events, side effects, reactions, drug safety, drug recalls, food recalls, recalls, contamination, allergens, openFDA, FAERS, pharmaceuticals",
    "Clinical Trials": "clinical trials, medical trials, studies, drug trials, condition, disease, intervention, treatment, recruiting, NCT, research studies, sponsors",
    "EIA": "energy, gasoline prices, gas prices, fuel prices, oil, crude oil, petroleum, natural gas, electricity, power, generation, coal, renewables, solar, wind, emissions, CO2, energy consumption",
    "FEMA": "disasters, disaster declarations, hurricanes, floods, wildfires, fires, storms, earthquakes, emergencies, disaster relief, grants, assistance, flood insurance, NFIP, flood claims",
    "Federal Register": "regulations, rules, rulemaking, proposed rules, final rules, notices, executive orders, presidential documents, agencies, federal regulations",
    "House Disclosures": "congressional stock trades, stock trades, politician trading, House members, representatives, financial disclosures, holdings, periodic transaction reports, PTR, congressional trading",
    "JEFS": "federal judges, judicial, judges financial disclosures, judiciary, court, judge holdings, financial disclosure reports",
    "NARA": "National Archives, archives, historical records, government records, presidential libraries, primary sources, declassified, catalog, historical documents",
    "NSArchive": "declassified, national security, intelligence, CIA, foreign policy, Cold War, cables, memos, FOIA, classified documents, diplomacy",
    "Smithsonian": "museum, museums, art, artwork, paintings, artifacts, collections, history, science, specimens, photographs, images, cultural heritage, open access, objects",
    "Wilson Center": "Cold War, diplomacy, international relations, foreign policy, declassified documents, primary sources, history, digital archive, telegrams",
    "arXiv": "arxiv, preprints, scientific papers, research papers, academic papers, physics, math, computer science, machine learning, AI, quantitative biology, economics, statistics, scholarly articles, abstracts, PDF",
    "Scholar": "google scholar, citations, cited by, academic papers, scholarly papers, research papers, citation count, most cited, bibliometrics, literature search",
    "Cross-Reference": "company profile, politician profile, aggregate, combined, cross-reference, multi-source",
}

_HTTP_METHODS = ("get", "post", "put", "delete", "patch")


def _type(schema: dict) -> str:
    if not schema:
        return ""
    if "type" in schema:
        if schema["type"] == "array":
            item = (schema.get("items") or {}).get("type", "")
            return f"array[{item}]" if item else "array"
        return schema["type"]
    if "anyOf" in schema:
        types = [s.get("type") for s in schema["anyOf"] if s.get("type") and s.get("type") != "null"]
        return "|".join(dict.fromkeys(types))
    return ""


def _params(operation: dict) -> list[tuple[str, str]]:
    """Return [(name, "in, type, required|default X, max N"), ...]."""
    out: list[tuple[str, str]] = []
    for param in operation.get("parameters", []):
        schema = param.get("schema", {}) or {}
        bits = [param.get("in", "")]
        ptype = _type(schema)
        if ptype:
            bits.append(ptype)
        if param.get("required"):
            bits.append("required")
        elif schema.get("default", "") != "":
            bits.append(f"default {schema['default']}")
        if schema.get("maximum") is not None:
            bits.append(f"max {schema['maximum']}")
        out.append((param["name"], ", ".join(str(b) for b in bits)))
    return out


def _grouped() -> tuple[list[str], dict[str, str], dict[str, list[tuple[str, str, dict]]]]:
    schema = app.openapi()
    order = [tag["name"] for tag in schema.get("tags", [])]
    descriptions = {tag["name"]: tag.get("description", "") for tag in schema.get("tags", [])}
    grouped: dict[str, list[tuple[str, str, dict]]] = {}
    for path, operations in schema["paths"].items():
        for method, operation in operations.items():
            if method not in _HTTP_METHODS:
                continue
            tag = (operation.get("tags") or ["(untagged)"])[0]
            grouped.setdefault(tag, []).append((method.upper(), path, operation))
    return order, descriptions, grouped


def render_md() -> tuple[str, list[str]]:
    """Thin router: header + example + need->source index + a rich description per
    source (the recall layer) with its endpoint paths and detail-doc link. Per-endpoint
    params live in endpoints.csv; deep detail in each source's doc."""
    order, tag_desc, grouped = _grouped()
    missing: list[str] = []
    out = [
        HEADER, "", EXAMPLE, "", QUICK_INDEX, "",
        "## Sources",
        "",
        "A keyword-rich description per source, so you can tell at a glance whether a "
        "source has what you need. Endpoint **parameters** are in `docs/endpoints.csv` "
        "(flat, greppable); **deep detail and quirks** are in each source's linked doc. "
        "Load only the source(s) you need.",
        "",
    ]
    for tag in order:
        rows = grouped.get(tag)
        if not rows:
            continue
        desc = SOURCE_DESC.get(tag)
        if desc is None:
            missing.append(tag)
            desc = tag_desc.get(tag, "")
        paths = " · ".join(f"`{path}`" for _m, path, _op in sorted(rows, key=lambda r: r[1]))
        doc = SOURCE_DOC.get(tag, "")
        out += [f"### {tag}", "", desc, ""]
        out.append(f"- **Endpoints:** {paths}")
        out.append(
            f"- **Detail:** `{doc}` · **params:** `docs/endpoints.csv`"
            if doc else "- **params:** `docs/endpoints.csv`"
        )
        out.append("")
    out += [
        "## Also",
        "",
        "Researched but **not wired** (no endpoint yet): `docs/UNWIRED_RESEARCH.md` "
        "(SAM.gov, PatentsView) · `docs/SENATE_EFD_API.md` (Senate financial disclosures).",
        "",
    ]
    return "\n".join(out).rstrip() + "\n", missing


def write_csv(path: Path) -> int:
    order, _descriptions, grouped = _grouped()
    count = 0
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["source", "method", "path", "description", "params"])
        for tag in order:
            for method, route, op in sorted(grouped.get(tag, []), key=lambda row: row[1]):
                desc = DESCRIPTIONS.get(route, op.get("summary", ""))
                params = "; ".join(f"{n} ({m})" for n, m in _params(op))
                writer.writerow([tag, method, route, desc, params])
                count += 1
    return count


def main() -> None:
    docs = Path(__file__).parent.parent / "docs"
    markdown, missing = render_md()
    (docs / "API_GUIDE.md").write_text(markdown)
    rows = write_csv(docs / "endpoints.csv")
    print(f"wrote docs/API_GUIDE.md and docs/endpoints.csv ({rows} endpoints)")
    if missing:
        print(f"WARNING: {len(missing)} sources missing curated descriptions: {missing}")


if __name__ == "__main__":
    main()
