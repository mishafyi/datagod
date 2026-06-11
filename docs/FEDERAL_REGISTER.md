---
name: federal-register
description: "US federal regulations (Federal Register) — proposed and final rules and rulemaking, agency notices, executive orders, and presidential documents, by type and agency. Use for regulations, rules, or executive orders."
keywords: "regulations, rules, rulemaking, proposed rules, final rules, notices, executive orders, presidential documents, agencies, federal regulations"
routes: "/federal-register, /federal-register/{doc_number}"
---

# Federal Register

US federal regulations (Federal Register) — proposed and final rules and rulemaking, agency notices, executive orders, and presidential documents, by type and agency. Use for regulations, rules, or executive orders.

## Endpoints

### `GET /federal-register`

Search the Federal Register: proposed and final rules, notices, executive orders, and presidential documents; filter by type and agency.

**Params:** `term` (query, string) · `doc_type` (query, string) · `agency` (query, string) · `limit` (query, integer, default 10, max 100)

### `GET /federal-register/{doc_number}`

One Federal Register document by its document number.

**Params:** `doc_number` (path, string, required)

## Quirks & notes

- No key. Base `federalregister.gov/api/v1`: `documents.json`, `documents/{n}.json`.
- Filters: `conditions[type][]` (RULE | PRORULE | NOTICE | PRESDOCU), `conditions[agencies][]`, `conditions[term]`, `order=newest`.

> Endpoint params are generated from the live OpenAPI schema (`/openapi.json`); the Quirks section is curated. Regenerate with `python -m scripts.gen_source_docs`.
