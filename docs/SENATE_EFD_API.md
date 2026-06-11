---
name: senate-efd
description: "Senate Electronic Financial Disclosures (EFD) — senators' financial disclosure reports and stock trades. Researched (undocumented, session-based) but NOT yet wired into DataGod."
keywords: "Senate, senators, financial disclosures, stock trades, EFD, periodic transaction reports, holdings, congressional trading, not wired"
routes: "(none — researched, not wired)"
---

# Senate EFD (Electronic Financial Disclosures) — Undocumented API

> Discovered via Chrome DevTools inspection, 2026-03-16
> Base URL: `https://efdsearch.senate.gov`

## Overview

The Senate Electronic Financial Disclosure system provides online access to financial disclosure reports filed by Senators, former Senators, and candidates since January 1, 2012. Behind the web UI is a **Django/gunicorn** app with a **DataTables server-side JSON API** at `/search/report/data/`.

**Total records:** 5,351 (all report types combined, as of 2026-03-16)

---

## Authentication Flow

The API requires a session established through a two-step process:

### Step 1: Get CSRF token
```bash
# GET the search page — sets csrftoken cookie
curl -c cookies.txt -s "https://efdsearch.senate.gov/search/"
```

### Step 2: Submit search form (establishes session + agreement)
```bash
# POST the form — sets sessionid cookie
# Must include report_type and csrfmiddlewaretoken
curl -b cookies.txt -c cookies.txt \
  -X POST "https://efdsearch.senate.gov/search/" \
  -H "Referer: https://efdsearch.senate.gov/search/" \
  -d "csrfmiddlewaretoken=$(grep csrftoken cookies.txt | awk '{print $NF}')&report_type=11&submitted_start_date=&submitted_end_date=&first_name=&last_name="
```

After Step 2, the `sessionid` cookie is set and the data API becomes accessible.

### Required cookies
| Cookie | Purpose | Set by |
|--------|---------|--------|
| `csrftoken` | CSRF protection | GET /search/ |
| `sessionid` | Session + agreement state | POST /search/ |

### Required headers for API calls
```
X-CSRFToken: {csrftoken value}
X-Requested-With: XMLHttpRequest
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
Referer: https://efdsearch.senate.gov/search/
```

---

## API Endpoint: Search Reports

```
POST https://efdsearch.senate.gov/search/report/data/
```

Returns JSON. Uses jQuery DataTables server-side protocol.

### Parameters (form-encoded)

**Search filters:**

| Parameter | Type | Values | Description |
|-----------|------|--------|-------------|
| `report_types` | JSON array string | `[7]`, `[11]`, `[7, 11, 10, 14, 15]` | Report type IDs (see below) |
| `filer_types` | JSON array string | `[1]`, `[4]`, `[5]`, `[]` | Filer type IDs (see below) |
| `first_name` | string | `""` | Filter by first name |
| `last_name` | string | `""` | Filter by last name |
| `senator_state` | string | `""` or state name | Filter senators by state |
| `candidate_state` | string | `""` or state name | Filter candidates by state |
| `office_id` | string | `""` | Office ID filter |
| `submitted_start_date` | string | `"01/01/2024 00:00:00"` | Start date |
| `submitted_end_date` | string | `""` | End date (empty = now) |

**DataTables pagination/sorting:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `start` | int | Pagination offset (0-based) |
| `length` | int | Page size (25, 50, 75, 100) |
| `draw` | int | DataTables draw counter (increment each call) |
| `order[0][column]` | int | Sort column index (0-4) |
| `order[0][dir]` | string | `asc` or `desc` |
| `search[value]` | string | Client-side filter text |
| `columns[N][data]` | int | Column definitions (required by DataTables) |

### Report Type IDs

| ID | Type | Total Records | Description |
|----|------|:------------:|-------------|
| `7` | Annual | ~1,800 | Annual financial disclosure reports |
| `11` | Periodic Transactions | ~2,370 | Stock trade reports (PTRs) |
| `10` | Due Date Extension | ~700 | Extension requests |
| `14` | Blind Trusts | ~50 | Blind trust reports |
| `15` | Other Documents | ~400 | Miscellaneous documents |

**Combined total: 5,351** (some overlap possible)

### Filer Type IDs

| ID | Type |
|----|------|
| `1` | Senator |
| `4` | Candidate |
| `5` | Former Senator |

### Response

