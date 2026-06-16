---
name: fred
description: "US economy and macroeconomic time series (800K+) — GDP, inflation and consumer prices (CPI, PCE), unemployment rate, interest rates (Fed funds, Treasury yields, 10-year), money supply (M1/M2), exchange rates, housing, industrial production, S&P 500, recession indicators. The default for any national economic indicator over time."
keywords: "economy, economic indicators, GDP, inflation, CPI, consumer prices, PCE, deflator, unemployment rate, interest rates, Fed funds rate, Treasury yields, 10-year yield, money supply, M1, M2, exchange rates, housing, industrial production, S&P 500, recession, macroeconomic, time series"
routes: "/fred, /fred/series/{series_id}, /fred/{series_id}"
---

# FRED

US economy and macroeconomic time series (800K+) — GDP, inflation and consumer prices (CPI, PCE), unemployment rate, interest rates (Fed funds, Treasury yields, 10-year), money supply (M1/M2), exchange rates, housing, industrial production, S&P 500, recession indicators. The default for any national economic indicator over time.

## Endpoints

### `GET /fred`

Keyword search across FRED's 800K-series catalog; returns series IDs to fetch above. Use when you don't know the exact series ID.

**Params:** `q` (query, string) · `limit` (query, integer, default 10, max 100)

### `GET /fred/series/{series_id}`

Fetch FRED series metadata

**Params:** `series_id` (path, string, required)

### `GET /fred/{series_id}`

One US macroeconomic time series by FRED series ID. Use for: GDP, inflation, consumer prices/CPI (CPIAUCSL), unemployment rate (UNRATE), Fed funds / interest rates (FEDFUNDS), Treasury yields (DGS10), money supply (M2), S&P 500 (SP500), industrial production, recession indicators — any US macro indicator.

**Params:** `series_id` (path, string, required) · `limit` (query, integer, default 10, max 1000) · `offset` (query, integer, default 0) · `sort_order` (query, string, default asc) · `observation_start` (query, string) · `observation_end` (query, string)

## Quirks & notes

- Requires a real `FRED_API_KEY` (no DEMO_KEY fallback).
- Response is the FRED observations envelope; `value` fields are strings.
- Handy series IDs: `GDP`, `UNRATE`, `CPIAUCSL`, `FEDFUNDS`, `DGS10`, `M2SL`, `SP500`.

> Endpoint params are generated from the live OpenAPI schema (`/openapi.json`); the Quirks section is curated. Regenerate with `python -m scripts.gen_source_docs`.
