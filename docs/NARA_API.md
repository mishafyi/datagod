---
name: nara
description: "US National Archives catalog — historical federal and government records, primary sources, and declassified documents across all record groups and the 14 presidential libraries. Use for archival US government documents, historical records, or presidential materials."
keywords: "National Archives, archives, historical records, government records, presidential libraries, primary sources, declassified, catalog, historical documents"
routes: "/nara/record/{na_id}, /nara/search"
---

# NARA — National Archives Catalog API Reference

**Base URL**: `https://catalog.archives.gov/proxy`
**Auth**: **None required.** The catalog's own web app calls a `/proxy` gateway that injects NARA's API key server-side. (NARA also documents a keyed API at `catalog.archives.gov/api/v2` requiring a NARA-issued `x-api-key`; datagod uses the keyless `/proxy` path the frontend uses instead.)
**Status**: Unofficial — this is the same endpoint `catalog.archives.gov` calls. Browser-like **fetch headers are mandatory**; without them the edge serves the SPA's HTML (HTTP 200, `text/html`) instead of JSON.
**Coverage**: the entire National Archives Catalog — every record group, including all **14 presidential libraries** (Hoover → Obama). Scope to one library with query terms.

## Required headers (set in `nara.py` HEADERS)

```
User-Agent: Mozilla/5.0 …            Referer: https://catalog.archives.gov/
Accept: application/json, …          Origin:  https://catalog.archives.gov
X-Requested-With: XMLHttpRequest     Sec-Fetch-Mode: cors / -Site: same-origin / -Dest: empty
```

Omitting these → the proxy returns `text/html` (the React app shell), not JSON. This was discovered by reading the catalog SPA bundle (`static/js/main.*.chunk.js`: `SEARCH_HOST="https://catalog.archives.gov"`, `J = SEARCH_HOST + "/proxy"`).

## Endpoints used by datagod

| datagod route | Upstream | Notes |
|---------------|----------|-------|
| `GET /nara/search` | `/proxy/records/search?q=&page=` | Full-text search, **fixed 20 results/page**. `page` is 1-based. |
| `GET /nara/record/{na_id}` | `/proxy/records/search?naId={id}` | One catalog record by National Archives Identifier (NAID). |

**Search params:** `q` accepts boolean operators (`AND`/`OR`/`NOT`), wildcards (`*`) and exact `"phrases"`, plus field queries (e.g. `record.ancestors.naId:NNNN`). The public proxy paginates with **`page`** only, at a **fixed 20 results/page** — sending `limit` (or `offset`) makes the proxy serve the SPA HTML instead of JSON, so the client sends neither. Other filters the frontend uses (`availableOnline=true`, `typeOfMaterials=…`, `levelOfDescription=…`) can be folded into `q` field-syntax or added to the client if they prove proxy-safe.

## Response shape

```json
{
  "body": {
    "hits": {
      "total": {"value": 133742, "relation": "eq"},
      "hits": [
        {"_index": "nac-records2", "_id": "196476293", "_score": 108.3,
         "_source": {"record": { "naId": "…", "title": "…", "levelOfDescription": "…",
                                  "recordType": "…", "ancestors": [...], "…": "…" }}}
      ]
    }
  }
}
```

Results are `body.hits.hits[]._source.record`; total match count is `body.hits.total.value`. datagod returns this envelope unchanged; `ResponseEnvelopeMiddleware` wraps it in `{meta, data, error}`.

## Scoping to a presidential library

All 14 libraries live in the same catalog. Reach one by querying its record group / organization in `q` (e.g. search the library name, or use `record.ancestors.naId:<library NAID>` once you have it). There is no separate per-library endpoint — one catalog, filtered.

## Curl examples (note the headers)

```bash
H=(-H 'User-Agent: Mozilla/5.0' -H 'Accept: application/json' \
   -H 'Referer: https://catalog.archives.gov/' -H 'Origin: https://catalog.archives.gov' \
   -H 'X-Requested-With: XMLHttpRequest' -H 'Sec-Fetch-Mode: cors' \
   -H 'Sec-Fetch-Site: same-origin' -H 'Sec-Fetch-Dest: empty')
curl -s "${H[@]}" 'https://catalog.archives.gov/proxy/records/search?q=reagan&page=1'
curl -s "${H[@]}" 'https://catalog.archives.gov/proxy/records/search?naId=1419123'
```

## Notes / gotchas

- **`limit` and `offset` both break it** — either one makes the public proxy return the SPA HTML (HTTP 200, `text/html`). Paginate with `page` only; page size is a fixed 20.
- The official keyed API (`/api/v2/records/search`, `x-api-key`) needs a key obtained from NARA's Catalog team; api.data.gov/DEMO_KEY keys do **not** work there (they return the SPA HTML). The `/proxy` path avoids the key entirely.
- Much of NARA's textual holdings are described but **not digitized** — `availableOnline=true` filters to records with viewable digital objects.
- Bulk catalog exports are also on data.gov; the live `/proxy` API is sufficient here.
