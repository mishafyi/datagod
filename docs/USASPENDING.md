---
name: usaspending
description: "US federal spending ($6T+/yr) — government contracts, grants, and awards; recipients, contractors, and vendors; award amounts; agency and defense spending totals; subawards. Use for who received federal money, federal contracts, or grant awards."
keywords: "federal spending, government contracts, grants, awards, contractors, recipients, vendors, procurement, award amount, agency spending, defense spending, federal money, subawards"
routes: "/usaspending/agencies, /usaspending/by-agency, /usaspending/search"
---

# USAspending

US federal spending ($6T+/yr) — government contracts, grants, and awards; recipients, contractors, and vendors; award amounts; agency and defense spending totals; subawards. Use for who received federal money, federal contracts, or grant awards.

## Endpoints

### `GET /usaspending/agencies`

List of federal agencies (names and IDs) for filtering spending queries.

### `GET /usaspending/by-agency`

Federal spending totals grouped by agency for a fiscal year / quarter.

**Params:** `fy` (query, string, required) · `quarter` (query, string, default 1)

### `GET /usaspending/search`

Search federal awards (contracts and grants) by keyword. Use for: who received federal money, contractors/recipients, award amounts, defense or agency spending.

**Params:** `q` (query, string, required) · `start_date` (query, string) · `end_date` (query, string) · `limit` (query, integer, default 10, max 100) · `page` (query, integer, default 1) · `sort` (query, string, default Award Amount) · `order` (query, string, default desc) · `award_type_codes` (query, string)

## Quirks & notes

- No key. Base `api.usaspending.gov/api/v2`.
- `agencies` → `references/toptier_agencies/`; `search` → POST `search/spending_by_award/`; `by-agency` → POST `spending/`.

> Endpoint params are generated from the live OpenAPI schema (`/openapi.json`); the Quirks section is curated. Regenerate with `python -m scripts.gen_source_docs`.
