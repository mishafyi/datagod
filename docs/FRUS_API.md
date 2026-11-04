---
name: frus
description: "Foreign Relations of the United States (history.state.gov) — the official State Department documentary record of US foreign policy: 500+ volumes of declassified cables, memos, meeting minutes and covert-action documents (Iran 1953, Guatemala, Congo, Chile, the intelligence community). Full-text search plus single documents with archival source notes."
keywords: "FRUS, Foreign Relations of the United States, State Department, diplomacy, diplomatic cables, foreign policy, declassified, covert action, history.state.gov, Office of the Historian"
routes: "/frus/document/{volume}/{doc}, /frus/search"
---

# FRUS — Foreign Relations of the United States

The official documentary record of US foreign policy, published by the State
Department's Office of the Historian (`history.state.gov`): 500+ volumes of
declassified cables, memoranda and meeting minutes, including the retrospective
covert-action volumes (Iran 1951–54, Guatemala 1952–54, Congo 1960–68,
Chile 1969–73, the Intelligence Community volumes). Keyless.
Client: `app/clients/frus.py`.

## Endpoints

### `GET /frus/search`

Full-text search across every volume:
`{start, per_page: 10, total, results: [{title, volume, doc, url, summary}]}`.
**Params:** `q` (required), `start` — the 1-based result offset (10 per page;
next page = `start + 10`). Ranked by relevance.

### `GET /frus/document/{volume}/{doc}`

One document by volume id and number (from the search results), e.g.
`/frus/document/frus1969-76v21/7`:
`{volume, doc, title, source_note, body (≤40,000 chars), url}`. A page without
document content answers 404.

## Quirks & notes

- **No JSON API.** Search results and documents are server-rendered HTML,
  parsed with selectolax — brittle if the site's theme changes:
  results are `div.hsg-search-result` (title link `h3.hsg-search-result-heading a`,
  summary `p.hsg-search-result-summary`); a document lives in `div.content`
  (heading `h3`, archival citation `.tei-note1` / `.tei-sourcenote`).
- `total` is parsed from the "N results" text on the page.
- Volume ids look like `frus1969-76v21`, `frus1964-68v26`, `frus1952-54Iran`;
  document URLs are `/historicaldocuments/{volume}/d{n}`.
