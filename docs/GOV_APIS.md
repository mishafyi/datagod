# Top 15 Free US Government APIs

> Tested and verified 2026-03-16. All endpoints confirmed working.

## Quick Reference

| # | API | Auth | Rate Limit | Base URL |
|---|-----|------|-----------|----------|
| 1 | FRED | Free key | 120/min | `api.stlouisfed.org` |
| 2 | EDGAR | User-Agent header | 10/sec | `data.sec.gov` |
| 3 | USAspending | None | 5/sec | `api.usaspending.gov` |
| 4 | Census | Free key (optional) | 500/day (no key) | `api.census.gov` |
| 5 | BLS | Free key (optional) | 25/day (no key), 500/day (key) | `api.bls.gov` |
| 6 | Treasury Fiscal Data | None | Unknown | `api.fiscaldata.treasury.gov` |
| 7 | FEC | Free key (DEMO_KEY works) | 1000/hr | `api.open.fec.gov` |
| 8 | Congress.gov | Free key (DEMO_KEY works) | 5000/hr | `api.congress.gov` |
| 9 | openFDA | None (key optional) | 240/min (no key), 120K/day (key) | `api.fda.gov` |
| 10 | ClinicalTrials.gov | None | Unknown | `clinicaltrials.gov/api/v2` |
| 11 | SAM.gov | Free key | Unknown | `api.sam.gov` |
| 12 | EIA | Free key (DEMO_KEY works) | Unknown | `api.eia.gov` |
| 13 | PatentsView | Free key | Unknown | `search.patentsview.org` |
| 14 | OpenFEMA | None | 1000/min | `fema.gov/api/open` |
| 15 | Federal Register | None | Unknown | `federalregister.gov/api/v1` |

---

## 1. FRED — Federal Reserve Economic Data

**What:** 800K+ economic time series — GDP, CPI, unemployment, interest rates, housing, money supply, and more. Aggregates data from BLS, Census, Treasury, Federal Reserve, and dozens of other sources.

**Auth:** Free API key from https://fred.stlouisfed.org/docs/api/api_key.html

**Endpoints:**

```bash
# Get series metadata
curl -s "https://api.stlouisfed.org/fred/series?series_id=GDP&api_key=YOUR_KEY&file_type=json"

# Get observations (actual data points)
curl -s "https://api.stlouisfed.org/fred/series/observations?series_id=GDP&api_key=YOUR_KEY&file_type=json"

# Search for series
curl -s "https://api.stlouisfed.org/fred/series/search?search_text=unemployment+rate&api_key=YOUR_KEY&file_type=json"

# Get categories
curl -s "https://api.stlouisfed.org/fred/category/children?category_id=0&api_key=YOUR_KEY&file_type=json"
```

**Key series IDs:**
| Series | Description |
|--------|-------------|
| `GDP` | Gross Domestic Product |
| `UNRATE` | Unemployment Rate |
| `CPIAUCSL` | Consumer Price Index |
| `FEDFUNDS` | Federal Funds Rate |
| `DGS10` | 10-Year Treasury Rate |
| `MORTGAGE30US` | 30-Year Mortgage Rate |
| `SP500` | S&P 500 Index |
| `M2SL` | M2 Money Stock |
| `TOTALSA` | Total Vehicle Sales |
| `HOUST` | Housing Starts |

**Response:**
```json
{
  "observations": [
    {"date": "2024-10-01", "value": "29719.405"}
  ]
}
```

---

## 2. EDGAR — SEC Corporate Filings

**What:** Every public company's structured financial data (XBRL), filing history, and metadata. 19,000+ companies.

**Auth:** `User-Agent: YourName your@email.com` header required

**Endpoints:**

```bash
# Company filing history + metadata
curl -s "https://data.sec.gov/submissions/CIK0000320193.json" \
  -H "User-Agent: Jack jack@gmail.com"

# All financial facts for a company
curl -s "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json" \
  -H "User-Agent: Jack jack@gmail.com"

# Single concept history (e.g., Apple's Revenue)
curl -s "https://data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/Revenues.json" \
  -H "User-Agent: Jack jack@gmail.com"

# Cross-company comparison (everyone's Revenue for 2023)
curl -s "https://data.sec.gov/api/xbrl/frames/us-gaap/Revenues/USD/CY2023.json" \
  -H "User-Agent: Jack jack@gmail.com"

# Full-text search inside filings
curl -s "https://efts.sec.gov/LATEST/search-index?q=%22artificial+intelligence%22&forms=10-K"

# Ticker to CIK lookup
curl -s "https://www.sec.gov/files/company_tickers.json" \
  -H "User-Agent: Jack jack@gmail.com"
```

