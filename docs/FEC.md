---
name: fec
description: "Federal campaign finance and elections (FEC) — candidates (presidential, Senate, House), itemized contributions and donors, PAC and super PAC money, and candidate fundraising totals (receipts, disbursements). Use for election money: who is running, who donated, how much was raised or spent."
keywords: "campaign finance, elections, candidates, presidential candidates, donors, donations, contributions, PAC, super PAC, fundraising, money raised, receipts, disbursements, spending, election money"
routes: "/fec/candidates, /fec/contributions, /fec/totals"
---

# FEC

Federal campaign finance and elections (FEC) — candidates (presidential, Senate, House), itemized contributions and donors, PAC and super PAC money, and candidate fundraising totals (receipts, disbursements). Use for election money: who is running, who donated, how much was raised or spent.

## Endpoints

### `GET /fec/candidates`

Search federal candidates (President, Senate, House) by office and state. Campaign finance.

**Params:** `office` (query, string) · `state` (query, string) · `limit` (query, integer, default 10, max 100) · `page` (query, integer, default 1)

### `GET /fec/contributions`

Campaign contributions — itemized donations by or for a candidate or donor name.

**Params:** `name` (query, string) · `candidate_id` (query, string) · `limit` (query, integer, default 10, max 100) · `page` (query, integer, default 1)

### `GET /fec/totals`

Candidate financial totals (money raised / receipts), ranked, by office and election year.

**Params:** `year` (query, integer, required) · `office` (query, string, default P) · `limit` (query, integer, default 10, max 100) · `page` (query, integer, default 1)

## Quirks & notes

- `FEC_API_KEY` with a `DEMO_KEY` fallback (low limits).
- Base `api.open.fec.gov/v1`: `candidates/`, `schedules/schedule_a/` (contributions), `candidates/totals/`.
- Results under `results`; paginated.

> Endpoint params are generated from the live OpenAPI schema (`/openapi.json`); the Quirks section is curated. Regenerate with `python -m scripts.gen_source_docs`.