```json
{
  "draw": 1,
  "recordsTotal": 5351,
  "recordsFiltered": 5351,
  "result": "ok",
  "data": [
    [
      "James",                           // [0] First name
      "Banks",                           // [1] Last name
      "Banks, James E. (Senator)",       // [2] Display name (office + filer type)
      "<a href=\"/search/view/ptr/{uuid}/\">Periodic Transaction Report for 08/10/2025</a>",  // [3] Link HTML
      "08/10/2025"                       // [4] Date filed
    ]
  ]
}
```

### Response columns
| Index | Field | Description |
|:-----:|-------|-------------|
| 0 | First name | Senator/candidate first name |
| 1 | Last name | Last name |
| 2 | Display name | Full name with office and filer type |
| 3 | Report link | HTML anchor with UUID link to report detail |
| 4 | Date filed | MM/DD/YYYY format |

### Report detail URL patterns (extracted from link HTML)

| Report Type | URL Pattern |
|-------------|-------------|
| Periodic Transaction Report | `/search/view/ptr/{uuid}/` |
| Annual Report | `/search/view/annual/{uuid}/` |
| Due Date Extension | `/search/view/extension-notice/regular/{uuid}/` |
| Candidate Report | `/search/view/annual/{uuid}/` |
| Termination Report | `/search/view/annual/{uuid}/` |

---

## Report Detail Pages

Each report has a detail page at `https://efdsearch.senate.gov/search/view/{type}/{uuid}/`. These are HTML pages (not JSON), but they contain structured data in tables.

### Periodic Transaction Report (PTR) — Stock Trades

**URL:** `https://efdsearch.senate.gov/search/view/ptr/{uuid}/`

**Example:** Senator James Banks — PTR for 08/10/2025
```
https://efdsearch.senate.gov/search/view/ptr/743c6542-9aec-48ae-8fa6-62645757bc8f/
```

**Verified data structure:**

| Field | Example | Description |
|-------|---------|-------------|
| Transaction Date | `08/04/2025` | Date of the trade |
| Owner | `Self` | Self, Spouse, Joint, Dependent Child |
| Ticker | `--` or ticker symbol | Stock ticker (sometimes missing) |
| Asset Name | `starbuck` | Name of the asset |
| Asset Type | `Stock` | Stock, Bond, Option, etc. |
| Type | `Purchase` | Purchase, Sale, Sale (Full), Sale (Partial), Exchange |
| Amount | `$1,001 - $15,000` | Value range of transaction |
| Comment | `--` | Optional comment |

**Transaction summary header shows:**
- Total transaction count
- Breakdown by owner: Self, Joint, Spouse, Dependent Child

### Annual Report — Full Financial Disclosure

**URL:** `https://efdsearch.senate.gov/search/view/annual/{uuid}/`

**Contains 10+ sections:**

| Part | Section | Data |
|------|---------|------|
| 1 | Honoraria Payments | Who was paid, type, who paid, amount |
| 2 | Earned & Non-Investment Income | Source, type, amount |
| 3 | **Assets** | Asset name, type, owner, value range, income type, income range |
| 4a | PTR Summary | Summary of periodic transaction reports |
| 4b | **Transactions** | Date, owner, ticker, asset, buy/sell, amount |
| 5 | Gifts | Source, description, value |
| 6 | Travel | Dates, destination, purpose, sponsor |
| 7 | **Liabilities** | Debtor, type, rate, amount, creditor |
| 8 | **Positions** | Position held, entity, entity type, dates |
| 9 | Agreements | Parties, type, status, terms |
| 10 | Compensation | Source, type, amount |

**Example data from Part 3 (Assets):**
```
Asset: First Tennessee (Knoxville, Tennessee) Type: Checking, Savings
Type: Bank Deposit
Owner: Self
Value: $250,001 - $500,000
Income Type: Interest
Income: $1,001 - $2,500
```

**Example data from Part 4b (Transactions):**
```
Owner: Spouse
Ticker: VFINX
Asset: Vanguard 500 Index Investor
Type: Purchase
Date: 02/26/2016
Amount: $1,001 - $15,000
```

---

## Tested API Calls