**CIK format:** 10 digits, zero-padded (e.g., `CIK0000320193` = Apple/AAPL)

**Verified response (submissions):**
```json
{
  "cik": "0000320193",
  "name": "Apple Inc.",
  "tickers": ["AAPL"],
  "exchanges": ["Nasdaq"],
  "sic": "3571",
  "sicDescription": "Electronic Computers",
  "category": "Large accelerated filer",
  "fiscalYearEnd": "0926"
}
```

**See also:** [EDGAR_API.md](./EDGAR_API.md) for full documentation.

---

## 3. USAspending — Federal Spending

**What:** Every federal dollar spent — contracts, grants, loans, direct payments. $6T+/year. Searchable by agency, recipient, location, NAICS code.

**Auth:** None

**Endpoints:**

```bash
# Search spending by award (POST)
curl -s -X POST "https://api.usaspending.gov/api/v2/search/spending_by_award/" \
  -H "Content-Type: application/json" \
  -d '{
    "filters": {
      "keywords": ["artificial intelligence"],
      "time_period": [{"start_date": "2024-01-01", "end_date": "2024-12-31"}]
    },
    "fields": ["Award ID", "Recipient Name", "Award Amount", "Awarding Agency"],
    "limit": 10,
    "page": 1,
    "sort": "Award Amount",
    "order": "desc"
  }'

# Agency list
curl -s "https://api.usaspending.gov/api/v2/references/toptier_agencies/"

# Spending by agency
curl -s -X POST "https://api.usaspending.gov/api/v2/spending/" \
  -H "Content-Type: application/json" \
  -d '{"type": "agency", "filters": {"fy": "2024"}}'

# Recipient profile
curl -s "https://api.usaspending.gov/api/v2/recipient/duns/RECIPIENT_DUNS/"
```

**Note:** Most endpoints use POST with JSON body, not GET.

**Verified — sample response:**
```json
{
  "results": [
    {
      "Recipient Name": "DELL MARKETING L.P.",
      "Award Amount": 46068.29,
      "Awarding Agency": "DEPARTMENT OF DEFENSE"
    }
  ]
}
```

---

## 4. Census Bureau

**What:** Demographics for every geography in the US — population, income, education, housing, race, business patterns. Hundreds of datasets.

**Auth:** Free key (optional, higher limits) from https://api.census.gov/data/key_signup.html

**Endpoints:**

```bash
# Population by state (ACS 1-year)
curl -s "https://api.census.gov/data/2023/acs/acs1?get=NAME,B01001_001E&for=state:*"

# Median household income by state
curl -s "https://api.census.gov/data/2023/acs/acs1?get=NAME,B19013_001E&for=state:*"

# Population by county in California
curl -s "https://api.census.gov/data/2023/acs/acs1?get=NAME,B01001_001E&for=county:*&in=state:06"

# Business patterns by state (number of establishments)
curl -s "https://api.census.gov/data/2022/cbp?get=ESTAB,NAICS2017_LABEL&for=state:*&NAICS2017=54"

# Available datasets
curl -s "https://api.census.gov/data.json"
```

**Key variable prefixes (ACS):**
| Prefix | Topic |
|--------|-------|
| `B01` | Age and sex |
| `B02` | Race |
| `B03` | Hispanic origin |
| `B19` | Income |
| `B25` | Housing |
| `B15` | Education |
| `B23` | Employment |

**Verified response (population by state):**
```json
[
  ["NAME", "B01001_001E", "state"],
  ["Alabama", "5108468", "01"],
  ["Alaska", "733406", "02"],
  ["Arizona", "7431344", "04"]
]
```

---

## 5. BLS — Bureau of Labor Statistics

**What:** Employment, wages, CPI, PPI, occupational data. Source of the monthly jobs report and inflation numbers.

**Auth:** Free key (optional, higher limits) from https://data.bls.gov/registrationEngine/

**Endpoints:**

