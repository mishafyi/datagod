---
name: edgar
description: "SEC filings and financials for public companies and corporations — 10-K, 10-Q, 8-K annual and quarterly reports, full XBRL financial statements (revenue, earnings, net income, assets, liabilities, EPS, cash flow), one-metric-across-all-companies comparisons, and full-text search inside filings (by CIK or ticker). Use for any public-company financial data, SEC disclosures, or 'which companies mention X'."
keywords: "SEC, public company, corporation, stock filings, 10-K, 10-Q, 8-K, annual report, quarterly report, financial statements, XBRL, revenue, earnings, net income, assets, liabilities, EPS, cash flow, CIK, ticker, full-text filing search, prospectus, IPO"
routes: "/edgar/company/{cik}, /edgar/concept/{cik}/{concept}, /edgar/financials/{cik}, /edgar/frames/{concept}, /edgar/search"
---

# SEC EDGAR API Reference

## Overview

The SEC provides free, public APIs to access all structured data from EDGAR (Electronic Data Gathering, Analysis, and Retrieval). No API key required — just a `User-Agent` header with your name and email.

**Base URLs:**
- `https://data.sec.gov` — structured XBRL data + submissions
- `https://efts.sec.gov` — full-text search of filing documents

**Rate limit:** 10 requests/second
**Auth:** None — just set `User-Agent: YourName your@email.com`
**Update frequency:** Submissions < 1 second, XBRL < 1 minute after filing

---

## APIs

### 1. Submissions API

Returns company metadata and complete filing history.

**Endpoint:**
```
GET https://data.sec.gov/submissions/CIK{number}.json
```

**CIK format:** 10 digits, zero-padded (e.g., `CIK0000320193` for Apple)

**Example:**
```bash
curl -s "https://data.sec.gov/submissions/CIK0000320193.json" \
  -H "User-Agent: Jack jack@gmail.com"
```

**Response structure:**
```json
{
  "cik": "0000320193",
  "entityType": "operating",
  "sic": "3571",
  "sicDescription": "Electronic Computers",
  "name": "Apple Inc.",
  "tickers": ["AAPL"],
  "exchanges": ["Nasdaq"],
  "ein": "942404110",
  "category": "Large accelerated filer",
  "fiscalYearEnd": "0926",
  "stateOfIncorporation": "CA",
  "addresses": {
    "mailing": { "street1": "...", "city": "...", "stateOrCountry": "...", "zipCode": "..." },
    "business": { "street1": "...", "city": "...", "stateOrCountry": "...", "zipCode": "..." }
  },
  "phone": "...",
  "formerNames": [],
  "filings": {
    "recent": {
      "accessionNumber": ["0000320193-24-000123", ...],
      "filingDate": ["2024-11-01", ...],
      "reportDate": ["2024-09-28", ...],
      "form": ["10-K", ...],
      "primaryDocument": ["aapl-20240928.htm", ...],
      "primaryDocDescription": ["10-K", ...],
      "acceptanceDateTime": ["2024-11-01T06:01:36.000Z", ...],
      "act": ["34", ...],
      "fileNumber": ["001-36743", ...],
      "size": [14520363, ...],
      "isXBRL": [1, ...],
      "isInlineXBRL": [1, ...]
    },
    "files": [
      {
        "name": "CIK0000320193-submissions-001.json",
        "filingCount": 1000,
        "filingFrom": "2005-01-03",
        "filingTo": "2015-07-22"
      }
    ]
  }
}
```

**Key fields:**
| Field | Description |
|-------|-------------|
| `cik` | Central Index Key — unique SEC identifier |
| `tickers` | Stock ticker symbols |
| `sic` | Standard Industrial Classification code |
| `fiscalYearEnd` | MMDD format (e.g., "0926" = Sept 26) |
| `filings.recent` | Last 1000 filings (parallel arrays) |
| `filings.files` | Overflow JSON files for companies with 1000+ filings |

**Overflow files:** For companies with 1000+ filings, older filings are in separate files:
```
GET https://data.sec.gov/submissions/CIK0000320193-submissions-001.json
```

---

### 2. Company Facts API

Returns every XBRL-tagged financial fact ever reported by a company.

**Endpoint:**
```
GET https://data.sec.gov/api/xbrl/companyfacts/CIK{number}.json
```

**Example:**
```bash
curl -s "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json" \
  -H "User-Agent: Jack jack@gmail.com"
```

