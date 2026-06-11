---
name: fda
description: "Drug and food safety (openFDA) — drug adverse-event and side-effect reports (FAERS), drug recalls, and food recalls (contamination, allergens), for medications and pharmaceuticals. Use for medication safety, adverse reactions, or recalled products."
keywords: "drugs, medications, adverse events, side effects, reactions, drug safety, drug recalls, food recalls, recalls, contamination, allergens, openFDA, FAERS, pharmaceuticals"
routes: "/fda/drug-events, /fda/drug-recalls, /fda/food-recalls"
---

# FDA

Drug and food safety (openFDA) — drug adverse-event and side-effect reports (FAERS), drug recalls, and food recalls (contamination, allergens), for medications and pharmaceuticals. Use for medication safety, adverse reactions, or recalled products.

## Endpoints

### `GET /fda/drug-events`

Drug adverse-event reports (side effects, reactions) from openFDA / FAERS.

**Params:** `search` (query, string) · `limit` (query, integer, default 10, max 100)

### `GET /fda/drug-recalls`

Drug recall enforcement reports — recalled medications, reasons, recall class.

**Params:** `search` (query, string) · `limit` (query, integer, default 10, max 100)

### `GET /fda/food-recalls`

Food recall enforcement reports — recalled foods, contamination, allergens, reasons.

**Params:** `search` (query, string) · `limit` (query, integer, default 10, max 100)

## Quirks & notes

- No key (openFDA). Base `api.fda.gov`.
- Datasets: `drug/event.json` (adverse events), `drug/enforcement.json` (drug recalls), `food/enforcement.json` (food recalls).
- `search=` uses Lucene-style queries; results under `results`.

> Endpoint params are generated from the live OpenAPI schema (`/openapi.json`); the Quirks section is curated. Regenerate with `python -m scripts.gen_source_docs`.
