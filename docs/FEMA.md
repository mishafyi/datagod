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

**Params:** `limit` (query, integer, default 10, max 1000)

### `GET /fema/flood-claims`

NFIP (National Flood Insurance Program) flood insurance claims data.

**Params:** `limit` (query, integer, default 10, max 1000)

### `GET /fema/grants`

FEMA grant and assistance awards.

**Params:** `limit` (query, integer, default 10, max 1000)

## Quirks & notes

- No key (OpenFEMA).
- Datasets: disasters → `DisasterDeclarationsSummaries`, grants → `HazardMitigationGrantProgramDisasterSummaries`, flood-claims → `FimaNfipClaims`.

> Endpoint params are generated from the live OpenAPI schema (`/openapi.json`); the Quirks section is curated. Regenerate with `python -m scripts.gen_source_docs`.
