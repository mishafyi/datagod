---
name: bls
description: "US labor statistics and jobs data (Bureau of Labor Statistics) — unemployment rate, employment and nonfarm payrolls, wages and average hourly earnings, job openings, CPI inflation and consumer prices, PPI producer prices, productivity, by series. Use for the labor market, jobs, or price indexes."
keywords: "jobs, employment, unemployment rate, labor market, nonfarm payrolls, payroll, wages, earnings, hourly earnings, salary, CPI, inflation, consumer prices, PPI, producer prices, productivity, job openings, labor statistics"
routes: "/bls/batch, /bls/{series_id}"
---

# BLS

US labor statistics and jobs data (Bureau of Labor Statistics) — unemployment rate, employment and nonfarm payrolls, wages and average hourly earnings, job openings, CPI inflation and consumer prices, PPI producer prices, productivity, by series. Use for the labor market, jobs, or price indexes.

## Endpoints

### `POST /bls/batch`

BLS multi-series batch (POST, registrationkey added when set)

### `GET /bls/{series_id}`

US labor statistics series by ID. Use for: unemployment rate, nonfarm payroll employment, CPI inflation, PPI, average hourly earnings. Shortcut IDs: unemployment, cpi, nonfarm_employment, ppi, hourly_earnings.

**Params:** `series_id` (path, string, required) · `start_year` (query, integer, required) · `end_year` (query, integer, required)

## Quirks & notes

- Uses the BLS public API **v1** (`api.bls.gov/publicAPI/v1/timeseries/data`) — not v2. `BLS_API_KEY` is optional (raises limits).
- The client accepts shortcut series IDs: `unemployment`, `cpi`, `nonfarm_employment`, `ppi`, `hourly_earnings`.
- Data is under `Results.series[].data`.

> Endpoint params are generated from the live OpenAPI schema (`/openapi.json`); the Quirks section is curated. Regenerate with `python -m scripts.gen_source_docs`.
