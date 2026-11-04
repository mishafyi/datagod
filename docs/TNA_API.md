---
name: tna
description: "UK National Archives (Discovery catalog, 32M+ record descriptions) — British government records including declassified intelligence and military files: MI5 Security Service (KV), Special Operations Executive (HS), Cabinet Office / JIC (CAB), Ministry of Defence (DEFE), Prime Minister's Office (PREM), Foreign Office (FO). Use for UK historical and intelligence records."
keywords: "UK National Archives, Discovery, Kew, British government records, MI5, KV, SOE, HS, Cabinet Office, JIC, CAB, DEFE, PREM, Foreign Office, declassified, UK intelligence"
routes: "/tna/record/{record_id}, /tna/search"
---

# TNA — UK National Archives Discovery

The UK National Archives' Discovery catalog: 32M+ record descriptions held at
Kew and elsewhere, including the declassified intelligence and military series
— KV (Security Service / MI5), HS (Special Operations Executive), DEFE
(Ministry of Defence), CAB (Cabinet Office / JIC), WO / ADM / AIR (the services),
PREM (Prime Minister's Office), FO (Foreign Office). Descriptions are open; many
records link to digitised downloads. Client: `app/clients/tna.py`.

## Endpoints

### `GET /tna/search`

Full-text search of record descriptions — the upstream JSON unchanged: `records[]`
(`id`, `reference`, `title`, `description`, covering dates, `heldBy`, …), `count`,
and facets (`timePeriods`, `departments`, …).
**Params:** `q` (required), `page` (1-based), `per_page` (default 20, max 100),
`series` — a lettercode such as `KV`, `HS`, `DEFE`, `CAB`, `PREM`.

### `GET /tna/record/{record_id}`

Full details for one record by its Discovery `id` (from the search results):
`citableReference`, `scopeContent`, dates, closure status, held-by, and more.

## Quirks & notes

- Official, keyless API: `https://discovery.nationalarchives.gov.uk/API`, plain
  GET with `Accept: application/json`.
- `series` is sent as the upstream's **`sps.departments`** filter.
  `sps.recordSeries` looks right but matches nothing (verified 2026-08-06).
- Paging: `sps.page` (1-based) + `sps.resultsPageSize`.
