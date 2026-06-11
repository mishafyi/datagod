---
name: clinical-trials
description: "Clinical and medical trials (ClinicalTrials.gov, 500K+ studies) — searchable by condition or disease, intervention / drug or treatment, and status (recruiting, completed), by NCT id. Use for clinical or drug trials on a disease or treatment."
keywords: "clinical trials, medical trials, studies, drug trials, condition, disease, intervention, treatment, recruiting, NCT, research studies, sponsors"
routes: "/clinical-trials, /clinical-trials/{nct_id}"
---

# Clinical Trials

Clinical and medical trials (ClinicalTrials.gov, 500K+ studies) — searchable by condition or disease, intervention / drug or treatment, and status (recruiting, completed), by NCT id. Use for clinical or drug trials on a disease or treatment.

## Endpoints

### `GET /clinical-trials`

Search ClinicalTrials.gov by condition, intervention, and status (recruiting, completed). Medical and drug trials.

**Params:** `condition` (query, string) · `intervention` (query, string) · `status` (query, string) · `limit` (query, integer, default 10, max 100)

### `GET /clinical-trials/{nct_id}`

Full record for one clinical trial by its NCT ID.

**Params:** `nct_id` (path, string, required)

## Quirks & notes

- No key. Base `clinicaltrials.gov/api/v2`: `studies` and `studies/{nct}`.
- Filters: `query.cond` (condition), `query.intr` (intervention), `filter.overallStatus`.

> Endpoint params are generated from the live OpenAPI schema (`/openapi.json`); the Quirks section is curated. Regenerate with `python -m scripts.gen_source_docs`.
