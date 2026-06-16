---
name: eia
description: "US energy data (Energy Information Administration) — gasoline and fuel prices, crude oil and petroleum, natural gas, electricity (generation, sales, prices), coal, renewables (solar, wind), CO2 emissions, and energy consumption. Use for energy prices or production."
keywords: "energy, gasoline prices, gas prices, fuel prices, oil, crude oil, petroleum, natural gas, electricity, power, generation, coal, renewables, solar, wind, emissions, CO2, energy consumption"
routes: "/eia, /eia/electricity, /eia/gas-prices, /eia/{route}"
---

# EIA

US energy data (Energy Information Administration) — gasoline and fuel prices, crude oil and petroleum, natural gas, electricity (generation, sales, prices), coal, renewables (solar, wind), CO2 emissions, and energy consumption. Use for energy prices or production.

## Endpoints

### `GET /eia`

List the EIA energy datasets available to query.

### `GET /eia/electricity`

Electricity data: generation, retail sales, and prices.

**Params:** `limit` (query, integer, default 10, max 100) · `data_field` (query, string, default revenue) · `frequency` (query, string, default annual)

### `GET /eia/gas-prices`

Gasoline and fuel prices over time.

**Params:** `limit` (query, integer, default 10, max 100)

### `GET /eia/{route}`

Generic EIA dataset query by route path — any energy series (crude oil, natural gas, coal, renewables, CO2 emissions, consumption).

**Params:** `route` (path, string, required) · `frequency` (query, string, default annual) · `data` (query, string, default value) · `limit` (query, integer, default 10, max 5000) · `offset` (query, integer, default 0) · `sort_col` (query, string, default period) · `sort_dir` (query, string, default desc)

## Quirks & notes

- `EIA_API_KEY` with a `DEMO_KEY` fallback. Base `api.eia.gov/v2`.
- `/` lists datasets; gas → `petroleum/pri/gnd`; electricity → `electricity/retail-sales`; generic `{route}/data/` takes `frequency`, `data[0]`, `sort[0][...]`, `length`.

> Endpoint params are generated from the live OpenAPI schema (`/openapi.json`); the Quirks section is curated. Regenerate with `python -m scripts.gen_source_docs`.