**Response structure:**
```json
{
  "cik": 320193,
  "entityName": "Apple Inc.",
  "facts": {
    "dei": {
      "EntityCommonStockSharesOutstanding": {
        "label": "Entity Common Stock, Shares Outstanding",
        "description": "...",
        "units": {
          "shares": [
            {
              "end": "2024-09-28",
              "val": 15115823000,
              "accn": "0000320193-24-000123",
              "fy": 2024,
              "fp": "FY",
              "form": "10-K",
              "filed": "2024-11-01",
              "frame": "CY2024Q3I"
            }
          ]
        }
      }
    },
    "us-gaap": {
      "Revenues": {
        "label": "Revenues",
        "description": "...",
        "units": {
          "USD": [
            {
              "end": "2024-09-28",
              "val": 391035000000,
              "accn": "0000320193-24-000123",
              "fy": 2024,
              "fp": "FY",
              "form": "10-K",
              "filed": "2024-11-01",
              "frame": "CY2023Q4"
            }
          ]
        }
      }
    }
  }
}
```

**Taxonomies:**
| Taxonomy | What it contains |
|----------|-----------------|
| `dei` | Document and Entity Information (shares outstanding, public float) |
| `us-gaap` | All US GAAP financial concepts (revenue, assets, liabilities, etc.) |
| `ifrs-full` | IFRS concepts (for foreign filers) |
| `srt` | SEC Reporting Taxonomy |

**Data point fields:**
| Field | Description |
|-------|-------------|
| `end` | Period end date |
| `val` | The reported value |
| `accn` | Accession number (links to the specific filing) |
| `fy` | Fiscal year |
| `fp` | Fiscal period: `FY`, `Q1`, `Q2`, `Q3`, `Q4` |
| `form` | Filing type: `10-K`, `10-Q`, `8-K`, etc. |
| `filed` | Date the filing was submitted to SEC |
| `frame` | Calendar frame (e.g., `CY2024Q3I`) |

**Frame format:** `CY{year}Q{quarter}{I}`
- `CY2023` = calendar year 2023 (duration/full year)
- `CY2023Q1` = Q1 2023 duration (income statement items)
- `CY2023Q1I` = Q1 2023 instant (balance sheet items)
- The `I` suffix = point-in-time value; no `I` = period value

---

### 3. Company Concept API

Returns the full history of a single XBRL concept for one company.

**Endpoint:**
```
GET https://data.sec.gov/api/xbrl/companyconcept/CIK{number}/{taxonomy}/{concept}.json
```

**Example — Apple's Revenue history:**
```bash
curl -s "https://data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/Revenues.json" \
  -H "User-Agent: Jack jack@gmail.com"
```

**Response:** Same structure as a single concept from Company Facts — all data points with units.

**Common concepts:**
| Concept | What it is |
|---------|-----------|
| `Revenues` | Total revenue |
| `NetIncomeLoss` | Net income |
| `Assets` | Total assets |
| `Liabilities` | Total liabilities |
| `StockholdersEquity` | Shareholders' equity |
| `EarningsPerShareBasic` | Basic EPS |
| `EarningsPerShareDiluted` | Diluted EPS |
| `OperatingIncomeLoss` | Operating income |
| `CashAndCashEquivalentsAtCarryingValue` | Cash on hand |
| `LongTermDebt` | Long-term debt |
| `CommonStockSharesOutstanding` | Shares outstanding |
| `AccountsPayableCurrent` | Current accounts payable |
| `AccountsReceivableNetCurrent` | Current accounts receivable |
| `ResearchAndDevelopmentExpense` | R&D expense |

Full list: https://xbrl.fasb.org/us-gaap/

---

### 4. Frames API

Returns a single XBRL concept value for ALL companies in a given period. This is the cross-company comparison endpoint.

**Endpoint:**
```
GET https://data.sec.gov/api/xbrl/frames/{taxonomy}/{concept}/{unit}/{period}.json
```

**Example — Every company's Revenue for CY2023:**
```bash
curl -s "https://data.sec.gov/api/xbrl/frames/us-gaap/Revenues/USD/CY2023.json" \
  -H "User-Agent: Jack jack@gmail.com"
```

**Response structure:**
```json
{
  "taxonomy": "us-gaap",
  "tag": "Revenues",
  "ccp": "CY2023",
  "uom": "USD",
  "label": "Revenues",
  "description": "...",
  "pts": 2631,
  "data": [
    {
      "accn": "0000104169-24-000012",
      "cik": 104169,
      "entityName": "Walmart Inc.",
      "loc": "US-AR",
      "end": "2024-01-31",
      "val": 648125000000
    }
  ]
}
```