```bash
# Single series (unemployment rate)
curl -s "https://api.bls.gov/publicAPI/v2/timeseries/data/LNS14000000"

# Multiple series with date range (POST)
curl -s -X POST "https://api.bls.gov/publicAPI/v2/timeseries/data/" \
  -H "Content-Type: application/json" \
  -d '{"seriesid": ["LNS14000000", "CES0000000001"], "startyear": "2023", "endyear": "2024"}'
```

**Key series IDs:**
| Series | Description |
|--------|-------------|
| `LNS14000000` | Unemployment rate |
| `CES0000000001` | Total nonfarm employment |
| `CUUR0000SA0` | CPI-U (all items) |
| `WPUFD4` | PPI final demand |
| `CEU0500000003` | Average hourly earnings |

**Verified response:**
```json
{
  "status": "REQUEST_SUCCEEDED",
  "Results": {
    "series": [{
      "seriesID": "LNS14000000",
      "data": [
        {"year": "2026", "period": "M02", "periodName": "February", "value": "4.4"},
        {"year": "2026", "period": "M01", "periodName": "January", "value": "4.3"}
      ]
    }]
  }
}
```

---

## 6. Treasury Fiscal Data

**What:** National debt (to the penny), federal revenue, spending by category, interest rates, exchange rates, savings bonds.

**Auth:** None

**Endpoints:**

```bash
# National debt (latest)
curl -s "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny?sort=-record_date&page[size]=3"

# Federal revenue
curl -s "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/revenue/rcm?sort=-record_date&page[size]=5"

# Treasury interest rates
curl -s "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/avg_interest_rates?sort=-record_date&page[size]=5"

# Exchange rates
curl -s "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/rates_of_exchange?sort=-record_date&page[size]=5"

# Available datasets
curl -s "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/"
```

**Supports:** filtering (`?filter=`), sorting (`?sort=`), pagination (`?page[size]=`), field selection (`?fields=`)

**Verified response:**
```json
{
  "data": [{
    "record_date": "2026-03-13",
    "tot_pub_debt_out_amt": "38902637810572.47",
    "debt_held_public_amt": "31298590850025.98",
    "intragov_hold_amt": "7604046960546.49"
  }]
}
```

---

## 7. FEC — Federal Election Commission

**What:** Every political donation and expenditure in federal elections. Candidates, committees, donors, disbursements.

**Auth:** Free key from https://api.open.fec.gov/developers/ (DEMO_KEY works for testing)

**Endpoints:**

```bash
# Presidential candidates
curl -s "https://api.open.fec.gov/v1/candidates/?api_key=DEMO_KEY&office=P&per_page=5"

# Search individual contributions
curl -s "https://api.open.fec.gov/v1/schedules/schedule_a/?api_key=DEMO_KEY&contributor_name=smith&per_page=5"

# Committee details
curl -s "https://api.open.fec.gov/v1/committees/?api_key=DEMO_KEY&q=actblue&per_page=5"

# Candidate financial totals
curl -s "https://api.open.fec.gov/v1/candidates/totals/?api_key=DEMO_KEY&office=P&election_year=2024&sort=-receipts&per_page=10"

# Independent expenditures
curl -s "https://api.open.fec.gov/v1/schedules/schedule_e/?api_key=DEMO_KEY&per_page=5"
```

**Verified — returns 6,744 presidential candidates with party, state, election year.**

---

## 8. Congress.gov

**What:** Every bill, vote, member, committee, amendment, treaty, and congressional record entry.

**Auth:** Free key from https://api.congress.gov/sign-up/ (DEMO_KEY works for testing)

**Endpoints:**

```bash
# Recent bills
curl -s "https://api.congress.gov/v3/bill?api_key=DEMO_KEY&limit=5&format=json"

# Specific bill
curl -s "https://api.congress.gov/v3/bill/118/hr/1?api_key=DEMO_KEY&format=json"

# Members of Congress
curl -s "https://api.congress.gov/v3/member?api_key=DEMO_KEY&limit=5&format=json"

# Recent votes
curl -s "https://api.congress.gov/v3/house/vote?api_key=DEMO_KEY&limit=5&format=json"

# Committee list
curl -s "https://api.congress.gov/v3/committee?api_key=DEMO_KEY&limit=5&format=json"
```

**Verified — returns bills with title, type, chamber, latest action.**

---

## 9. openFDA

**What:** Drug adverse events (20M+ reports), drug labeling, device recalls, food enforcement actions.

**Auth:** None (API key optional for higher rate limits)

**Endpoints:**

