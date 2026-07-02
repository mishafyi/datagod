# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

DataGod is a FastAPI service that unifies 21 free data sources behind one HTTP API: 16 US government sources (FRED, SEC EDGAR, USAspending, Census, BLS, Treasury, FEC, Congress.gov, FDA, ClinicalTrials.gov, EIA, FEMA, Federal Register, House Financial Disclosures, Smithsonian Open Access, National Archives (NARA)), 2 markets sources (Nasdaq.com, Yahoo Finance via yfinance), 2 research sources (arXiv, Google Scholar), and the non-governmental National Security Archive (GWU; Virtual Reading Room scrape). Two more sources live in the codebase but are currently **disabled**: JEFS (judicial disclosures; needs Playwright + reCAPTCHA) and the Wilson Center Digital Archive (needs a local `data/wilson.db` mirror that isn't distributed). Routes are thin pass-throughs; each upstream gets a dedicated async client module that returns the upstream's JSON (or DataFrame-as-records, for yfinance) unchanged.

## Commands

```bash
# Run the server (auto-reload during dev)
.venv/bin/uvicorn app.main:app --reload --port 8000

# Install deps
.venv/bin/pip install -r requirements.txt

# Docker
docker build -t datagod .
docker run -p 8000:8000 --env-file .env datagod

# Integration tests
.venv/bin/python tests/test_all_endpoints.py      # smoke-tests every endpoint; target = $DATAGOD_BASE_URL (default http://localhost:8000)
.venv/bin/python tests/test_edgar_endpoints.py    # requires server running on localhost:8000
.venv/bin/python tests/test_nsarchive_search.py   # no server; needs network to nsarchive.gwu.edu
.venv/bin/python tests/test_arxiv.py              # no server; calls the arxiv client against live export.arxiv.org
.venv/bin/python tests/test_scholar.py            # no server; live Google Scholar (expect CAPTCHA/429 failures)

# Interactive API exploration (server must be running)
open http://localhost:8000/docs   # HTTP Basic prompt: user "datagod", password = DATAGOD_DOCS_PASSWORD (falls back to DATAGOD_API_KEY)
```

Five test files (no unit-test runner, linter, or type-checker is configured):
- `tests/test_all_endpoints.py` — smoke-tests every endpoint over HTTP (needs a running server + `DATAGOD_API_KEY` in `.env`), prints a grouped pass/fail table. JEFS and Wilson are skipped (disabled).
- `tests/test_edgar_endpoints.py` — hits the running server with httpx, prints a pass/fail table, writes `tests/reports/edgar_test_results.json`.
- `tests/test_nsarchive_search.py` — calls the `nsarchive` client directly against the live Virtual Reading Room (no server needed) and verifies its search behavior: the `search_api_fulltext` GET defaults to **OR** (the site's "Search Tips" wrongly say AND), while explicit `AND`/`OR`/`NOT`/parentheses/`*`/`"phrase"` and `field_date[max]` bounds all work; `sort_by` is ignored (always newest-first). See `docs/NSARCHIVE_API.md`.
- `tests/test_arxiv.py` / `tests/test_scholar.py` — call those clients directly against the live upstreams (no server needed).

## Available API clients

24 client modules in `app/clients/`. Each has matching routes in `main.py` and (for non-trivial APIs) a deep-dive doc in `docs/`.

| Module | What it covers | Routes (in `main.py`) | Per-source doc | Auth |
|--------|---------------|----------------------|----------------|------|
| **`arxiv.py`** | arXiv — 2M+ scientific preprints (Atom XML → records) | `/arxiv/search`, `/arxiv/{arxiv_id}` | `docs/ARXIV_API.md` | none |
| **`bls.py`** | BLS — employment, wages, CPI, occupational | `/bls/{series_id}`, `POST /bls/batch` | `docs/BLS.md` | `BLS_API_KEY` (optional) |
| **`census.py`** | Census Bureau — demographics, ACS | `/census/population`, `/census/income`, `/census/acs` | `docs/CENSUS.md` | `CENSUS_API_KEY` (required; client now sends it — set a *valid* key) |
| **`clinicaltrials.py`** | ClinicalTrials.gov — 500K+ trials | `/clinical-trials`, `/clinical-trials/{nct_id}` | `docs/CLINICAL_TRIALS.md` | none |
| **`congress_gov.py`** | Congress.gov — bills, members, votes | `/congress/bills`, `/congress/bill/...`, `/congress/members`, `/congress/votes` | `docs/CONGRESS.md` | `CONGRESS_API_KEY` (DEMO_KEY fallback) |
| **`cross_reference.py`** | Cross-source aggregator | `/cross-reference/company/{name}`, `/cross-reference/politician/{last_name}` | — | inherits from underlying clients |
| **`edgar.py`** | SEC EDGAR — corporate filings, XBRL, full-text search, raw documents | `/edgar/company/{cik}`, `/edgar/financials/{cik}`, `/edgar/concept/{cik}/{concept}`, `/edgar/frames/{concept}`, `/edgar/search`, `/edgar/submissions/{filename}`, `/edgar/document/{cik}/{accession}/{document}`, `/edgar/cik/{ticker}` | `docs/EDGAR_API.md` | `SEC_USER_AGENT` (required, "Name email") |
| **`eia.py`** | EIA — energy production, prices, electricity, gas | `/eia`, `/eia/gas-prices`, `/eia/electricity`, `/eia/{route:path}` | `docs/EIA.md` | `EIA_API_KEY` (DEMO_KEY fallback) |
| **`fda.py`** | openFDA — drug events, recalls, food recalls | `/fda/drug-events`, `/fda/drug-recalls`, `/fda/food-recalls` | `docs/FDA.md` | none |
| **`fec.py`** | FEC — campaign finance, candidates, contributions | `/fec/candidates`, `/fec/contributions`, `/fec/totals` | `docs/FEC.md` | `FEC_API_KEY` (DEMO_KEY fallback) |
| **`federal_register.py`** | Federal Register — rules, notices, executive orders | `/federal-register`, `/federal-register/{doc_number}` | `docs/FEDERAL_REGISTER.md` | none |
| **`fema.py`** | OpenFEMA — disasters, grants, flood claims | `/fema/disasters`, `/fema/grants`, `/fema/flood-claims` | `docs/FEMA.md` | none |
| **`fred.py`** | FRED — 800K+ economic time series | `/fred/{series_id}`, `/fred/series/{series_id}`, `/fred?q=...` | `docs/FRED.md` | `FRED_API_KEY` (required) |
| **`house_fd.py`** | House Financial Disclosures — member/candidate trades, report PDFs | `/house-disclosures/members`, `/house-disclosures/candidates`, `/house-disclosures/pdf` | `docs/HOUSE_FD_API.md` | none (scrapes HTML) |
| **`jefs.py`** | JEFS — Judicial Financial Disclosures (federal judges) | **DISABLED 2026-06-11** (routes commented out in `main.py`) | `docs/JEFS_API.md` | session + Playwright reCAPTCHA; user must provide real credentials |
| **`nara.py`** | NARA — US National Archives Catalog (all record groups + the 14 presidential libraries) | `/nara/search`, `/nara/record/{na_id}` | `docs/NARA_API.md` | none (keyless `/proxy` gateway) |
| **`nasdaq.py`** | Nasdaq.com — quote, history, dividends, financials, insider trades, calendars, screener (unofficial) | `/nasdaq/quote/{ticker}`, `/nasdaq/price/{ticker}`, `/nasdaq/history/{ticker}`, `/nasdaq/dividends/{ticker}`, `/nasdaq/financials/{ticker}`, `/nasdaq/insider-trades/{ticker}`, `/nasdaq/earnings-surprise/{ticker}`, `/nasdaq/calendar/earnings`, `/nasdaq/calendar/ipo`, `/nasdaq/screener` | `docs/NASDAQ_API.md` | browser-like `User-Agent` only |
| **`nsarchive.py`** | National Security Archive (GWU NGO, ≠ NARA) — Virtual Reading Room declassified docs (HTML scrape, brittle) | `/nsarchive/search`, `/nsarchive/document/{doc_id}` | `docs/NSARCHIVE_API.md` | none (scrapes HTML) |
| **`scholar.py`** | Google Scholar — citation-ranked paper search (vendored `sort-google-scholar`, brittle) | `/scholar/search` | `docs/SCHOLAR_API.md` | none (scrapes HTML; Google blocks with CAPTCHA/429) |
| **`smithsonian.py`** | Smithsonian Open Access (EDAN) — 11M+ museum/library/archive records | `/smithsonian/search`, `/smithsonian/object/{id}`, `/smithsonian/category/{category}/search`, `/smithsonian/terms/{category}`, `/smithsonian/stats` | `docs/SMITHSONIAN_API.md` | `SMITHSONIAN_API_KEY` (DEMO_KEY fallback) |
| **`treasury.py`** | Treasury Fiscal Data — debt, rates, exchange | `/treasury/debt`, `/treasury/rates`, `/treasury/exchange` | `docs/TREASURY.md` | none |
| **`usaspending.py`** | USAspending — federal contracts, grants ($6T+/yr) | `/usaspending/agencies`, `/usaspending/search`, `/usaspending/by-agency` | `docs/USASPENDING.md` | none |
| **`wilson.py`** | Wilson Center Digital Archive — LOCAL mirror of 16,756 declassified documents (SQLite + FTS5; live site is DNS-dead) | **DISABLED 2026-07-02** (routes commented out in `main.py`; `data/wilson.db` not distributed) | `docs/WILSON_DIGITAL_ARCHIVE_API.md` | none (local data) |
| **`yfin.py`** | Yahoo Finance via `yfinance` — fundamentals, news, options, holdings, earnings | `/yfinance/info/{ticker}`, `/yfinance/history/{ticker}`, `/yfinance/news/{ticker}`, `/yfinance/recommendations/{ticker}`, `/yfinance/holders/{ticker}`, `/yfinance/financials/{ticker}`, `/yfinance/dividends/{ticker}`, `/yfinance/earnings/{ticker}`, `/yfinance/options/{ticker}` | `docs/YFINANCE_API.md` | none (crumb handled internally) |

**Total**: 21 active upstream sources + 1 cross-reference aggregator + 2 disabled sources (JEFS, Wilson) = **24 client modules, 82 routes**. The interactive Swagger UI at `/docs` (HTTP Basic auth) is the always-in-sync endpoint reference; its rich app description documents the API key and the response envelope, and each source has a tag description.

## Reference documentation in `docs/`

Each file is a deep-dive on a specific upstream — quirks, undocumented behavior, response shapes, common pitfalls. Check these before guessing about external API behavior:

| Doc | Covers |
|-----|--------|
| `docs/API_GUIDE.md` | **Agent-facing API guide** — "which endpoint for which information" routing map + a keyword-rich description and the parameters for every endpoint (no app architecture). Curated descriptions live in `scripts/gen_api_guide.py`; `docs/endpoints.csv` is the same data, flat. Regenerate with `python -m scripts.gen_api_guide`. |
| `docs/EDGAR_API.md` | SEC EDGAR — submissions, company concepts, XBRL frames, full-text search. The Frames API quirks (period format `CYxxxxQxI`), ticker→CIK resolution, rate limit (10/sec). |
| `docs/<SOURCE>.md` (FRED, BLS, CENSUS, TREASURY, FEC, CONGRESS, FDA, CLINICAL_TRIALS, EIA, FEMA, FEDERAL_REGISTER, USASPENDING) | Per-source skill docs (YAML frontmatter + endpoints + params + quirks), generated by `scripts/gen_source_docs.py`. The router `docs/API_GUIDE.md` links to them. (Split out of the former `GOV_APIS.md`.) |
| `docs/UNWIRED_RESEARCH.md` | Researched-but-not-wired gov APIs (SAM.gov, PatentsView) — kept for future wiring. |
| `docs/HOUSE_FD_API.md` | House Financial Disclosures — undocumented form-POST endpoint, response shape (HTML table), how `house_fd.py` parses it. |
| `docs/JEFS_API.md` | Judicial Financial Disclosures (pub.jefs.uscourts.gov) — session-based, reCAPTCHA-protected, no public REST API. How `jefs.py` uses Playwright for registration and then session-based POSTs for search/download. |
| `docs/SENATE_EFD_API.md` | Senate Financial Disclosures — not yet wired into a client, but research is here. Includes session-based auth model. |
| `docs/NASDAQ_API.md` | Nasdaq.com unofficial API — `/info`, `/summary`, `/historical`, `/dividends` endpoints. String-encoded numbers (`"5,480,000,000,000"`), browser UA requirement, OTC coverage gaps. |
| `docs/WILSON_DIGITAL_ARCHIVE_API.md` | Wilson Center Digital Archive — now served from a LOCAL mirror (live site is DNS-dead). Mirror tarball layout, the `scripts/build_wilson_index.py` indexer, `data/wilson.db` (SQLite + FTS5), local routes, metadata-only downloads. |
| `docs/SMITHSONIAN_API.md` | Smithsonian Open Access (EDAN) API — base `api.si.edu/openaccess/api/v1.0`, `api_key` auth, search/content/category/terms/stats endpoints, `{status, responseCode, response:{rows,facets,rowCount}}` envelope. |
| `docs/NARA_API.md` | National Archives Catalog — keyless `catalog.archives.gov/proxy` gateway (the SPA's own endpoint), mandatory browser fetch headers, `records/search?q/limit/page` + `?naId=`, `body.hits.hits[]._source.record` envelope, `page` not `offset`. |
| `docs/NSARCHIVE_API.md` | National Security Archive (GWU NGO, **not** NARA) — has no API; Drupal 10 Virtual Reading Room HTML scrape. `search_api_fulltext` GET search + `/document/{id-slug}` pages, selectolax parsing anchors, brittle; full corpus is the paywalled DNSA. |
| `docs/YFINANCE_API.md` | yfinance Python wrapper — sync→async pattern, DataFrame→records conversion, period/interval values, options-chain mechanics. |
| `docs/ARXIV_API.md` | arXiv query API — single Atom-XML endpoint, `search_query` field prefixes, feedparser parsing, id-list fetches. |
| `docs/SCHOLAR_API.md` | Google Scholar via vendored `sort-google-scholar` — scraping selectors, citation ranking, CAPTCHA/429 brittleness. |
| `docs/obsidian-help/` | Local-only clone of the `obsidian-help` repo (git-ignored, not in the public repo) — reference for Obsidian features when working on the local research vault. |

When adding a new API client, **write a new `docs/<SOURCE>_API.md`** alongside the code if the upstream has quirks worth remembering.

## Architecture

### Layout

- `app/main.py` — Every route is declared here, grouped by source under `# ── X ──` section comments. Each route has `tags=["X"]` so Swagger UI groups them in collapsible sections. Routes are 1–3 lines: validate query params, `await client.fn(...)`, return the result.
- `app/clients/` — One module per upstream API. Each defines a `BASE` URL and a few async functions.
- `app/clients/__init__.py` — Provides `get_client()` (shared `httpx.AsyncClient`, 30s timeout, process singleton), `safe_get` / `safe_post` helpers that wrap try/except + `raise_for_status` + json() + error-dict, and the `UpstreamJSON = dict | list` type alias.
- `app/clients/cross_reference.py` — Aggregates multiple upstreams (used by `/cross-reference/*` routes). Calls other client modules via `asyncio.gather` wrapped in `_safe(...)` so one bad source doesn't break the response.
- `app/clients/yfin.py` — yfinance wrapper. yfinance is synchronous; each call is dispatched via `asyncio.to_thread()` to keep the event loop free. DataFrames are converted to records-orientation lists.
- `app/config.py` — Loads `.env` at import time and exposes a `cfg` singleton with API keys.
- `app/middleware.py` — `ResponseEnvelopeMiddleware` rewrites every JSON response into `{meta: {source, endpoint, timestamp, status}, data, error}`. Skips `/openapi.json`, `/docs`, `/redoc`, `/docs/oauth2-redirect` (FastAPI's auto-doc paths must pass through raw). Non-JSON content-types also pass through unwrapped — the raw-bytes routes (`/edgar/document/...`, `/house-disclosures/pdf`) rely on this.
- `app/cache.py` — In-memory TTL cache and `@cached(ttl_seconds)` decorator. **Defined but not wired** to any client; TTL constants documented per source.
- `app/resilience.py` — Tenacity-based retry helpers (`resilient_get`, `resilient_post`). **Defined but not used** — every client uses `get_client().get(...)` directly via `safe_get`.
- `app/routers/` — Empty placeholder. All routing is in `main.py`.
- `docs/` — Per-source API reference docs. See the **Reference documentation** section above for the full list and what each covers.
- `tests/` — `test_edgar_endpoints.py` (integration tests). `tests/reports/` holds historical run outputs.
- `research/` — Ad-hoc local analyses (git-ignored, not in the repo). Not part of the runtime.

### Client module contract

Every client function returns either upstream JSON or the **error dict** below. Most clients accomplish this through the `safe_get` / `safe_post` helpers in `app/clients/__init__.py`:

```python
from . import UpstreamJSON, safe_get

async def some_endpoint(arg: str) -> UpstreamJSON:
    return await safe_get(f"{BASE}/path", "<source>", params={...})
```

`safe_get` returns either the upstream JSON or `{"error": True, "source": "<src>", "upstream_status": <int>, "message": "<str>"}`. `upstream_status` is the HTTP status from the failed upstream call, `0` for connection/parse/timeout errors, or set explicitly (e.g. EDGAR's `_by_cik` sets it to `404` for unknown tickers).

`ResponseEnvelopeMiddleware` inspects `data.get("error") is True` to set `meta.status = "error"` and populate the top-level `error` field, then maps the response HTTP status:

- **Success** → keep `response.status_code` (200 unless route changed it)
- **Upstream 4xx error** → pass-through (404 stays 404)
- **Upstream 5xx / timeout / connect-error / status=0** → `502 Bad Gateway`

**Do not raise from client functions.** Return the error dict instead. `HTTPException` doesn't currently fit because the middleware reads `data.error`, not HTTP status — adopting it would require either (a) changing middleware to infer error state from HTTP status, or (b) registering a global `HTTPException` handler that converts to error-dict shape. Both are real refactors; current pattern works.

### Client-specific wrinkles

- **EDGAR**: `_ticker_to_cik(ticker)` converts symbols like `AAPL` → CIK by fetching `sec.gov/files/company_tickers.json` on first use; result is cached in a module-level dict for the process lifetime. All EDGAR endpoints accept either form. Local ticker-resolution failures set `upstream_status=404` in the error dict.
- **yfinance**: synchronous library — all calls go through `asyncio.to_thread()`. DataFrames converted with `df.reset_index().to_dict(orient='records')`; NaN values become JSON `null`. yfinance is imported unmodified so `pip install --upgrade yfinance` propagates upstream fixes.
- **Nasdaq.com**: unofficial API. Requires browser-like `User-Agent` header (returns 401 without). String fields like `MarketCap` come back as `"5,553,872,968,719"` — strip commas + cast to int.
- **House Financial Disclosures**: upstream returns HTML, not JSON. Client parses tables with regex. Can't use `safe_get`; has its own try/except.
- **Wilson Center** (*disabled 2026-07-02* — routes commented out in `main.py`): serves a LOCAL mirror, not a live API (the live host is DNS-dead). Reads `data/wilson.db` (SQLite + FTS5, not distributed with the repo) built once by `scripts/build_wilson_index.py` from a downloaded HTML scrape; sync `sqlite3` calls run via `asyncio.to_thread`. Returns locally-built JSON, not upstream JSON — an intentional exception to the pass-through rule.
- **NSArchive**: HTML scrape of the GWU NGO's Virtual Reading Room (it has no API). Like `house_fd`, can't use `safe_get`; parses Drupal markup with `selectolax` and has its own try/except returning the error-dict. Brittle (markup changes break parsing). Distinct from `nara` (the government agency).
- **arXiv**: upstream returns Atom XML, not JSON — parsed with `feedparser` into records; can't use `safe_get`. An intentional exception to the pass-through rule.
- **Scholar**: vendored from `WittmannF/sort-google-scholar` (MIT) — the one deliberate exception to the "don't vendor" convention: upstream is an interactive CLI tool (its CAPTCHA fallback blocks on `input()`), unusable in a server unmodified. Google blocks scraping (CAPTCHA/429) → expect error-dicts. See the module docstring for what was kept vs dropped.

### Adding a new endpoint

1. Add an async function to the relevant `app/clients/<source>.py` (or create a new module — register the import in `main.py`).
2. Use `safe_get` / `safe_post` for HTTP, read keys from `cfg`, declare `-> UpstreamJSON` return type.
3. Add a route in `main.py` that calls it. **Include `tags=["X"]`** so Swagger UI groups it. Use FastAPI `Query(...)` for limits (`le=100` or `le=1000` are the common caps).
4. If you add a new source, also add a TTL entry in `app/cache.py` `TTL` dict for future use.
5. Add a per-source doc in `docs/` if the API has non-obvious quirks.

### Environment

`.env` is loaded from the project root by `app/config.py`. Keys are listed there; `FEC_API_KEY`, `CONGRESS_API_KEY`, `EIA_API_KEY`, and `SMITHSONIAN_API_KEY` fall back to `"DEMO_KEY"` (works with low rate limits), the rest default to empty strings. `SEC_USER_AGENT` is required by the SEC and must be a real `"Name email"` string — EDGAR returns 403 without it.

**API-key auth (DataGod's own endpoints).** `DATAGOD_API_KEY` gates every route: requests must send an `X-API-Key: <key>` header. Enforced by `app/auth.py` (FastAPI's built-in `APIKeyHeader`) wired as an app-level dependency in `main.py`. Public (no auth): `/health` (`auth.PUBLIC_PATHS`). The interactive docs (`/docs`, `/redoc`, `/openapi.json`) are custom routes protected by **HTTP Basic** (`auth.require_docs_auth`: user `DATAGOD_DOCS_USER`, password `DATAGOD_DOCS_PASSWORD` — both fall back to `datagod` / `DATAGOD_API_KEY`), and are exempt from the `X-API-Key` check (`auth.DOCS_PATHS`). A missing/invalid key returns **401** in the standard error envelope. Set it in `.env` locally and as a Coolify env var in production; the service fails **closed** if the key is unset. The `.env` file is git-ignored — never commit it.

**Census key**: `census.py` now sends `cfg.CENSUS_API_KEY` (fixed 2026-06-11; it previously never sent the key → keyless request → Census "Invalid Key" redirect → JSON parse error "Expecting value" → 502). The endpoint still needs a **valid** `CENSUS_API_KEY`: Census rejects invalid keys with the same Invalid-Key page, so set a working key in `.env` / Coolify.

## Conventions specific to this repo

- **No transformation of upstream responses.** Every client returns whatever the source returned. The envelope wrapping is the only mutation.
- **Async only.** Every client function is `async`; sync libraries (yfinance, pandas) go through `asyncio.to_thread()`.
- **One shared httpx client.** Don't create per-request clients — reuse `get_client()` so connection pooling works.
- **Tag every route.** All `@app.get(...)` decorators include `tags=["X"]` so Swagger UI groups them in collapsible sections.
- **HTTP semantics matter.** Don't return 200 with `error: true` body and call it done. The middleware translates `upstream_status` into proper HTTP codes; if you bypass the helper you bypass the codes.
- **The EDGAR Frames endpoint is the cross-company killer feature** (one concept across all 2,600+ filers in one call). Preserve its shape when modifying.
- **yfinance lives untouched.** Don't fork or vendor; rely on PyPI updates.

## SEC EDGAR endpoints we use (from the SEC's official APIs page)

Per [sec.gov/search-filings/edgar-application-programming-interfaces](https://www.sec.gov/search-filings/edgar-application-programming-interfaces):

| SEC official endpoint | DataGod client function |
|----------------------|------------------------|
| `data.sec.gov/submissions/CIK*.json` | `edgar.company` |
| `data.sec.gov/api/xbrl/companyfacts/CIK*.json` | `edgar.financials` |
| `data.sec.gov/api/xbrl/companyconcept/...` | `edgar.concept` |
| `data.sec.gov/api/xbrl/frames/...` | `edgar.frames` |
| `efts.sec.gov/LATEST/search-index` (full-text) | `edgar.search_filings` |
| Bulk ZIPs (companyfacts.zip, submissions.zip) | Not used; live API is enough |

The `api.edgarfiling.sec.gov` API is a **separate filing-submission API** for sending data **to** the SEC (10-Ks, 10-Qs etc.); requires auth tokens; not applicable for read-only data access.
