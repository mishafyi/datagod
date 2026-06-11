---
name: census
description: "US demographics from the Census Bureau / American Community Survey (ACS) — population, median household income, race and ethnicity, age, sex, education, poverty, housing and rent, commute, employment — by state, county, or census tract. Use for any US demographic or socioeconomic statistic."
keywords: "demographics, population, household income, median income, ACS, American Community Survey, race, ethnicity, age, sex, gender, education, poverty, housing, rent, commute, employment, state, county, census tract"
routes: "/census/acs, /census/income, /census/population"
---

# Census

US demographics from the Census Bureau / American Community Survey (ACS) — population, median household income, race and ethnicity, age, sex, education, poverty, housing and rent, commute, employment — by state, county, or census tract. Use for any US demographic or socioeconomic statistic.

## Endpoints

### `GET /census/acs`

Raw American Community Survey query — any ACS variables and geography (state / county / tract). Use for: demographics, race, age, sex, education, income, poverty, housing, commute — any ACS table by variable code.

**Params:** `variables` (query, string, default NAME,B01001_001E) · `year` (query, integer, default 2022) · `geo_for` (query, string, default state:*) · `geo_in` (query, string)

### `GET /census/income`

Median household income by US state.

**Params:** `year` (query, integer, default 2022)

### `GET /census/population`

Population by US state.

**Params:** `year` (query, integer, default 2022)

## Quirks & notes

- **Requires a valid `CENSUS_API_KEY`** (free signup: https://api.census.gov/data/key_signup.html). A missing or invalid key 302-redirects to an HTML `invalid_key.html` page → JSON parse error → 502.
- The client sends `cfg.CENSUS_API_KEY` as `key=`. Uses ACS 1-year (`acs/acs1`).
- Response is a 2-D array: a header row followed by data rows.

> Endpoint params are generated from the live OpenAPI schema (`/openapi.json`); the Quirks section is curated. Regenerate with `python -m scripts.gen_source_docs`.