```bash
# Drug adverse events
curl -s "https://api.fda.gov/drug/event.json?limit=3"

# Search adverse events for a specific drug
curl -s "https://api.fda.gov/drug/event.json?search=patient.drug.openfda.brand_name:aspirin&limit=3"

# Drug recalls
curl -s "https://api.fda.gov/drug/enforcement.json?limit=3"

# Device adverse events
curl -s "https://api.fda.gov/device/event.json?limit=3"

# Food recalls
curl -s "https://api.fda.gov/food/enforcement.json?limit=3"

# Count adverse events by reaction
curl -s "https://api.fda.gov/drug/event.json?count=patient.reaction.reactionmeddrapt.exact"
```

**Supports:** `search=`, `count=`, `limit=`, `skip=`

**Verified — returns adverse event reports with patient info, drugs, reactions.**

---

## 10. ClinicalTrials.gov

**What:** 500K+ clinical trials worldwide. Protocols, enrollment, conditions, interventions, results.

**Auth:** None

**Endpoints:**

```bash
# Recent studies
curl -s "https://clinicaltrials.gov/api/v2/studies?pageSize=3"

# Search by condition
curl -s "https://clinicaltrials.gov/api/v2/studies?query.cond=cancer&pageSize=5"

# Search by intervention (drug name)
curl -s "https://clinicaltrials.gov/api/v2/studies?query.intr=pembrolizumab&pageSize=5"

# Specific study
curl -s "https://clinicaltrials.gov/api/v2/studies/NCT06472635"

# Filter by status
curl -s "https://clinicaltrials.gov/api/v2/studies?filter.overallStatus=RECRUITING&pageSize=5"

# Available field values
curl -s "https://clinicaltrials.gov/api/v2/stats/fieldValues/StudyType"
```

**Verified — returns study ID, title, status, conditions, phases.**

---

## 11. SAM.gov — System for Award Management

**What:** Federal contracting opportunities (RFPs/bids), entity registrations, wage determinations, exclusions.

**Auth:** Free key from https://sam.gov/content/entity-information (DEMO_KEY does NOT work)

**Endpoints:**

```bash
# Search contracting opportunities
curl -s "https://api.sam.gov/opportunities/v2/search?api_key=YOUR_KEY&limit=5&postedFrom=01/01/2026&postedTo=03/16/2026"

# Entity (company) information
curl -s "https://api.sam.gov/entity-information/v3/entities?api_key=YOUR_KEY&ueiSAM=ENTITY_UEI"

# Exclusions (debarred entities)
curl -s "https://api.sam.gov/entity-information/v3/exclusions?api_key=YOUR_KEY&limit=5"

# Wage determinations
curl -s "https://api.sam.gov/wage-determination/v1/sca?api_key=YOUR_KEY"
```

---

## 12. EIA — Energy Information Administration

**What:** Energy production, consumption, prices, forecasts. Oil, gas, coal, renewables, electricity, nuclear — by state, country, sector.

**Auth:** Free key from https://www.eia.gov/opendata/register.php (DEMO_KEY works for testing)

**Endpoints:**

```bash
# API route catalog (lists all 14 datasets)
curl -s "https://api.eia.gov/v2/?api_key=DEMO_KEY"

# Electricity data
curl -s "https://api.eia.gov/v2/electricity/retail-sales?api_key=DEMO_KEY&frequency=annual&data[0]=revenue&sort[0][column]=period&sort[0][direction]=desc&length=5"

# Petroleum prices
curl -s "https://api.eia.gov/v2/petroleum/pri/gnd?api_key=DEMO_KEY&frequency=weekly&data[0]=value&length=5"

# Natural gas
curl -s "https://api.eia.gov/v2/natural-gas/sum/lsum?api_key=DEMO_KEY&frequency=annual&data[0]=value&length=5"

# CO2 emissions
curl -s "https://api.eia.gov/v2/co2-emissions/co2-emissions-aggregates?api_key=DEMO_KEY&frequency=annual&data[0]=value&length=5"
```

**Verified — 14 datasets:** coal, crude-oil-imports, electricity, international, natural-gas, nuclear-outages, petroleum, seds, steo, densified-biomass, total-energy, aeo, ieo, co2-emissions.

---

## 13. PatentsView — USPTO Patent Analytics

**What:** Patent data — inventors, assignees, citations, classifications, claims. Searchable and filterable.

**Auth:** Free key from https://patentsview.org/apis/purpose

