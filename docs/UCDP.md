---
name: ucdp
description: "UCDP — Uppsala Conflict Data Program georeferenced event dataset (GED): individual organized-violence events worldwide with location, date, actors, and fatality estimates. Use for armed-conflict and political-violence data."
keywords: "UCDP, armed conflict, war, political violence, conflict events, fatalities, Uppsala, GED, battle deaths"
routes: "/ucdp/gedevents"
---

# UCDP

Uppsala Conflict Data Program — georeferenced event data (GED).

## Endpoints

### `GET /ucdp/gedevents`

Organized-violence events with locations, actors, and fatality estimates.

**Params:** `country` (Gleditsch-Ward numeric id(s), comma-separated — 369=Ukraine, 365=Russia; NOT names or ISO codes) · `start_date` / `end_date` (`YYYY-MM-DD`) · `pagesize` (default 10, max 1000) · `page` (0-based) · `version` (dataset release, default `24.1`)

## Quirks & notes

- **No longer keyless (verified 2026-07-25):** every request without an `x-ucdp-access-token` header now gets 401 "API token required" — across all resources and versions. Register for a free token at ucdp.uu.se and set `UCDP_ACCESS_TOKEN`; the client sends the header only when the env var is set.
- Response: `{TotalCount, TotalPages, PreviousPageUrl, NextPageUrl, Result}` — rows in `Result`.
- `version` pins a dataset release (`24.1` = GED through 2023); candidate/monthly releases use versions like `25.0.X`.
- Country filter uses Gleditsch-Ward numeric ids; the upstream param names are capitalized (`Country`, `StartDate`, `EndDate`) — the client maps them.
