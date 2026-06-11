---
name: house-disclosures
description: "US House financial disclosures and congressional stock trades — representatives' and candidates' stock trades, holdings, and periodic transaction reports (PTRs). Use for politicians' or members of Congress' stock transactions in the House."
keywords: "congressional stock trades, stock trades, politician trading, House members, representatives, financial disclosures, holdings, periodic transaction reports, PTR, congressional trading"
routes: "/house-disclosures/candidates, /house-disclosures/members"
---

# House Financial Disclosures — Undocumented API

> Discovered via Chrome DevTools inspection, 2026-03-16
> Base URL: `https://disclosures-clerk.house.gov`

## Overview

The U.S. House of Representatives Clerk's office provides financial disclosure reports for Members, staff, and candidates since 2008. Behind the search UI is an **ASP.NET Core** app with **two POST endpoints** that return HTML fragments containing structured table data. **No authentication required** — works with simple curl.

---

## API Endpoints

### 1. Member Search

```
POST https://disclosures-clerk.house.gov/FinancialDisclosure/ViewMemberSearchResult
```

**No auth required.** Just needs `X-Requested-With: XMLHttpRequest` header.

#### Parameters (form-encoded)

| Parameter | Type | Required | Description |
|-----------|------|:--------:|-------------|
| `LastName` | string | No | Filter by last name (partial match) |
| `FilingYear` | string | No | Year: `2008`—`2026` |
| `State` | string | No | Two-letter state code: `CA`, `TX`, `NY`, etc. |
| `District` | string | No | District number |

#### Example — All 2026 PTRs

```bash
curl -s "https://disclosures-clerk.house.gov/FinancialDisclosure/ViewMemberSearchResult" \
  -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-Requested-With: XMLHttpRequest" \
  -d "LastName=&FilingYear=2026&State=&District="
```
**Result:** 200 OK — HTML table with all 2026 filings

#### Example — Search by name

```bash
curl -s "https://disclosures-clerk.house.gov/FinancialDisclosure/ViewMemberSearchResult" \
  -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-Requested-With: XMLHttpRequest" \
  -d "LastName=Pelosi&FilingYear=2024&State=&District="
```
**Result:** 200 OK — All Pelosi filings for 2024 (6 PTRs + 1 Annual)

#### Example — Search by state

```bash
curl -s "https://disclosures-clerk.house.gov/FinancialDisclosure/ViewMemberSearchResult" \
  -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-Requested-With: XMLHttpRequest" \
  -d "LastName=&FilingYear=2026&State=CA&District="
```

#### Response (HTML table)

```html
<table class="library-table table dataTable no-footer table-striped">
  <thead>
    <tr>
      <th>Name</th>
      <th>Office</th>
      <th>Filing Year</th>
      <th>Filing</th>
    </tr>
  </thead>
  <tbody>
    <tr role="row">
      <td data-label="Name" class="memberName">
        <a href="public_disc/ptr-pdfs/2024/20024542.pdf" target="_blank">Pelosi, Hon.. Nancy </a>
      </td>
      <td data-label="Office">CA11</td>
      <td data-label="Filing Year">2024</td>
      <td data-label="Filing">PTR Original</td>
    </tr>
  </tbody>
</table>
```

#### Response fields

| Field | Example | Description |
|-------|---------|-------------|
| Name | `Pelosi, Hon.. Nancy` | Member name with prefix |
| Office | `CA11` | State + district |
| Filing Year | `2024` | Year of filing |
| Filing | `PTR Original` | Filing type (see table below) |
| PDF href | `public_disc/ptr-pdfs/2024/20024542.pdf` | Relative path to PDF |

---

### 2. Candidate Search

```
POST https://disclosures-clerk.house.gov/FinancialDisclosure/ViewCandidateSearchResult
```

**No auth required.**

#### Parameters (form-encoded)

| Parameter | Type | Required | Description |
|-----------|------|:--------:|-------------|
| `LastName` | string | No | Filter by last name |
| `ElectionYear` | string | No | Election year: `2011`—`2027` |
| `State` | string | No | Two-letter state code |
| `District` | string | No | District number |

#### Example

```bash
curl -s "https://disclosures-clerk.house.gov/FinancialDisclosure/ViewCandidateSearchResult" \
  -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-Requested-With: XMLHttpRequest" \
  -d "LastName=&ElectionYear=2026&State=&District="
```

#### Candidate-specific filing types

| Filing | Description |
|--------|-------------|
| `Candidate/Misc` | Standard candidate disclosure |
| `FEC Non-Filer` | Non-filer notification |
| `Withdrawal` | Withdrawn candidacy |

---

### 3. Other Endpoints (GET, return HTML partials)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/FinancialDisclosure/ViewSearch` | GET | Returns the search form HTML (sets antiforgery cookie) |
| `/FinancialDisclosure/ViewReport` | GET | Returns the overview/download tab HTML |

---

## Filing Types (Members)

Verified from 2025 data (610 total filings):

| Filing Type | Count (2025) | Description |
|-------------|:------------:|-------------|
| `PTR Original` | 514 | Periodic Transaction Report — stock trades |
| `Termination` | 50 | Member leaving office |
| `Extension` | 34 | Filing deadline extension |
| `Term. Exemption` | 5 | Termination exemption |
| `Gift Waiver` | 5 | Gift rule waiver |
| `New Filer` | 1 | New member first filing |
| `FD Original` | — | Annual financial disclosure |
| `FD Amendment` | — | Amendment to annual disclosure |
| `PTR Amendment` | — | Amendment to PTR |

---

## PDF Download URLs