### Search for all Periodic Transaction Reports
```bash
# After establishing session (Steps 1 & 2 above):
curl -b cookies.txt \
  -X POST "https://efdsearch.senate.gov/search/report/data/" \
  -H "X-CSRFToken: $(grep csrftoken cookies.txt | awk '{print $NF}')" \
  -H "X-Requested-With: XMLHttpRequest" \
  -H "Referer: https://efdsearch.senate.gov/search/" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "draw=1&start=0&length=25&report_types=[11]&filer_types=[]&submitted_start_date=&submitted_end_date=&candidate_state=&senator_state=&office_id=&first_name=&last_name=&order[0][column]=1&order[0][dir]=asc&columns[0][data]=0&columns[1][data]=1&columns[2][data]=2&columns[3][data]=3&columns[4][data]=4"
```
**Result:** 200 OK — 2,370 records

### Search for all report types
```bash
# Same as above but with all report types:
-d "...&report_types=[7, 11, 10, 14, 15]&..."
```
**Result:** 200 OK — 5,351 records

### Search by senator name
```bash
-d "...&report_types=[11]&first_name=&last_name=Banks&..."
```

### Search by state
```bash
-d "...&report_types=[11]&senator_state=Texas&..."
```

### Search by date range
```bash
-d "...&report_types=[11]&submitted_start_date=01/01/2025 00:00:00&submitted_end_date=03/16/2026 00:00:00&..."
```

### Paginate through all results
```bash
# Page 1: start=0&length=100
# Page 2: start=100&length=100
# Page 3: start=200&length=100
# ...until start >= recordsTotal
```

### Fetch PTR detail page (stock trades)
```bash
curl -b cookies.txt "https://efdsearch.senate.gov/search/view/ptr/743c6542-9aec-48ae-8fa6-62645757bc8f/"
```
**Result:** 200 OK — HTML page with structured trade data table

### Fetch Annual report detail page
```bash
curl -b cookies.txt "https://efdsearch.senate.gov/search/view/annual/18f41949-aa19-46cd-bbe3-835f8474ce03/"
```
**Result:** 200 OK — HTML page with 10+ sections of financial data

---

## Technical Details

| Detail | Value |
|--------|-------|
| Framework | Django (Python) |
| Server | gunicorn |
| Frontend | jQuery 3.7.1, DataTables 1.10.15, Bootstrap |
| CSRF | Django CSRF middleware (cookie + form token) |
| Session | Django sessions (cookie-based, encodes agreement) |
| Data API | DataTables server-side JSON protocol |
| Report detail | HTML pages (not JSON) — need HTML parsing |
| Rate limiting | Aggressive — 503 on rapid sequential API calls |
| Session expiry | Unknown (cookies don't specify max-age for sessionid) |

---

## Constraints & Gotchas

1. **Session is tied to initial form POST** — the `report_types` and filters in the form POST determine what the `/search/report/data/` endpoint will return. Changing report types requires a new form POST.

2. **Rate limiting** — rapid API calls return 503. Add delays (1-2 seconds) between requests.

3. **Detail pages are HTML, not JSON** — the search index returns JSON, but individual reports are HTML tables that need parsing.

4. **Some reports are scanned PDFs** — older reports (pre-electronic filing) may render as PDF images rather than structured HTML.

5. **DataTables protocol overhead** — every request must include `columns[N][data]`, `columns[N][searchable]`, etc. boilerplate parameters.

6. **CSRF double-submit** — both the cookie `csrftoken` and the `X-CSRFToken` header must match.

---

## Data Coverage

- **Date range:** January 1, 2012 — present
- **Senators:** Current + former (retained 6 years after leaving office)
- **Candidates:** Retained 1 year after no longer a candidate
- **Report types:** Annual, Periodic Transactions (stock trades), Extensions, Blind Trusts, Other

---

## Comparison with House Financial Disclosures

| Feature | Senate (efdsearch.senate.gov) | House (disclosures-clerk.house.gov) |
|---------|:----:|:----:|
| Index format | JSON API (DataTables) | XML + TSV zip files |
| Detail format | HTML tables | PDF documents |
| Structured trade data | Yes (HTML tables) | No (PDFs) |
| API | Yes (undocumented) | No (zip download) |
| Auth required | Session + CSRF | None for zip; search needs agreement |
| Bulk download | Via pagination (100/page) | Annual zip files |
| DocID/UUID system | UUID per report | Numeric DocID per report |

**Senate is more accessible for programmatic use** — JSON API with paginated search vs House's ZIP-of-PDFs approach. However, House provides a cleaner structured index (XML) while Senate buries the index in DataTables JSON.

---

*Researched 2026-03-16 via Chrome DevTools MCP. All endpoints verified working.*
