# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

DataGod is a FastAPI service that unifies 41 free data sources behind one HTTP API: 16 US government sources (FRED, SEC EDGAR, USAspending, Census, BLS, Treasury, FEC, Congress.gov, FDA, ClinicalTrials.gov, EIA, FEMA, Federal Register, House Financial Disclosures, Smithsonian Open Access, National Archives (NARA)), 10 global/international sources (World Bank, IMF, Eurostat, ECB, UN Comtrade, UCDP, USGS Earthquakes, NWS, NASA EONET, Wikipedia), 2 markets sources (Nasdaq.com, Yahoo Finance via yfinance), 2 research sources (arXiv, Google Scholar), 3 keyless media/video sources (NASA Image and Video Library, Internet Archive, Wikimedia Commons — public-domain/CC video harvesting, served under `/nasa`, `/archive`, `/commons`), the non-governmental National Security Archive (GWU; Virtual Reading Room scrape), 5 declassified/military-archive sources (CIA FOIA Electronic Reading Room and the FBI Vault, both via the Wayback mirror — see `app/clients/_wayback.py`; State Department FRUS; UK National Archives Discovery; the FAS Intelligence Resource Program — served under `/cia`, `/vault`, `/frus`, `/tna`, `/fas`), the Wilson Center Digital Archive (a LOCAL SQLite mirror — the deployment mounts `data/wilson.db`, which isn't distributed), and NewsNow (self-hosted trending-boards aggregator — ~50 hot lists: Hacker News, GitHub trending, Product Hunt, Weibo/Zhihu/Douyin and other CN boards; served at `/trending`). One more source lives in the codebase but is currently **disabled**: JEFS (judicial disclosures; needs Playwright + reCAPTCHA). Routes are thin pass-throughs; each upstream gets a dedicated async client module that returns the upstream's JSON (or DataFrame-as-records, for yfinance) unchanged.

## Commands

```bash
# Run the server (auto-reload during dev)
.venv/bin/uvicorn app.main:app --reload --port 8000

# Install deps (requirements-dev.txt adds pytest on top)
.venv/bin/pip install -r requirements-dev.txt

# Offline unit tests — no network, no server (upstreams faked with httpx.MockTransport)
.venv/bin/python -m pytest

# Docker
docker build -t datagod .
docker run -p 8000:8000 --env-file .env datagod

# Live integration tests (network; scripts, not pytest)
.venv/bin/python tests/test_all_endpoints.py      # smoke-tests every endpoint; target = $DATAGOD_BASE_URL (default http://localhost:8000)
.venv/bin/python tests/test_edgar_endpoints.py    # requires server running on localhost:8000
.venv/bin/python tests/test_nsarchive_search.py   # no server; needs network to nsarchive.gwu.edu
.venv/bin/python tests/test_arxiv.py              # no server; calls the arxiv client against live export.arxiv.org
.venv/bin/python tests/test_scholar.py            # no server; live Google Scholar (expect CAPTCHA/429 failures)
.venv/bin/python tests/test_intel_archives.py     # no server; live TNA, FRUS, CIA + Vault (Wayback throttling soft-passes)

# Interactive API exploration (server must be running)
open http://localhost:8000/docs   # HTTP Basic prompt: user "datagod", password = DATAGOD_DOCS_PASSWORD (falls back to DATAGOD_API_KEY)
```

Two kinds of tests (no linter or type-checker is configured):
- `tests/unit/` — the **offline pytest suite** (`pytest.ini` collects only this directory). Fakes every upstream with `httpx.MockTransport` (`upstream` fixture in `conftest.py`) and drives the real app through `TestClient` (`api` fixture). Covers the envelope/status contract, auth, credential redaction, the SSRF guard, the retry policy, and per-client regressions. Add a test here for every client fix.
- The `tests/*.py` scripts are **live** — they hit real upstreams, run at import time, and are run with `python tests/<file>.py`, never by pytest:
- `tests/test_all_endpoints.py` — smoke-tests every endpoint over HTTP (needs a running server + `DATAGOD_API_KEY` in `.env`), prints a grouped pass/fail table, ending with a "Contract" group of negative checks (SSRF refusal, 422/404 envelopes, Nasdaq in-body errors, missing key). JEFS is skipped (disabled); Wilson errors unless `data/wilson.db` is mounted.
- `tests/test_edgar_endpoints.py` — hits the running server with httpx, prints a pass/fail table, writes `tests/reports/edgar_test_results.json`.
- `tests/test_nsarchive_search.py` — calls the `nsarchive` client directly against the live Virtual Reading Room (no server needed) and verifies its search behavior: the `search_api_fulltext` GET defaults to **OR** (the site's "Search Tips" wrongly say AND), while explicit `AND`/`OR`/`NOT`/parentheses/`*`/`"phrase"` and `field_date[max]` bounds all work; `sort_by` is ignored (always newest-first). See `docs/NSARCHIVE_API.md`.
- `tests/test_arxiv.py` / `tests/test_scholar.py` / `tests/test_intel_archives.py` — call those clients directly against the live upstreams (no server needed).

## Available API clients

43 client modules in `app/clients/` (plus the shared `_wayback.py` helper). Each has matching routes in `main.py` and (for non-trivial APIs) a deep-dive doc in `docs/`.

| Module | What it covers | Routes (in `main.py`) | Per-source doc | Auth |
|--------|---------------|----------------------|----------------|------|
| **`arxiv.py`** | arXiv — 2M+ scientific preprints (Atom XML → records) | `/arxiv/search`, `/arxiv/{arxiv_id}` | `docs/ARXIV_API.md` | none |
| **`bls.py`** | BLS — employment, wages, CPI, occupational | `/bls/{series_id}`, `POST /bls/batch` | `docs/BLS.md` | `BLS_API_KEY` (optional; switches to the v2 API — v1 ignores keys) |
| **`cia.py`** | CIA FOIA Electronic Reading Room — via the Wayback mirror (cia.gov's TLS-fingerprint bot wall blocks all server clients; newest usable 200 capture per page, skipping stored 403s and bm-verify interstitials) | `/cia/collections`, `/cia/collection/{slug}`, `/cia/document/{doc_path}` | — | none |
| **`census.py`** | Census Bureau — demographics, ACS | `/census/population`, `/census/income`, `/census/acs` | `docs/CENSUS.md` | `CENSUS_API_KEY` (required; client now sends it — set a *valid* key) |
| **`clinicaltrials.py`** | ClinicalTrials.gov — 500K+ trials | `/clinical-trials`, `/clinical-trials/{nct_id}` | `docs/CLINICAL_TRIALS.md` | none |
| **`commons.py`** | Wikimedia Commons — video-file search with direct file URLs + per-file license (CC-BY/CC-BY-SA/PD) | `/commons/search` | `docs/COMMONS_API.md` | none (client sends a polite User-Agent) |
| **`comtrade.py`** | UN Comtrade — global goods-trade flows (keyless public preview, ≤500 records, rate-limited) | `/comtrade` | `docs/COMTRADE.md` | none |
| **`congress_gov.py`** | Congress.gov — bills, members, votes | `/congress/bills`, `/congress/bill/...`, `/congress/members`, `/congress/votes` | `docs/CONGRESS.md` | `CONGRESS_API_KEY` (DEMO_KEY fallback) |
| **`cross_reference.py`** | Cross-source aggregator | `/cross-reference/company/{name}`, `/cross-reference/politician/{last_name}` | — | inherits from underlying clients |
| **`ecb.py`** | ECB Data Portal — euro-area FX, inflation, rates via SDMX | `/ecb/{flow_ref}/{key}` | `docs/ECB.md` | none |
| **`edgar.py`** | SEC EDGAR — corporate filings, XBRL, full-text search, raw documents | `/edgar/company/{cik}`, `/edgar/financials/{cik}`, `/edgar/concept/{cik}/{concept}`, `/edgar/frames/{concept}`, `/edgar/search`, `/edgar/submissions/{filename}`, `/edgar/document/{cik}/{accession}/{document}`, `/edgar/cik/{ticker}` | `docs/EDGAR_API.md` | `SEC_USER_AGENT` (required, "Name email") |
| **`eia.py`** | EIA — energy production, prices, electricity, gas | `/eia`, `/eia/gas-prices`, `/eia/electricity`, `/eia/{route:path}` | `docs/EIA.md` | `EIA_API_KEY` (DEMO_KEY fallback) |
| **`eonet.py`** | NASA EONET — global natural events (wildfires, severe storms, volcanoes) | `/eonet/events`, `/eonet/categories` | `docs/EONET.md` | none |
| **`eurostat.py`** | Eurostat — official EU statistics (JSON-stat; dimension filters pass through) | `/eurostat/{dataset}` | `docs/EUROSTAT.md` | none |
| **`fda.py`** | openFDA — drug events, recalls, food recalls | `/fda/drug-events`, `/fda/drug-recalls`, `/fda/food-recalls` | `docs/FDA.md` | none |
| **`fec.py`** | FEC — campaign finance, candidates, contributions | `/fec/candidates`, `/fec/contributions`, `/fec/totals` | `docs/FEC.md` | `FEC_API_KEY` (DEMO_KEY fallback) |
| **`federal_register.py`** | Federal Register — rules, notices, executive orders | `/federal-register`, `/federal-register/{doc_number}` | `docs/FEDERAL_REGISTER.md` | none |
| **`fema.py`** | OpenFEMA — disasters (v2), HMGP grants (v3), NFIP flood claims (`NfipClaims` v3) | `/fema/disasters`, `/fema/grants`, `/fema/flood-claims` | `docs/FEMA.md` | none |
| **`fas.py`** | FAS Intelligence Resource Program (irp.fas.org) — mirrored intelligence-community documents: agency pages, collection programs, official documents, DoD directives (static-HTML scrape; non-HTML documents answer 415 with their direct URL) | `/fas/sections`, `/fas/index/{path}`, `/fas/page/{path}` | — | none |
| **`fred.py`** | FRED — 800K+ economic time series | `/fred/{series_id}`, `/fred/series/{series_id}`, `/fred?q=...` | `docs/FRED.md` | `FRED_API_KEY` (required) |
| **`frus.py`** | Foreign Relations of the United States (history.state.gov) — 500+ volumes of declassified diplomatic/covert-action records (server-rendered HTML scrape) | `/frus/search`, `/frus/document/{volume}/{doc}` | — | none |
| **`house_fd.py`** | House Financial Disclosures — member/candidate trades, report PDFs | `/house-disclosures/members`, `/house-disclosures/candidates`, `/house-disclosures/pdf` | `docs/HOUSE_FD_API.md` | none (scrapes HTML; `/pdf` only fetches the disclosures host) |
| **`imf.py`** | IMF SDMX-JSON — macro time series (IFS, DOT, BOP…); legacy host currently DNS-dead — see doc | `/imf/{database}/{key}`, `/imf/structure/{database}` | `docs/IMF.md` | none |
| **`internetarchive.py`** | Internet Archive — archival films/newsreels search (movies-scoped) + per-item files with download paths; license per item (`licenseurl`) | `/archive/search`, `/archive/item/{identifier}` | `docs/INTERNET_ARCHIVE_API.md` | none |
| **`jefs.py`** | JEFS — Judicial Financial Disclosures (federal judges) | **DISABLED 2026-06-11** (routes commented out in `main.py`) | `docs/JEFS_API.md` | session + Playwright reCAPTCHA; user must provide real credentials |
| **`nara.py`** | NARA — US National Archives Catalog (all record groups + the 14 presidential libraries) | `/nara/search`, `/nara/record/{na_id}` | `docs/NARA_API.md` | none (keyless `/proxy` gateway) |
| **`nasa_images.py`** | NASA Image and Video Library — public-domain space/science media with direct mp4 renditions | `/nasa/search`, `/nasa/asset/{nasa_id}` | `docs/NASA_IMAGES_API.md` | none |
| **`nasdaq.py`** | Nasdaq.com — quote, history, dividends, financials, insider trades, calendars, screener (unofficial) | `/nasdaq/quote/{ticker}`, `/nasdaq/price/{ticker}`, `/nasdaq/history/{ticker}`, `/nasdaq/dividends/{ticker}`, `/nasdaq/financials/{ticker}`, `/nasdaq/insider-trades/{ticker}`, `/nasdaq/earnings-surprise/{ticker}`, `/nasdaq/calendar/earnings`, `/nasdaq/calendar/ipo`, `/nasdaq/screener` | `docs/NASDAQ_API.md` | browser-like `User-Agent` only; failures arrive as HTTP 200 + `status.rCode` (mapped to the error-dict) |
| **`newsnow.py`** | NewsNow (self-hosted, image pinned `v0.0.41`) — ~50 trending/hot boards: HN, GitHub trending, Product Hunt, Weibo/Zhihu/Douyin hot searches, CN finance wires | `/trending`, `/trending/{source_id}` | `docs/API_GUIDE.md` § Trending | `NEWSNOW_BASE_URL` (required; Coolify-internal `http://newsnow:4444`) |
| **`nsarchive.py`** | National Security Archive (GWU NGO, ≠ NARA) — Virtual Reading Room declassified docs (HTML scrape, brittle) | `/nsarchive/search`, `/nsarchive/document/{doc_id}` | `docs/NSARCHIVE_API.md` | none (scrapes HTML) |
| **`nws.py`** | US National Weather Service — active weather alerts | `/nws/alerts` | `docs/NWS.md` | none (User-Agent required — client sends it) |
| **`scholar.py`** | Google Scholar — citation-ranked paper search (vendored `sort-google-scholar`, brittle) | `/scholar/search` | `docs/SCHOLAR_API.md` | none (scrapes HTML; Google blocks with CAPTCHA/429) |
| **`smithsonian.py`** | Smithsonian Open Access (EDAN) — 11M+ museum/library/archive records | `/smithsonian/search`, `/smithsonian/object/{id}`, `/smithsonian/category/{category}/search`, `/smithsonian/terms/{category}`, `/smithsonian/stats` | `docs/SMITHSONIAN_API.md` | `SMITHSONIAN_API_KEY` (DEMO_KEY fallback) |
| **`tna.py`** | UK National Archives Discovery — 32M+ record descriptions incl. KV (MI5), HS (SOE), DEFE, CAB series (official keyless JSON API; series filter = `sps.departments`, NOT `sps.recordSeries`) | `/tna/search`, `/tna/record/{record_id}` | — | none |
| **`treasury.py`** | Treasury Fiscal Data — debt, rates, exchange | `/treasury/debt`, `/treasury/rates`, `/treasury/exchange` | `docs/TREASURY.md` | none |
| **`ucdp.py`** | UCDP — georeferenced armed-conflict events (GED) | `/ucdp/gedevents` | `docs/UCDP.md` | `UCDP_ACCESS_TOKEN` (upstream began requiring a free token in 2026; 401 without) |
| **`usaspending.py`** | USAspending — federal contracts, grants ($6T+/yr) | `/usaspending/agencies`, `/usaspending/search`, `/usaspending/by-agency` | `docs/USASPENDING.md` | none |
| **`vault.py`** | FBI Vault — via the Wayback mirror (vault.fbi.gov 403s all server clients; shared `_wayback.py` picks the newest usable capture, gunzipping raw `id_` bodies) | `/vault/subjects`, `/vault/page/{path}` | — | none |
| **`usgs.py`** | USGS Earthquake Hazards — worldwide earthquake catalog (GeoJSON) | `/usgs/earthquakes` | `docs/USGS.md` | none |
| **`wikipedia.py`** | Wikipedia — page summaries, whole articles as plain text, full-text search, Wikimedia pageviews (every call waits out a 429) | `/wikipedia/summary/{title}`, `/wikipedia/article/{title}`, `/wikipedia/search`, `/wikipedia/pageviews/{title}` | `docs/WIKIPEDIA.md` | none (client sends a polite User-Agent) |
| **`wilson.py`** | Wilson Center Digital Archive — LOCAL mirror of 16,756 declassified documents (SQLite + FTS5; live site is DNS-dead) | `/wilson/documents`, `/wilson/document/{slug}` (re-enabled 2026-08-27; the deployment mounts `data/wilson.db`, else an error envelope with a build hint) | `docs/WILSON_DIGITAL_ARCHIVE_API.md` | none (local data) |
| **`worldbank.py`** | World Bank Open Data — 16K+ development indicators for every country | `/worldbank/{indicator}`, `/worldbank/countries` | `docs/WORLDBANK.md` | none |
| **`yfin.py`** | Yahoo Finance via `yfinance` — fundamentals, news, options, holdings, earnings | `/yfinance/info/{ticker}`, `/yfinance/history/{ticker}`, `/yfinance/news/{ticker}`, `/yfinance/recommendations/{ticker}`, `/yfinance/holders/{ticker}`, `/yfinance/financials/{ticker}`, `/yfinance/dividends/{ticker}`, `/yfinance/earnings/{ticker}`, `/yfinance/options/{ticker}` | `docs/YFINANCE_API.md` | none (crumb handled internally) |

**Total**: 41 active upstream sources + 1 cross-reference aggregator + 1 disabled source (JEFS) = **43 client modules, 119 routes**. The interactive Swagger UI at `/docs` (HTTP Basic auth) is the always-in-sync endpoint reference; its rich app description documents the API key and the response envelope, and each source has a tag description.

## Reference documentation in `docs/`

Each file is a deep-dive on a specific upstream — quirks, undocumented behavior, response shapes, common pitfalls. Check these before guessing about external API behavior:

| Doc | Covers |
|-----|--------|
| `docs/API_GUIDE.md` | **Agent-facing API guide** — "which endpoint for which information" routing map + a keyword-rich description and the parameters for every endpoint (no app architecture). Curated descriptions live in `scripts/gen_api_guide.py`; `docs/endpoints.csv` is the same data, flat. Regenerate with `python -m scripts.gen_api_guide`. |
| `docs/EDGAR_API.md` | SEC EDGAR — submissions, company concepts, XBRL frames, full-text search. The Frames API quirks (period format `CYxxxxQxI`), ticker→CIK resolution, rate limit (10/sec). |
| `docs/<SOURCE>.md` (FRED, BLS, CENSUS, TREASURY, FEC, CONGRESS, FDA, CLINICAL_TRIALS, EIA, FEMA, FEDERAL_REGISTER, USASPENDING) | Per-source skill docs (YAML frontmatter + endpoints + params + quirks), generated by `scripts/gen_source_docs.py`. The router `docs/API_GUIDE.md` links to them. (Split out of the former `GOV_APIS.md`.) |
| `docs/<SOURCE>.md` (WORLDBANK, IMF, EUROSTAT, ECB, COMTRADE, UCDP, USGS, NWS, EONET, WIKIPEDIA) | Global-tier per-source docs, hand-written in the same skill-doc format (not generated). Notable: IMF's legacy SDMX host is currently DNS-dead; UCDP now requires a free token (`UCDP_ACCESS_TOKEN`); Comtrade is the ≤500-record keyless preview. |
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
| `docs/NASA_IMAGES_API.md` | NASA Image and Video Library — keyless `images-api.nasa.gov` search + `/asset/{nasa_id}` manifests of direct mp4/srt/thumbnail URLs; everything public domain (credit "NASA"). |
| `docs/INTERNET_ARCHIVE_API.md` | Internet Archive — `advancedsearch.php` (Lucene queries, movies-scoped by default) + `/metadata/{identifier}` files list; download URL shape and the per-item `licenseurl` caveat (prelinger/newsreels are the PD targets). |
| `docs/COMMONS_API.md` | Wikimedia Commons — `generator=search` video-file search with `imageinfo` (direct URL, size, mime) + `extmetadata` license/author; webm-not-mp4 and pages-keyed-by-pageid quirks. |
| `docs/SCHOLAR_API.md` | Google Scholar via vendored `sort-google-scholar` — scraping selectors, citation ranking, CAPTCHA/429 brittleness. |
| `docs/obsidian-help/` | Local-only clone of the `obsidian-help` repo (git-ignored, not in the public repo) — reference for Obsidian features when working on the local research vault. |

When adding a new API client, **write a new `docs/<SOURCE>_API.md`** alongside the code if the upstream has quirks worth remembering.

## Architecture

### Layout

- `app/main.py` — Every route is declared here, grouped by source under `# ── X ──` section comments. Each route has `tags=["X"]` so Swagger UI groups them in collapsible sections. Routes are 1–3 lines: validate query params, `await client.fn(...)`, return the result.
- `app/clients/` — One module per upstream API. Each defines a `BASE` URL and a few async functions.
- `app/clients/__init__.py` — Provides `get_client()` (shared `httpx.AsyncClient`, 30s timeout, process singleton), `safe_get` / `safe_post` helpers that wrap try/except + `raise_for_status` + json() + error-dict, `error_dict(source, status, message)` and `_error(source, exc)` (the only sanctioned ways to build the error-dict — see the contract below), `json_or_error(response, source)`, `clean_text()` (whitespace collapse for scrapers), `RateLimiter` (sliding window: EDGAR 10/s, arXiv 1 per 3s — deliberately not aiolimiter, whose bucket allows ~2x bursts), and the `UpstreamJSON = dict | list` type alias.
- `app/clients/cross_reference.py` — Aggregates multiple upstreams (used by `/cross-reference/*` routes) via `asyncio.gather`. Clients return the error-dict rather than raising, so a failed source is detected by its payload: it goes into the response's `errors` map, is left out of `source_count`, and its slot holds None / []. Company names resolve to a CIK through `edgar.resolve_company` (ticker, CIK, or SEC title match); revenue is the newest full-year fact across the ASC 606 and legacy revenue tags; FEC is searched by name (`q`).
- `app/clients/yfin.py` — yfinance wrapper. yfinance is synchronous; each call is dispatched via `asyncio.to_thread()` to keep the event loop free. DataFrames are converted to records-orientation lists.
- `app/config.py` — Loads `.env` at import time and exposes a `cfg` singleton with API keys. Blank values count as unset (`_env`), so `FEC_API_KEY=` falls back to DEMO_KEY. `redact(text)` masks credential query params (`api_key=`, `key=`, `registrationkey=`, `token=`…) and every configured secret value.
- `app/middleware.py` — `ResponseEnvelopeMiddleware` rewrites every JSON response into `{meta: {source, endpoint, timestamp, status}, data, error}`. Skips `/openapi.json`, `/docs`, `/redoc`, `/docs/oauth2-redirect` (FastAPI's auto-doc paths must pass through raw). Non-JSON content-types also pass through unwrapped — the raw-bytes routes (`/edgar/document/...`, `/house-disclosures/pdf`) rely on this. Responses FastAPI produces itself with status ≥ 400 (422 validation, 404 route, 405 method) are error envelopes too, keeping their status; error messages are `redact()`ed; original headers (e.g. `Allow`) are carried over. Unhandled exceptions are answered by `main.unhandled_handler` as a 500 envelope.
- `app/cache.py` — In-memory TTL cache and `@cached(ttl_seconds)` decorator. **Defined but not wired** to any client; TTL constants documented per source. Keys are module-qualified and error-dicts are never cached. It is unbounded — if you wire it broadly, switch to `cachetools.TTLCache`.
- `app/resilience.py` — `get_with_retry()` (tenacity): retries 429/503 after the upstream's `Retry-After` (capped) else a backoff step, raising `Throttled` (carrying the last response, so the real status is reported) when retries run out. Used by `_wayback.py` (cia, vault; also retries transport errors) and `wikipedia.py`. `safe_get` itself does not retry.
- `app/routers/` — Empty placeholder. All routing is in `main.py`.
- `docs/` — Per-source API reference docs. See the **Reference documentation** section above for the full list and what each covers.
- `tests/` — `tests/unit/` is the offline pytest suite; the other `tests/*.py` are live-network scripts (see Commands). `tests/reports/` holds historical run outputs.
- `research/` — Ad-hoc local analyses (git-ignored, not in the repo). Not part of the runtime.

### Client module contract

Every client function returns either upstream JSON or the **error dict** below. Most clients accomplish this through the `safe_get` / `safe_post` helpers in `app/clients/__init__.py`:

```python
from . import UpstreamJSON, safe_get

async def some_endpoint(arg: str) -> UpstreamJSON:
    return await safe_get(f"{BASE}/path", "<source>", params={...})
```

`safe_get` returns either the upstream JSON or `{"error": True, "source": "<src>", "upstream_status": <int>, "message": "<str>"}`. `upstream_status` is the HTTP status from the failed upstream call, `0` for connection/parse/timeout errors, or set explicitly (e.g. EDGAR's `_by_cik` sets it to `404` for unknown tickers).

**Build error dicts only with `error_dict(source, status, message)` or `_error(source, exc)`** — never hand-format `str(exc)`. httpx exception text contains the full request URL, and FRED, EIA, FEC, Congress, Census, Smithsonian and BLS take their key as a query parameter: hand-formatted messages leaked those keys to API callers until 2026-11-04. Both helpers `redact()`, and `_error` also quotes the start of the upstream's own JSON/text error body (e.g. FRED's "The value for variable api_key is not registered"). The middleware redacts again as a safety net.

Upstreams that report failure **inside a 200** must be translated to the error-dict in the client, or the envelope says `success`: Nasdaq (`status.rCode` ≠ 200 → `upstream_status` = rCode), BLS (`status: REQUEST_NOT_PROCESSED` → 429 for the daily threshold, else 400), Census (302 to a key-error page), Wikipedia `/article` (missing page → 404).

`ResponseEnvelopeMiddleware` inspects `data.get("error") is True` to set `meta.status = "error"` and populate the top-level `error` field, then maps the response HTTP status:

- **Success** → keep `response.status_code` (200 unless route changed it)
- **Upstream 4xx error** → pass-through (404 stays 404)
- **Upstream 5xx / timeout / connect-error / status=0** → `502 Bad Gateway`

**Do not raise from client functions.** Return the error dict instead — it carries `source` and `upstream_status`, which drive the 4xx-passthrough / 502 mapping. (The middleware does treat any status ≥ 400 response as an error, which is how FastAPI's own 422/404/405 are reported, but that path keeps the raw status and has no source.)

### Client-specific wrinkles

- **EDGAR**: `_ticker_to_cik(ticker)` converts symbols like `AAPL` → CIK by fetching `sec.gov/files/company_tickers.json` on first use (lock-guarded, status-checked — a 403 from a missing `SEC_USER_AGENT` surfaces as 403); result is cached in module-level state for the process lifetime. All EDGAR endpoints accept either form. Local ticker-resolution failures set `upstream_status=404` in the error dict. `resolve_company()` additionally matches company names against SEC's titles (used by cross-reference only).
- **yfinance**: synchronous library — all calls go through `asyncio.to_thread()`. DataFrames converted with `df.reset_index().to_dict(orient='records')`; NaN values become JSON `null`. yfinance is imported unmodified so `pip install --upgrade yfinance` propagates upstream fixes.
- **Nasdaq.com**: unofficial API. Requires browser-like `User-Agent` header (returns 401 without). String fields like `MarketCap` come back as `"5,553,872,968,719"` — strip commas + cast to int. Failures arrive as HTTP 200 + `status.rCode` (mapped to the error-dict). `/financials` takes `frequency=1|2` only (the route maps annual/A and quarterly/Q); the IPO calendar takes a month (`YYYY-MM`).
- **House Financial Disclosures**: upstream returns HTML, not JSON. Client parses the result table with `selectolax` (entities decoded, `<th>` header row skipped). Can't use `safe_get`; has its own try/except. `/house-disclosures/pdf` resolves `path` against the disclosures host and refuses any other host (SSRF guard, 400).
- **Wilson Center** (*re-enabled 2026-08-27*; the deployment mounts `data/wilson.db`): serves a LOCAL mirror, not a live API (the live host is DNS-dead). Reads `data/wilson.db` (SQLite + FTS5, not distributed with the repo) built once by `scripts/build_wilson_index.py` from a downloaded HTML scrape; sync `sqlite3` calls run via `asyncio.to_thread`. Returns locally-built JSON, not upstream JSON — an intentional exception to the pass-through rule.
- **NSArchive**: HTML scrape of the GWU NGO's Virtual Reading Room (it has no API). Like `house_fd`, can't use `safe_get`; parses Drupal markup with `selectolax` and has its own try/except returning the error-dict. Brittle (markup changes break parsing). Distinct from `nara` (the government agency).
- **BLS**: v1 without a key, v2 with `BLS_API_KEY` (v1 ignores `registrationkey`). `REQUEST_NOT_PROCESSED` bodies (HTTP 200) become the error-dict.
- **FEMA**: dataset versions differ per dataset — disasters v2, HMGP grants v3, NFIP claims `NfipClaims` v3. Check `/api/open/v1/OpenFemaDataSets` (`version`, `depDate`) when one 404s. OData `$filter` literals are quote-escaped (`_quoted`).
- **FAS**: static-HTML scrape; `_get` refuses non-HTML content types (index pages link PDFs/xlsx) with 415 + the direct URL instead of returning binary noise as text.
- **Wikimedia (Wikipedia, Commons)**: blocks by TLS fingerprint + IP reputation as well as User-Agent: from some cloud egress IPs the action API, pageviews and Commons answer 403 "respect our robot policy" to Python clients whatever the UA (curl from the same IP passes). Not fixable in code without impersonating a browser — don't.
- **arXiv**: upstream returns Atom XML, not JSON — parsed with `feedparser` into records; can't use `safe_get`. An intentional exception to the pass-through rule.
- **Scholar**: vendored from `WittmannF/sort-google-scholar` (MIT) — the one deliberate exception to the "don't vendor" convention: upstream is an interactive CLI tool (its CAPTCHA fallback blocks on `input()`), unusable in a server unmodified. Google blocks scraping (CAPTCHA/429) → expect error-dicts. See the module docstring for what was kept vs dropped.

### Adding a new endpoint

1. Add an async function to the relevant `app/clients/<source>.py` (or create a new module — register the import in `main.py`).
2. Use `safe_get` / `safe_post` for HTTP, read keys from `cfg`, declare `-> UpstreamJSON` return type.
3. Add a route in `main.py` that calls it. **Include `tags=["X"]`** so Swagger UI groups it. Use FastAPI `Query(...)` for limits (`le=100` or `le=1000` are the common caps).
4. If you add a new source, also add a TTL entry in `app/cache.py` `TTL` dict for future use.
5. Add a per-source doc in `docs/` if the API has non-obvious quirks.

### Environment

`.env` is loaded from the project root by `app/config.py`. Keys are listed there; `FEC_API_KEY`, `CONGRESS_API_KEY`, `EIA_API_KEY`, and `SMITHSONIAN_API_KEY` fall back to `"DEMO_KEY"` (works with low rate limits), the rest default to empty strings. A blank or whitespace-only value counts as unset. Keep `.env` comments on their own lines: python-dotenv reads `KEY=   # note` as the value `# note`, and `docker run --env-file` keeps every inline comment in the value. `SEC_USER_AGENT` is required by the SEC and must be a real `"Name email"` string — EDGAR returns 403 without it. `UCDP_ACCESS_TOKEN` is optional but the UCDP upstream now 401s without it (free registration at ucdp.uu.se). The global-tier sources (World Bank, IMF, Eurostat, ECB, Comtrade, USGS, NWS, EONET, Wikipedia) and the media/video sources (NASA Image and Video Library, Internet Archive, Wikimedia Commons) are keyless; NWS, Wikipedia, and Commons calls send the polite `DataGod/1.0 (github.com/mishafyi/datagod)` User-Agent from the client modules.

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