PDFs are directly accessible — no auth, no session, no CSRF.

### URL patterns

| Filing Type | URL Pattern |
|-------------|-------------|
| PTR (stock trades) | `https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{year}/{DocID}.pdf` |
| Annual / FD | `https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}/{DocID}.pdf` |
| Candidate filings | `https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}/{DocID}.pdf` |

### DocID ranges (observed)

| Prefix | Type |
|--------|------|
| `200xxxxx` | PTR filings |
| `100xxxxx` | Annual/FD filings |
| `400xxxxx` | FEC non-filer notices |
| `300xxxxx` | Other documents |
| `8xxx` | Smaller filings (withdrawals, exemptions) |

### Verified working

```bash
# PTR PDF — Pelosi
curl -sI "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2024/20024542.pdf"
# → 200 OK, 63KB PDF

# Annual FD PDF — Pelosi
curl -sI "https://disclosures-clerk.house.gov/public_disc/financial-pdfs/2024/10066169.pdf"
# → 200 OK, PDF
```

---

## Bulk Downloads (XML + TXT index)

Annual ZIP files contain an XML index and TSV of all filings for that year.

### Download URL pattern

```
https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}FD.zip
```

### Available years and sizes

| Year | Size | URL |
|------|------|-----|
| 2008 | ~95K | `.../2008FD.zip` |
| ... | ... | ... |
| 2022 | 93K | `.../2022FD.zip` |
| 2023 | 82K | `.../2023FD.zip` |
| 2024 | 78K | `.../2024FD.zip` |
| 2025 | 74K | `.../2025FD.zip` |
| 2026 | 7K | `.../2026FD.zip` |

### ZIP contents

Each ZIP contains two files:
- `{year}FD.xml` — Structured XML index
- `{year}FD.txt` — Tab-delimited text (same data)

### XML structure

```xml
<FinancialDisclosure>
  <Member>
    <Prefix>Hon.</Prefix>
    <Last>Pelosi</Last>
    <First>Nancy</First>
    <Suffix />
    <FilingType>P</FilingType>
    <StateDst>CA11</StateDst>
    <Year>2026</Year>
    <FilingDate>1/15/2026</FilingDate>
    <DocID>20033751</DocID>
  </Member>
</FinancialDisclosure>
```

### XML Filing type codes

| Code | Meaning |
|------|---------|
| `P` | Periodic Transaction Report (PTR) |
| `A` | Annual Report |
| `C` | Candidate filing |
| `X` | Extension / Termination |
| `D` | Due date notification |
| `W` | Withdrawal |

### TXT format (tab-delimited)

```
Prefix	Last	First	Suffix	FilingType	StateDst	Year	FilingDate	DocID
Hon.	Allen	Richard W.		P	GA12	2026	1/15/2026	20033751
```

---

## Data Coverage

| Metric | Value |
|--------|-------|
| Date range | 2008 — present |
| 2025 member filings | 610 |
| 2025 PTRs (stock trades) | 514 |
| 2026 filings (YTD) | 173 |
| Unique 2026 filers | 106 |
| Filing types | 9+ (PTR, Annual, Extension, Termination, etc.) |
| Candidate filings | Available via separate search endpoint |

---

## Technical Details

| Detail | Value |
|--------|-------|
| Framework | ASP.NET Core |
| CSRF | `.AspNetCore.Antiforgery.irol_7OdSko` cookie (NOT required for API calls) |
| Auth | **None** — API works with simple POST |
| Response format | HTML table fragments (not JSON) |
| Rate limiting | Not observed |
| Analytics | Google Analytics (G-3FFR6GSYFC), New Relic |
| Frontend | jQuery DataTables (client-side), Bootstrap |

---

## Key Differences from Senate EFD

| Feature | House | Senate |
|---------|:-----:|:------:|
| Auth required | **No** | Yes (session + CSRF) |
| Response format | HTML tables | JSON (DataTables protocol) |
| Bulk download | XML + TXT zip per year | No bulk download |
| PDF access | Direct URL, no auth | Requires session cookie |
| Search API | Simple POST, no boilerplate | DataTables params required |
| Rate limiting | None observed | 503 on rapid calls |
| Total records | ~610/year (members) | ~5,351 (all types, all years) |

**House is significantly easier to work with** — no auth, direct PDF access, structured XML bulk downloads, and the search API works with plain curl.

---

## Full Workflow: Get All House Stock Trades

```bash
# 1. Download the annual index
curl -o 2026FD.zip "https://disclosures-clerk.house.gov/public_disc/financial-pdfs/2026FD.zip"
unzip 2026FD.zip

# 2. Parse the XML for PTR filings (FilingType=P)
python3 -c "
import xml.etree.ElementTree as ET
tree = ET.parse('2026FD.xml')
for m in tree.findall('Member'):
    if m.find('FilingType').text == 'P':
        name = f\"{m.find('First').text} {m.find('Last').text}\"
        doc = m.find('DocID').text
        date = m.find('FilingDate').text
        state = m.find('StateDst').text
        print(f'{name} ({state}) {date} → https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/{doc}.pdf')
"

# 3. Download each PTR PDF
# curl -o "{DocID}.pdf" "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/{DocID}.pdf"

# 4. Or use the search API for real-time results
curl -s "https://disclosures-clerk.house.gov/FinancialDisclosure/ViewMemberSearchResult" \
  -X POST -H "X-Requested-With: XMLHttpRequest" \
  -d "LastName=&FilingYear=2026&State=&District="
```

---

*Researched 2026-03-16 via Chrome DevTools MCP + curl testing. All endpoints verified working with no authentication.*
