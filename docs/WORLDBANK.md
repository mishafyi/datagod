---
name: worldbank
description: "World Bank Open Data — 16K+ development indicators for every country and aggregate: GDP, population, poverty, trade, education, health, energy. Use for cross-country macro/development comparisons and long historical series."
keywords: "World Bank, GDP by country, development indicators, population, poverty, global economy, country comparison, NY.GDP.MKTP.CD, SP.POP.TOTL"
routes: "/worldbank/{indicator}, /worldbank/countries"
---

# World Bank

World Bank Open Data — development indicators for every country (16K+ series). Keyless.

## Endpoints

### `GET /worldbank/{indicator}`

One indicator across countries, e.g. `NY.GDP.MKTP.CD` (GDP, current US$), `SP.POP.TOTL` (population).

**Params:** `countries` (ISO2 codes joined with `;`, e.g. `us;cn;fr`, or `all`, default `all`) · `date_range` (`YYYY:YYYY`) · `per_page` (default 200, max 1000)

### `GET /worldbank/countries`

All countries/aggregates with region, income level, and ISO codes.

**Params:** `per_page` (default 300, max 400)

## Quirks & notes

- Upstream base `api.worldbank.org/v2`; `format=json` is mandatory (default is XML).
- Response is a 2-element array: `[paging-metadata, rows]` — rows are in element `[1]`.
- The country dimension also accepts aggregates (`EUU`, `WLD`) and 3-letter ISO codes.
- Invalid indicator ids still return 200 with a `message` element in `[0]` — check for missing `[1]`.
