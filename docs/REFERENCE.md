# DataGod — Complete Reference

The single source of truth for **what DataGod is, how it works, and every endpoint**.
The interactive equivalent is the Swagger UI at [`/docs`](https://datagod.example.com/docs);
the endpoint section below is generated from the same OpenAPI schema by
`scripts/gen_reference_doc.py`.

- **Base URL:** `https://datagod.example.com`
- **Source:** https://github.com/mishafyi/datagod
- **Version:** 1.0.0

## Contents
1. [Overview](#1-overview)
2. [How it works](#2-how-it-works) — auth, response envelope, errors
3. [Architecture](#3-architecture) — request lifecycle, layout, client contract, deployment
4. [Configuration](#4-configuration) — environment variables
5. [Endpoints](#5-endpoints) — every route, grouped by source (generated)
6. [Per-source notes](#6-per-source-notes)

---

## 1. Overview

DataGod unifies **21 free US-government and markets data sources** (plus a
cross-reference aggregator) behind one HTTP API. Every route is a thin async
pass-through: it calls one upstream and returns that upstream's JSON **unchanged**,
wrapped in a standard response envelope. There is no data transformation — the
envelope is the only mutation.

Sources: FRED · SEC EDGAR · USAspending · US Census · BLS · Treasury Fiscal Data ·
FEC · Congress.gov · openFDA · ClinicalTrials.gov · EIA · FEMA · Federal Register ·
House Financial Disclosures · JEFS (judicial disclosures) · NARA · National Security
Archive · Smithsonian Open Access · Wilson Center Digital Archive · Nasdaq.com ·
Yahoo Finance — plus `/cross-reference/*` aggregators.

---

## 2. How it works

### 2.1 Authentication — two separate mechanisms

They are **not** interchangeable:

| Target | Auth that works | Auth that fails |
|--------|-----------------|-----------------|
| **Data endpoints** (everything except below) | `X-API-Key: <key>` request header | HTTP Basic alone → **401** |
| **Spec & docs** (`/openapi.json`, `/docs`, `/redoc`) | HTTP Basic — user `datagod`, password = the API key | `X-API-Key` header alone → **401** |
| **`/health`** | none (public) | — |

- The data-endpoint key is `DATAGOD_API_KEY`. A missing or wrong key returns **401**
  (rendered in the standard error envelope). Enforced by an app-level dependency
  (`app/auth.py::require_api_key`, FastAPI's built-in `APIKeyHeader`). The service
  **fails closed**: if `DATAGOD_API_KEY` is unset, every gated request is rejected.
- The docs use HTTP Basic so a browser can authenticate with a login prompt
  (`app/auth.py::require_docs_auth`). Username defaults to `datagod`; the password is
  `DATAGOD_DOCS_PASSWORD` if set, otherwise it falls back to `DATAGOD_API_KEY`.

```bash
# Call a data endpoint
curl -H "X-API-Key: $DATAGOD_API_KEY" "https://datagod.example.com/fred/GDP?limit=5"

# Fetch the full machine-readable spec
curl -u "datagod:$DATAGOD_API_KEY" https://datagod.example.com/openapi.json
```

In Swagger UI, click **Authorize** and paste the key once — every "Try it out" call
then sends the `X-API-Key` header for you.

### 2.2 Response envelope

Every JSON response is wrapped by `app/middleware.py::ResponseEnvelopeMiddleware`:

```json
{
  "meta": {
    "source": "fred",
    "endpoint": "/fred/GDP",
    "timestamp": "2026-06-10T00:00:00Z",
    "status": "success"
  },
  "data": { "...": "the upstream payload, unchanged" },
  "error": null
}
```

- Read the payload from **`data`**.
- `meta.source` is the first path segment; `meta.status` is `"success"` or `"error"`.
- On error, `data` is the error dict (below), `error` holds its message, and
  `meta.status` is `"error"`.
- The docs/spec paths are exempt from wrapping (Swagger needs the raw spec).

### 2.3 Error semantics

Client modules never raise; they return an **error dict**:

```json
{ "error": true, "source": "<src>", "upstream_status": <int>, "message": "<str>" }
```

The middleware maps that to the HTTP status:

| Situation | `upstream_status` | HTTP status returned |
|-----------|-------------------|----------------------|
| Success | — | the route's status (200) |
| Upstream client error | 400–499 | **passed through** (e.g. 404 stays 404) |
| Upstream 5xx / timeout / connect error / parse error | 500+ or `0` | **502 Bad Gateway** |
| Missing or invalid API key | 401 | **401** |

So always branch on the HTTP status (or `meta.status`), then read `data`.

---

## 3. Architecture

### 3.1 Request lifecycle

```
client request
   │
   ▼
ResponseEnvelopeMiddleware  ── wraps the response on the way out
   │
   ▼
require_api_key (app-level dependency)  ── checks X-API-Key
   │   └─ skips PUBLIC_PATHS (/health) and DOCS_PATHS (/docs,/redoc,/openapi.json)
   │   └─ invalid/missing → UnauthorizedError → 401 error envelope
   ▼
route handler (app/main.py)  ── validates query params, calls one client function
   │
   ▼
client function (app/clients/<source>.py)  ── safe_get / safe_post → upstream
   │
   ▼
upstream API  ── returns JSON (or the client returns an error dict)
   │
   ▼
envelope { meta, data, error }  ── status mapped per §2.3
```

### 3.2 Code layout

| Path | Responsibility |
|------|----------------|
| `app/main.py` | Every route, grouped by source under `# ── X ──` comments, each tagged for Swagger. Holds the `FastAPI(...)` app config (description, tags, version), the app-level API-key dependency, the Basic-auth-protected docs routes, and the `UnauthorizedError` handler. |
| `app/clients/` | One module per upstream. Each defines a `BASE` URL and a few `async` functions returning upstream JSON or an error dict. |
| `app/clients/__init__.py` | `get_client()` (one shared `httpx.AsyncClient`, 30s timeout, process singleton), `safe_get` / `safe_post` (try/except + `raise_for_status` + `.json()` + error dict), and `UpstreamJSON = dict \| list`. |
| `app/clients/cross_reference.py` | Aggregates several upstreams via `asyncio.gather` wrapped in `_safe(...)` so one bad source doesn't break the response. |
| `app/clients/yfin.py` | yfinance is synchronous → each call dispatched via `asyncio.to_thread()`; DataFrames converted to records lists (NaN → JSON null). |
| `app/auth.py` | `require_api_key` (data, `APIKeyHeader`) and `require_docs_auth` (docs, `HTTPBasic`); `PUBLIC_PATHS`, `DOCS_PATHS`. |
| `app/middleware.py` | `ResponseEnvelopeMiddleware` — the envelope + HTTP-status mapping. |
| `app/config.py` | Loads `.env` at import; exposes the `cfg` singleton with all keys. |
| `app/cache.py` | In-memory TTL cache + `@cached` decorator. Defined; only `/admin/clear-cache` uses `clear_cache()`. |
| `app/resilience.py` | Tenacity retry helpers. Defined but not currently wired. |
| `docs/` | This reference, the generated `ENDPOINTS.md`, and per-source deep-dives. |
| `scripts/` | `gen_reference_doc.py` (this file's endpoint section), `gen_endpoints_doc.py`, `build_wilson_index.py`. |

### 3.3 Client contract

Every client function returns either upstream JSON or the error dict, almost always
through `safe_get` / `safe_post`:

```python
from . import UpstreamJSON, safe_get

async def some_endpoint(arg: str) -> UpstreamJSON:
    return await safe_get(f"{BASE}/path", "<source>", params={...})
```

**Do not raise from client functions** — return the error dict instead; the
middleware reads `data.error`, not exceptions. Conventions: no transformation of
upstream responses; async only (sync libs go through `asyncio.to_thread()`); reuse
the single shared `httpx` client; tag every route.

### 3.4 Deployment

`Dockerfile` (python:3.11-slim) copies `app/` + `requirements.txt` and runs
`uvicorn app.main:app` on port 8000. Deployed on a self-hosted **Coolify** instance
(VPS), which builds the image, runs it behind a **Traefik** reverse proxy that
terminates TLS (Let's Encrypt) for `datagod.example.com`. **Auto-deploys on every
push to `main`** via a GitHub webhook. Upstream keys and `DATAGOD_API_KEY` are set as
Coolify environment variables. See `DEPLOY-NEW-PROJECT-COOLIFY.md`.

---

## 4. Configuration

Loaded from `.env` at import by `app/config.py`. Only `DATAGOD_API_KEY` is required to
start; per-source keys unlock the sources that need them (see `.env.example`).

| Variable | Required? | Purpose |
|----------|-----------|---------|
| `DATAGOD_API_KEY` | **yes** | Gates every data endpoint (`X-API-Key`). |
| `DATAGOD_DOCS_USER` | no (default `datagod`) | Username for the docs Basic auth. |
| `DATAGOD_DOCS_PASSWORD` | no (falls back to `DATAGOD_API_KEY`) | Password for the docs Basic auth. |
| `SEC_USER_AGENT` | for EDGAR | `"Name email"`; SEC returns 403 without it. |
| `FRED_API_KEY` | for FRED | FRED economic data. |
| `CENSUS_API_KEY` | for Census | Census now 302s keyless requests to a Missing-Key page. |
| `BLS_API_KEY` | optional | Higher BLS rate limits. |
| `FEC_API_KEY` | optional | Falls back to `DEMO_KEY`. |
| `CONGRESS_API_KEY` | optional | Falls back to `DEMO_KEY`. |
| `EIA_API_KEY` | optional | Falls back to `DEMO_KEY`. |
| `SMITHSONIAN_API_KEY` | optional | Falls back to `DEMO_KEY`. |
| `SAM_API_KEY` / `DATAGOV_API_KEY` | optional | Reserved; not yet wired to a client. |

---

## 5. Endpoints

All paths are relative to the base URL and require the `X-API-Key` header (except
`GET /health`). Query/path parameters, types, defaults, and descriptions below are
generated from the live OpenAPI schema.

<!-- BEGIN GENERATED ENDPOINTS -->

### Health

_Liveness probe. `GET /health` is public (no key required)._

#### `GET /`

**API index: sources and endpoint map**

_No parameters._

#### `GET /health`

**Liveness probe (public, no API key)**

Public liveness probe (no API key required).

_No parameters._

### FRED

_Federal Reserve Economic Data — 800K+ economic time series._

#### `GET /fred`

**Search FRED series by keyword**

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `q` | query | string | no |  | Search series by keyword |
| `limit` | query | integer | no | 10 |  |

#### `GET /fred/{series_id}`

**Fetch a FRED economic time series**

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `series_id` | path | string | yes |  |  |
| `limit` | query | integer | no | 10 |  |

### EDGAR

_SEC EDGAR — corporate filings, XBRL financials, full-text search. The Frames endpoint compares one concept across all filers in a single call._

#### `GET /edgar/company/{cik}`

**Company profile and filing history (CIK or ticker)**

Company metadata + filing history. Accepts CIK number or ticker (e.g., AAPL).

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `cik` | path | string | yes |  |  |

#### `GET /edgar/concept/{cik}/{concept}`

**One XBRL concept's history for a company**

One concept's history (e.g., Revenues, Assets, NetIncomeLoss).

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `cik` | path | string | yes |  |  |
| `concept` | path | string | yes |  |  |
| `taxonomy` | query | string | no | us-gaap |  |

#### `GET /edgar/financials/{cik}`

**All XBRL financial facts for a company**

All XBRL financial facts for a company.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `cik` | path | string | yes |  |  |

#### `GET /edgar/frames/{concept}`

**One concept across all filers (cross-company)**

Cross-company comparison. One concept for ALL companies.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `concept` | path | string | yes |  |  |
| `unit` | query | string | no | USD |  |
| `period` | query | string | no | CY2023 |  |
| `taxonomy` | query | string | no | us-gaap |  |

#### `GET /edgar/search`

**Full-text search inside filing documents**

Full-text search inside filing documents.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `q` | query | string | yes |  |  |
| `forms` | query | string | no |  |  |
| `limit` | query | integer | no | 10 |  |

### Nasdaq

_Nasdaq.com (unofficial) — quote, price, history, dividends._

#### `GET /nasdaq/dividends/{ticker}`

**Dividend history**

Dividend history.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `ticker` | path | string | yes |  |  |
| `asset_class` | query | string | no | stocks |  |

#### `GET /nasdaq/history/{ticker}`

**Daily OHLCV between two dates**

Daily OHLCV between two dates (YYYY-MM-DD). Newest row first.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `ticker` | path | string | yes |  |  |
| `fromdate` | query | string | yes |  |  |
| `todate` | query | string | yes |  |  |
| `limit` | query | integer | no | 30 |  |
| `asset_class` | query | string | no | stocks |  |

#### `GET /nasdaq/price/{ticker}`

**Real-time price, bid/ask, volume, change**

Real-time price, bid/ask, volume, percent change.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `ticker` | path | string | yes |  |  |
| `asset_class` | query | string | no | stocks |  |

#### `GET /nasdaq/quote/{ticker}`

**Quote summary: market cap, sector, P/E, 52-week**

Market cap, sector, industry, P/E, dividend, 52-week range.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `ticker` | path | string | yes |  |  |
| `asset_class` | query | string | no | stocks |  |

### yfinance

_Yahoo Finance via the yfinance library — fundamentals, news, options, holders._

#### `GET /yfinance/dividends/{ticker}`

**Dividend payment history**

Dividend payment history.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `ticker` | path | string | yes |  |  |

#### `GET /yfinance/financials/{ticker}`

**Income statement, balance sheet, cash flow**

Annual + quarterly income statement, balance sheet, cash flow.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `ticker` | path | string | yes |  |  |

#### `GET /yfinance/history/{ticker}`

**OHLCV price history**

OHLCV history. period: 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max. interval: 1m,5m,1h,1d,1wk,1mo.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `ticker` | path | string | yes |  |  |
| `period` | query | string | no | 1mo |  |
| `interval` | query | string | no | 1d |  |

#### `GET /yfinance/holders/{ticker}`

**Major, institutional, and fund holders**

Major, institutional, and mutual-fund holders.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `ticker` | path | string | yes |  |  |

#### `GET /yfinance/info/{ticker}`

**Full ticker fundamentals (~140 fields)**

Full ticker info: ~140 fields incl. market cap, P/E, EPS, beta, margins, ROE, analyst targets.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `ticker` | path | string | yes |  |  |

#### `GET /yfinance/news/{ticker}`

**Recent news headlines**

Recent news headlines linked to the ticker.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `ticker` | path | string | yes |  |  |

#### `GET /yfinance/options/{ticker}`

**Options chain (expiries or calls/puts)**

Options chain. expiry blank → list expiries; else calls+puts for that date.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `ticker` | path | string | yes |  |  |
| `expiry` | query | string | no |  |  |

#### `GET /yfinance/recommendations/{ticker}`

**Analyst recommendation history**

Analyst recommendation history.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `ticker` | path | string | yes |  |  |

### USAspending

_USAspending.gov — federal contracts and grants ($6T+/yr)._

#### `GET /usaspending/agencies`

**List federal agencies**

_No parameters._

#### `GET /usaspending/by-agency`

**Spending totals by agency (fiscal year)**

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `fy` | query | string | no | 2025 |  |
| `quarter` | query | string | no | 1 |  |

#### `GET /usaspending/search`

**Search federal awards by keyword**

Search federal awards by keyword.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `q` | query | string | yes |  |  |
| `start_date` | query | string | no |  |  |
| `end_date` | query | string | no |  |  |
| `limit` | query | integer | no | 10 |  |

### Census

_US Census Bureau — population, income, and raw ACS queries._

#### `GET /census/acs`

**Raw ACS query (any variables and geography)**

Raw ACS query. variables: comma-separated ACS variable codes.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `variables` | query | string | no | NAME,B01001_001E |  |
| `year` | query | integer | no | 2022 |  |
| `geo_for` | query | string | no | state:* |  |
| `geo_in` | query | string | no |  |  |

#### `GET /census/income`

**Median household income by state**

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `year` | query | integer | no | 2022 |  |

#### `GET /census/population`

**Population by state**

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `year` | query | integer | no | 2022 |  |

### BLS

_Bureau of Labor Statistics — employment, wages, CPI._

#### `GET /bls/{series_id}`

**BLS series (CPI, unemployment, wages, PPI)**

Get BLS series. Shortcuts: unemployment, cpi, nonfarm_employment, ppi, hourly_earnings.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `series_id` | path | string | yes |  |  |
| `start_year` | query | integer | no | 2024 |  |
| `end_year` | query | integer | no | 2026 |  |

### Treasury

_Treasury Fiscal Data — debt, interest rates, exchange rates._

#### `GET /treasury/debt`

**US public debt (debt to the penny)**

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `limit` | query | integer | no | 5 |  |

#### `GET /treasury/exchange`

**Treasury exchange rates**

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `limit` | query | integer | no | 5 |  |

#### `GET /treasury/rates`

**Average interest rates on US debt**

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `limit` | query | integer | no | 5 |  |

### FEC

_Federal Election Commission — candidates, contributions, totals._

#### `GET /fec/candidates`

**Search federal candidates**

Search candidates. office: P, S, H.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `office` | query | string | no |  |  |
| `state` | query | string | no |  |  |
| `limit` | query | integer | no | 10 |  |

#### `GET /fec/contributions`

**Campaign contributions**

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `name` | query | string | no |  |  |
| `candidate_id` | query | string | no |  |  |
| `limit` | query | integer | no | 10 |  |

#### `GET /fec/totals`

**Candidate financial totals by receipts**

Candidate financial totals by receipts.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `office` | query | string | no | P |  |
| `year` | query | integer | no | 2024 |  |
| `limit` | query | integer | no | 10 |  |

### Congress

_Congress.gov — bills, members, votes._

#### `GET /congress/bill/{congress_num}/{bill_type}/{number}`

**Single bill detail**

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `congress_num` | path | integer | yes |  |  |
| `bill_type` | path | string | yes |  |  |
| `number` | path | integer | yes |  |  |

#### `GET /congress/bills`

**Recent bills**

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `limit` | query | integer | no | 10 |  |
| `congress_num` | query | integer | no | 0 |  |

#### `GET /congress/members`

**Members of Congress**

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `limit` | query | integer | no | 10 |  |

#### `GET /congress/votes`

**Roll-call votes by chamber**

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `chamber` | query | string | no | house |  |
| `congress_session` | query | integer | no | 118 |  |
| `limit` | query | integer | no | 10 |  |

### FDA

_openFDA — drug adverse events, drug recalls, food recalls._

#### `GET /fda/drug-events`

**Drug adverse-event reports**

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `search` | query | string | no |  |  |
| `limit` | query | integer | no | 10 |  |

#### `GET /fda/drug-recalls`

**Drug recall enforcement reports**

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `search` | query | string | no |  |  |
| `limit` | query | integer | no | 10 |  |

#### `GET /fda/food-recalls`

**Food recall enforcement reports**

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `search` | query | string | no |  |  |
| `limit` | query | integer | no | 10 |  |

### Clinical Trials

_ClinicalTrials.gov — 500K+ registered trials._

#### `GET /clinical-trials`

**Search ClinicalTrials.gov**

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `condition` | query | string | no |  |  |
| `intervention` | query | string | no |  |  |
| `status` | query | string | no |  |  |
| `limit` | query | integer | no | 10 |  |

#### `GET /clinical-trials/{nct_id}`

**Single trial by NCT ID**

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `nct_id` | path | string | yes |  |  |

### EIA

_Energy Information Administration — gas prices, electricity, and generic dataset queries._

#### `GET /eia`

**List available EIA datasets**

_No parameters._

#### `GET /eia/electricity`

**Electricity generation and retail data**

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `limit` | query | integer | no | 10 |  |

#### `GET /eia/gas-prices`

**Gasoline prices**

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `limit` | query | integer | no | 10 |  |

#### `GET /eia/{route}`

**Generic EIA dataset query by route**

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `route` | path | string | yes |  |  |
| `frequency` | query | string | no | annual |  |
| `data` | query | string | no | value |  |
| `limit` | query | integer | no | 10 |  |

### FEMA

_OpenFEMA — disaster declarations, grants, flood claims._

#### `GET /fema/disasters`

**Disaster declarations**

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `limit` | query | integer | no | 10 |  |

#### `GET /fema/flood-claims`

**NFIP flood insurance claims**

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `limit` | query | integer | no | 10 |  |

#### `GET /fema/grants`

**FEMA grant awards**

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `limit` | query | integer | no | 10 |  |

### Federal Register

_Federal Register — rules, notices, executive orders._

#### `GET /federal-register`

**Search the Federal Register**

Search Federal Register. doc_type: RULE, PRORULE, NOTICE, PRESDOCU.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `term` | query | string | no |  |  |
| `doc_type` | query | string | no |  |  |
| `agency` | query | string | no |  |  |
| `limit` | query | integer | no | 10 |  |

#### `GET /federal-register/{doc_number}`

**Single Federal Register document**

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `doc_number` | path | string | yes |  |  |

### JEFS

_Judicial Financial Disclosures — session-based; needs Playwright registration + reCAPTCHA first._

#### `GET /jefs/facets`

**JEFS filter facets (needs session)**

Get filter dropdowns (years, courts, positions, report types). Requires active session.

_No parameters._

#### `POST /jefs/register`

**Open a JEFS session (Playwright + reCAPTCHA)**

Open a Playwright browser to register a JEFS session.
Required: real name, occupation, address (under penalty of perjury per JEFS terms).
The browser opens headed; user solves reCAPTCHA + submits user-agreement.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `name` | query | string | yes |  |  |
| `occupation` | query | string | yes |  |  |
| `address` | query | string | yes |  |  |
| `headed` | query | boolean | no | True |  |

#### `POST /jefs/reset`

**Clear the JEFS session**

Clear JEFS session. Must re-register before next call.

_No parameters._

#### `GET /jefs/search`

**Search judicial disclosures (needs session)**

Search judicial financial disclosures. Requires active session.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `q` | query | string | no |  |  |
| `year` | query | string | no |  |  |
| `court_type` | query | string | no |  |  |
| `start` | query | integer | no | 0 |  |

### House Disclosures

_US House financial disclosures (member/candidate stock trades)._

#### `GET /house-disclosures/candidates`

**House candidate financial disclosures**

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `last_name` | query | string | no |  |  |
| `year` | query | string | no |  |  |
| `state` | query | string | no |  |  |
| `district` | query | string | no |  |  |

#### `GET /house-disclosures/members`

**House member financial disclosures**

Search House member financial disclosures (stock trades).

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `last_name` | query | string | no |  |  |
| `year` | query | string | no |  |  |
| `state` | query | string | no |  |  |
| `district` | query | string | no |  |  |

### NARA

_US National Archives Catalog — all record groups plus the 14 presidential libraries._

#### `GET /nara/record/{na_id}`

**Single catalog record by NAID**

A single catalog record by National Archives Identifier (NAID).

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `na_id` | path | string | yes |  |  |

#### `GET /nara/search`

**Search the National Archives Catalog**

Search the National Archives Catalog (all record groups + the 14 presidential libraries). 20 results/page.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `q` | query | string | no |  |  |
| `page` | query | integer | no | 1 |  |

### NSArchive

_National Security Archive (GWU NGO, not NARA) — Virtual Reading Room declassified docs (HTML scrape)._

#### `GET /nsarchive/document/{doc_id}`

**Single VRR document by id-slug**

One VRR document by its '{id}-{slug}' path (from search results).

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `doc_id` | path | string | yes |  |  |

#### `GET /nsarchive/search`

**Search the National Security Archive VRR**

Search the National Security Archive Virtual Reading Room (empty q browses). 20/page.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `q` | query | string | no |  |  |
| `page` | query | integer | no | 1 |  |

### Smithsonian

_Smithsonian Open Access (EDAN) — 11M+ museum/library/archive records._

#### `GET /smithsonian/category/{category}/search`

**Search within a Smithsonian category**

Search within art_design | history_culture | science_technology.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `category` | path | string | yes |  |  |
| `q` | query | string | no |  |  |
| `start` | query | integer | no | 0 |  |
| `rows` | query | integer | no | 10 |  |

#### `GET /smithsonian/object/{object_id}`

**Full object record by EDAN id**

Full metadata record by EDAN id.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `object_id` | path | string | yes |  |  |

#### `GET /smithsonian/search`

**Search Smithsonian Open Access**

Search 11M+ Open Access records. sort: relevancy|newest|updated|random.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `q` | query | string | no |  |  |
| `start` | query | integer | no | 0 |  |
| `rows` | query | integer | no | 10 |  |
| `sort` | query | string | no |  |  |
| `obj_type` | query | string | no |  |  |

#### `GET /smithsonian/stats`

**Open Access dataset statistics**

Open Access dataset statistics.

_No parameters._

#### `GET /smithsonian/terms/{category}`

**Controlled-vocabulary terms**

Controlled-vocab terms: culture, topic, place, object_type, data_source, date, name.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `category` | path | string | yes |  |  |

### Wilson Center

_Wilson Center Digital Archive — local mirror of 16,756 declassified documents._

#### `GET /wilson/document/{slug}`

**Single Wilson document by slug**

Full record for one document by slug: title, source, subjects, download availability.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `slug` | path | string | yes |  |  |

#### `GET /wilson/documents`

**Search the Wilson Center mirror**

Full-text search the local Wilson Center mirror (16,756 declassified documents).

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `q` | query | string | no |  |  |
| `page` | query | integer | no | 1 |  |
| `items_per_page` | query | integer | no | 10 |  |

### Cross-Reference

_Aggregators that join several sources for one company or politician._

#### `GET /cross-reference/company/{name}`

**Company across EDGAR + USAspending + FEC**

Cross-reference a company across EDGAR + USAspending + FEC.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `name` | path | string | yes |  |  |

#### `GET /cross-reference/politician/{last_name}`

**Politician across House disclosures + FEC**

Cross-reference a politician across House disclosures + FEC.

| Parameter | In | Type | Required | Default | Description |
|-----------|----|------|----------|---------|-------------|
| `last_name` | path | string | yes |  |  |
| `first_name` | query | string | no |  |  |

### Admin

_Operational endpoints (cache management)._

#### `POST /admin/clear-cache`

**Clear the in-memory cache**

_No parameters._

<!-- END GENERATED ENDPOINTS -->

---

## 6. Per-source notes

Each upstream has quirks worth knowing before you call it — these live in dedicated
deep-dives (response shapes, undocumented behavior, rate limits, pitfalls):

| Doc | Covers |
|-----|--------|
| `docs/GOV_APIS.md` | The 12 core gov APIs bundled here (FRED, BLS, Census, Treasury, FEC, Congress, FDA, ClinicalTrials, EIA, FEMA, Federal Register, USAspending) with verified curl examples. |
| `docs/EDGAR_API.md` | SEC EDGAR — submissions, company concepts, XBRL frames, full-text search, ticker→CIK, rate limit (10/sec). |
| `docs/NASDAQ_API.md` | Nasdaq.com unofficial API — string-encoded numbers, browser-UA requirement, OTC gaps. |
| `docs/YFINANCE_API.md` | yfinance wrapper — sync→async, DataFrame→records, period/interval values, options mechanics. |
| `docs/NARA_API.md` | National Archives Catalog — keyless proxy gateway, mandatory browser headers, `page` not `offset`. |
| `docs/NSARCHIVE_API.md` | National Security Archive (GWU NGO, ≠ NARA) — Drupal VRR HTML scrape, brittle. |
| `docs/SMITHSONIAN_API.md` | Smithsonian Open Access (EDAN) — auth, search/content/category/terms/stats, response envelope. |
| `docs/WILSON_DIGITAL_ARCHIVE_API.md` | Wilson Center — local SQLite + FTS5 mirror (live site is DNS-dead), metadata-only downloads. |
| `docs/HOUSE_FD_API.md` | House Financial Disclosures — undocumented form-POST, HTML-table parsing. |
| `docs/JEFS_API.md` | Judicial disclosures — session + Playwright reCAPTCHA; no public REST API. |
| `docs/SENATE_EFD_API.md` | Senate disclosures — researched, not yet wired to a client. |
| `docs/CONVERSATION_LOG.md` | Project research log. |
