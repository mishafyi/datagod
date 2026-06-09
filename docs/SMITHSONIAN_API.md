# Smithsonian Open Access (EDAN) API Reference

**Base URL**: `https://api.si.edu/openaccess/api/v1.0`
**Auth**: `api_key` query param (api.data.gov key). `DEMO_KEY` works at low rate limits; the project key lives in `.env` as `SMITHSONIAN_API_KEY`. Register at <https://api.data.gov/signup/>.
**Coverage**: ~11M+ metadata records across Smithsonian units (museums, libraries, archives); millions are CC0 with media.
**Rate limits**: api.data.gov default (1,000 req/hour for a registered key; far less for `DEMO_KEY`).

## Endpoints used by datagod

| datagod route | Upstream | Notes |
|---------------|----------|-------|
| `GET /smithsonian/search` | `/search?q=&start=&rows=&sort=&type=&api_key=` | Full-text search. `rows` capped at 100; `start` paginates. |
| `GET /smithsonian/object/{object_id}` | `/content/{id}?api_key=` | Full record for one EDAN id (route uses `{object_id:path}` to allow ids with slashes). |
| `GET /smithsonian/category/{category}/search` | `/category/{category}/search?q=&start=&rows=&api_key=` | `category`: `art_design` \| `history_culture` \| `science_technology`. |
| `GET /smithsonian/terms/{category}` | `/terms/{category}?api_key=` | Controlled-vocabulary terms. `category`: `culture`, `topic`, `place`, `object_type`, `data_source`, `date`, `name`, `set_name`, … |
| `GET /smithsonian/stats` | `/stats?api_key=` | Dataset statistics. |

## Search parameters

- **`q`** — free-text query (Lucene-style; supports field queries like `unit_code:NMNHANTHRO` and `online_media_type:Images`).
- **`start`** — 0-based offset for pagination.
- **`rows`** — page size, max 100.
- **`sort`** — `relevancy` (default), `newest`, `updated`, `random`.
- **`type`** — exposed as `obj_type` on the datagod route; EDAN record type (e.g. `edanmdm`, `ld`).

## Response shape

All endpoints return:

```json
{
  "status": 200,
  "responseCode": 1,
  "response": {
    "rows": [ { "id": "...", "title": "...", "unitCode": "...", "type": "...",
                "url": "...", "content": { ... }, "hash": "...", "docSignature": "...",
                "timestamp": "...", "lastTimeUpdated": "...", "version": "..." } ],
    "facets": { ... },
    "rowCount": 634,
    "message": null
  }
}
```

Results live in `response.rows[]`; `response.rowCount` is the total match count. The full descriptive metadata for a row is under `row.content` (EDAN `descriptiveNonRepeating`, `freetext`, `indexedStructured`). datagod returns this envelope unchanged; `ResponseEnvelopeMiddleware` wraps it in the standard `{meta, data, error}`.

## Curl examples

```bash
KEY=... # SMITHSONIAN_API_KEY
curl -s "https://api.si.edu/openaccess/api/v1.0/search?q=sunflower&rows=2&api_key=$KEY"
curl -s "https://api.si.edu/openaccess/api/v1.0/content/ld1-1646149545906-1646150375926-0?api_key=$KEY"
curl -s "https://api.si.edu/openaccess/api/v1.0/category/art_design/search?q=painting&rows=1&api_key=$KEY"
curl -s "https://api.si.edu/openaccess/api/v1.0/terms/culture?api_key=$KEY"
curl -s "https://api.si.edu/openaccess/api/v1.0/stats?api_key=$KEY"
```

## Notes

- `q=sunflower` returns `rowCount: 634`; `category/art_design/search?q=painting` returns `rowCount: 10576` (verified live).
- Row `id` values look like `ld1-1646149545906-1646150375926-0` or `edanmdm-<unit>_<accession>`.
- Bulk metadata is also mirrored on GitHub at `Smithsonian/OpenAccess` (not used here; the live API is sufficient).
