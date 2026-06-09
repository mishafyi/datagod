# Wilson Center Digital Archive — Local Mirror

**Source**: a downloaded mirror of <https://digitalarchive.wilsoncenter.org/search>, captured ~2025-03-16, stored at `data/digitalarchive wilsoncenter/`.
**Why local**: the live site became unreachable (its DNS returns NODATA — no A record from any resolver, including Cloudflare's own 1.1.1.1). The `wilson.py` client was therefore rewritten to serve the mirror instead of the live `/srv/*.json` API. There is **no network call** in this client.

## The mirror (zstd-compressed tarballs)

| File | Size | Contents |
|------|------|----------|
| `documents.tar.zst` | 36 MB | 16,756 Drupal HTML document pages at `documents/document/{slug}` |
| `search-results.tar.zst` | 12 MB | 1,676 HTML pages of the site's *default* (unfiltered) search, paginated |
| `downloads.tar.zst` | 11 GB | The actual PDF/scan binaries at `downloads/document/{numeric-id}/download` |
| `document-urls.txt.zst` | — | List of all `/document/{slug}` paths |
| `download-urls.txt.zst` | — | List of all `/document/{numeric-id}/download` paths |

Document pages are HTML (no clean embedded JSON — the only `<script type="application/json">` is Drupal settings, which usefully carries `currentPath: node/{numeric-id}`, the id used for downloads). Metadata lives in HTML markup: `<h1>` title, `.information-block` (label `.sub-title` + value: Source, Original Archive, Rights, Date, Language, Record ID, Donors…), `.pill-subject` (subjects), `.pill` (people/orgs/places).

## Build step (run once)

```bash
.venv/bin/python scripts/build_wilson_index.py
```

This streams `documents.tar.zst`, parses every page with `selectolax`, and writes **`data/wilson.db`** (~228 MB): a `documents` table (slug, node_id, record_id, title, info JSON, subjects JSON, names JSON, download flag) plus a `documents_fts` FTS5 virtual table over title + full body text. ~20 s, 16,756 rows. Re-run if the mirror is refreshed.

## Routes

| Route | Backed by | Notes |
|-------|-----------|-------|
| `GET /wilson/documents?q=&page=&items_per_page=` | `documents_fts` FTS5 | Full-text search across title + body. Empty `q` lists all by title. `items_per_page` ≤ 100. |
| `GET /wilson/document/{slug}` | `documents` | Full local record by slug (the slug is the last path segment of the original `/document/{slug}` URL). |

Dropped vs. the old live client: `/wilson/collections`, `/wilson/collection/{id}`, and the `/wilson/{route:path}` passthrough — the mirror has no collections dataset and no live API.

## Response shapes

**Search** keeps a `{list, pagination}` shape for continuity (it is *not* the upstream's envelope — it's built locally):

```json
{
  "list": [ {"slug": "...", "title": "...", "record_id": "134845", "node_id": "99018",
             "subjects": ["..."], "download_available": true} ],
  "pagination": {"page": 1, "itemsPerPage": 10, "totalItems": 1557, "totalPages": 156}
}
```

**Document** returns the full extracted record:

```json
{
  "slug": "about-irans-approach-against-tudeh-party",
  "node_id": "99018", "record_id": "134845",
  "title": "About Iran’s approach against the Tudeh Party",
  "info": {"Source": "...", "Original Archive": "...", "Rights": "...",
           "Original Uploaded Date": "2017-02-17", "Language": "German", "Record ID": "134845"},
  "subjects": ["Iran--Politics and government", "..."],
  "names": ["...Stasi...", "..."],
  "download": {"available": true, "id": "99018",
               "mirror_path": "data/digitalarchive wilsoncenter/downloads.tar.zst::downloads/document/99018/download"}
}
```

Errors use the standard contract dict (`{"error": true, "source": "wilson", "upstream_status": 404|503, ...}`): `404` for an unknown slug, `503` if `data/wilson.db` hasn't been built yet.

## Downloads (metadata-only)

The 11 GB of binaries are **not** served. Each record's `download` block exposes availability, the numeric id, and the in-tarball `mirror_path` so a caller can extract it themselves (`zstd -dc downloads.tar.zst | tar -xO downloads/document/99018/download`). Serving binaries would require extracting the tarball or building a seekable index — out of scope by design.

## Client mechanics

`wilson.py` opens `data/wilson.db` read-only per call; since `sqlite3` is synchronous, calls run via `asyncio.to_thread` (the yfinance pattern). FTS queries are sanitized to quoted tokens (implicit AND) to avoid FTS5 syntax errors.