**Period format examples:**
| Period | Meaning |
|--------|---------|
| `CY2023` | Calendar year 2023 (duration — use for income statement items) |
| `CY2023Q1` | Q1 2023 duration |
| `CY2023Q3I` | Q3 2023 instant (use for balance sheet items) |

**Unit options:** `USD`, `shares`, `pure` (ratios), `USD-per-shares` (EPS)

**More examples:**
```bash
# All companies' total assets (balance sheet = instant, so use I suffix)
curl -s "https://data.sec.gov/api/xbrl/frames/us-gaap/Assets/USD/CY2023Q4I.json" \
  -H "User-Agent: Jack jack@gmail.com"

# All companies' EPS
curl -s "https://data.sec.gov/api/xbrl/frames/us-gaap/EarningsPerShareBasic/USD-per-shares/CY2023.json" \
  -H "User-Agent: Jack jack@gmail.com"

# All companies' shares outstanding
curl -s "https://data.sec.gov/api/xbrl/frames/us-gaap/CommonStockSharesOutstanding/shares/CY2023Q4I.json" \
  -H "User-Agent: Jack jack@gmail.com"
```

---

### 5. Full-Text Search API

Searches inside the actual filing documents (the text of 10-Ks, 10-Qs, etc.).

**Endpoint:**
```
GET https://efts.sec.gov/LATEST/search-index?q={query}&forms={form_types}
```

**Example — Find 10-K filings mentioning "artificial intelligence":**
```bash
curl -s "https://efts.sec.gov/LATEST/search-index?q=%22artificial+intelligence%22&forms=10-K" \
  -H "User-Agent: Jack jack@gmail.com"
```

**Parameters:**
| Parameter | Description | Example |
|-----------|-------------|---------|
| `q` | Search query (supports quotes for exact match) | `"artificial intelligence"` |
| `forms` | Comma-separated form types | `10-K,10-Q,8-K` |
| `dateRange` | `custom` for date filtering | `custom` |
| `startdt` | Start date (with dateRange=custom) | `2024-01-01` |
| `enddt` | End date (with dateRange=custom) | `2025-01-01` |
| `from` | Pagination offset | `0` |
| `size` | Results per page | `50` |

**Response structure:**
```json
{
  "hits": {
    "total": { "value": 2436 },
    "hits": [
      {
        "_source": {
          "ciks": ["0001498148"],
          "display_names": ["Artificial Intelligence Technology Solutions Inc. (AITX)"],
          "root_forms": ["10-K"],
          "form": "10-K/A",
          "file_date": "2024-05-29",
          "adsh": "0001493152-24-021767",
          "biz_locations": ["Ferndale, MI"],
          "sics": ["7372"]
        }
      }
    ]
  }
}
```

---

## Accessing Raw Filing Documents

Once you have an accession number from any API, you can download the actual filing:

```
https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number_with_dashes}/{primary_document}
```

**Example — Apple's 10-K:**
```
https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm
```

The `primaryDocument` field from the Submissions API gives you the filename.

---

## Bulk Data Downloads

For offline analysis — same data as the APIs, recompiled nightly:

| File | URL | Size | Contents |
|------|-----|------|----------|
| `companyfacts.zip` | `https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip` | ~1.3 GB | All XBRL data for all companies |
| `submissions.zip` | `https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip` | ~1.4 GB | Filing history + metadata for all filers |

---

## CIK Lookup

To find a company's CIK from its ticker:

```bash
curl -s "https://www.sec.gov/cgi-bin/browse-edgar?company=&CIK=AAPL&type=&dateb=&owner=include&count=10&search_text=&action=getcompany" \
  -H "User-Agent: Jack jack@gmail.com"
```

Or use the bulk ticker-to-CIK mapping:
```bash
curl -s "https://www.sec.gov/files/company_tickers.json" \
  -H "User-Agent: Jack jack@gmail.com"
```

This returns all tickers mapped to CIK numbers.

---

## Key Relationships

```
Submissions API ──────────── accessionNumber ──────────── Company Facts API
  (who filed what, when)          │                      (what numbers were reported)
                                  │
                                  ▼
                         Raw Filing Document
                    (the actual 10-K/10-Q HTML/PDF)
                                  │
                                  ▼
                       Full-Text Search API
                    (search inside those documents)

Frames API = Company Facts aggregated across ALL companies for one concept + period
```

- `accessionNumber` (submissions) = `accn` (companyfacts) — the join key
- `cik` is the universal company identifier across all APIs
- `tickers` → `cik` mapping available at `/files/company_tickers.json`

---

*Researched 2026-03-16. Source: https://www.sec.gov/search-filings/edgar-application-programming-interfaces*