**Endpoints:**

```bash
# Search patents (new v1 API)
curl -s "https://search.patentsview.org/api/v1/patent/?q={\"_gte\":{\"patent_date\":\"2024-01-01\"}}&f=patent_id,patent_title,patent_date&per_page=5" \
  -H "X-Api-Key: YOUR_KEY"

# Search by assignee (company)
curl -s "https://search.patentsview.org/api/v1/patent/?q={\"assignee_organization\":\"Apple Inc.\"}&f=patent_id,patent_title,patent_date&per_page=5" \
  -H "X-Api-Key: YOUR_KEY"

# Inventor search
curl -s "https://search.patentsview.org/api/v1/inventor/?q={\"inventor_last_name\":\"Musk\"}&f=inventor_first_name,inventor_last_name&per_page=5" \
  -H "X-Api-Key: YOUR_KEY"
```

**Note:** Legacy `api.patentsview.org` POST endpoint is discontinued (returns 410). Use new `search.patentsview.org/api/v1/` with API key.

---

## 14. OpenFEMA — Disaster Data

**What:** Every disaster declaration since 1953, assistance payments, NFIP flood claims, hazard mitigation grants.

**Auth:** None

**Endpoints:**

```bash
# Recent disaster declarations
curl -s "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries?\$top=5&\$orderby=declarationDate%20desc"

# FEMA grants by state
curl -s "https://www.fema.gov/api/open/v2/HazardMitigationGrants?\$top=5"

# Public assistance funded projects
curl -s "https://www.fema.gov/api/open/v2/PublicAssistanceFundedProjectsDetails?\$top=5"

# NFIP flood claims
curl -s "https://www.fema.gov/api/open/v2/FimaNfipClaims?\$top=5"

# Available datasets
curl -s "https://www.fema.gov/api/open/v2/"
```

**Supports OData:** `$top`, `$skip`, `$filter`, `$orderby`, `$select`

**Verified response:**
```json
{
  "DisasterDeclarationsSummaries": [{
    "disasterNumber": 3643,
    "declarationTitle": "SEWER LINE COLLAPSE",
    "declarationDate": "2026-02-20T00:00:00.000Z",
    "state": "PA"
  }]
}
```

---

## 15. Federal Register

**What:** Every proposed rule, final rule, executive order, and agency notice published by the federal government. Real-time.

**Auth:** None

**Endpoints:**

```bash
# Recent documents
curl -s "https://www.federalregister.gov/api/v1/documents.json?per_page=5&order=newest"

# Search by keyword
curl -s "https://www.federalregister.gov/api/v1/documents.json?conditions[term]=artificial+intelligence&per_page=5"

# Filter by type (Rule, Proposed Rule, Notice, Presidential Document)
curl -s "https://www.federalregister.gov/api/v1/documents.json?conditions[type][]=RULE&per_page=5"

# Filter by agency
curl -s "https://www.federalregister.gov/api/v1/documents.json?conditions[agencies][]=environmental-protection-agency&per_page=5"

# Specific document
curl -s "https://www.federalregister.gov/api/v1/documents/2026-05242.json"

# Public inspection documents (not yet published)
curl -s "https://www.federalregister.gov/api/v1/public-inspection-documents/current.json"
```

**Verified — returns ~10,000 documents with title, type, agency, publication date, abstract.**

---

## API Keys Cheat Sheet

| API | Where to get key | Time to get |
|-----|-----------------|-------------|
| FRED | https://fred.stlouisfed.org/docs/api/api_key.html | Instant |
| Census | https://api.census.gov/data/key_signup.html | Instant |
| BLS | https://data.bls.gov/registrationEngine/ | Instant |
| FEC | https://api.open.fec.gov/developers/ | Instant |
| Congress.gov | https://api.congress.gov/sign-up/ | Instant |
| EIA | https://www.eia.gov/opendata/register.php | Instant |
| SAM.gov | https://sam.gov/content/entity-information | ~24 hours |
| PatentsView | https://patentsview.org/apis/purpose | Instant |
| data.gov universal | https://api.data.gov/signup/ | Instant |

**Tip:** The `api.data.gov` key works across FEC, Congress.gov, EIA, College Scorecard, and several other APIs that route through the GSA gateway.

---

*All endpoints tested 2026-03-16. 12 of 15 work with no key or DEMO_KEY. 3 require free registration (FRED, SAM.gov, PatentsView).*
