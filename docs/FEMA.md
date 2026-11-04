---
name: fema
description: "Disasters and emergency management (OpenFEMA) — federal disaster declarations (hurricanes, floods, wildfires / fires, storms, earthquakes, emergencies), FEMA grants and assistance, and NFIP flood-insurance claims. Use for disaster events or federal disaster aid."
keywords: "disasters, disaster declarations, hurricanes, floods, wildfires, fires, storms, earthquakes, emergencies, disaster relief, grants, assistance, flood insurance, NFIP, flood claims"
routes: "/fema/disasters, /fema/flood-claims, /fema/grants"
---

# FEMA

Disasters and emergency management (OpenFEMA) — federal disaster declarations (hurricanes, floods, wildfires / fires, storms, earthquakes, emergencies), FEMA grants and assistance, and NFIP flood-insurance claims. Use for disaster events or federal disaster aid.

## Endpoints

### `GET /fema/disasters`

Federal disaster declarations (hurricanes, floods, wildfires, severe storms) by date and state.

**Params:** `limit` (query, integer, default 10, max 1000) · `state` (query, string) · `declared_since` (query, string)

### `GET /fema/flood-claims`

NFIP (National Flood Insurance Program) flood insurance claims data.

**Params:** `limit` (query, integer, default 10, max 1000)

### `GET /fema/grants`

FEMA grant and assistance awards.

**Params:** `limit` (query, integer, default 10, max 1000)

## Quirks & notes

- No key (OpenFEMA).
- Datasets: disasters → `DisasterDeclarationsSummaries`, grants → `HazardMitigationGrantProgramDisasterSummaries` **v3**, flood-claims → `NfipClaims` **v3** (`FimaNfipClaims` v2 is gone — 404; HMGP v2 was frozen 2026-08-31 and deprecated 2026-10-15).
- `state`/`declared_since` are sent as an OData `$filter` with quotes escaped.

> Endpoint params are generated from the live OpenAPI schema (`/openapi.json`); the Quirks section is curated. Regenerate with `python -m scripts.gen_source_docs`.
