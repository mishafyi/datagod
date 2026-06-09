# National Security Archive (NSArchive) — Virtual Reading Room (HTML scrape)

**Base URL**: `https://nsarchive.gwu.edu`
**Auth**: none.
**Status**: **Unofficial & brittle HTML scrape.** The National Security Archive is an NGO at George Washington University (**not** the government agency NARA — see `docs/NARA_API.md`). It has **no public API** — confirmed by inspection: `/jsonapi` → 404, REST `?_format=json` → 404, and loading the page fires only Google Analytics (no data XHR). It is a **Drupal 10** site whose Virtual Reading Room is a **Search API + Views** listing. This client scrapes the rendered HTML, so theme/markup changes will break it.
**Coverage**: the free published documents (~14,000) in the Virtual Reading Room. The full searchable corpus is the paywalled **DNSA** (ProQuest).

## Endpoints used by datagod

| datagod route | Upstream | Notes |
|---------------|----------|-------|
| `GET /nsarchive/search?q=&page=` | `GET /virtual-reading-room?search_api_fulltext={q}&page={page-1}` | Full-text search; empty `q` browses chronologically. **20 results/page**; `page` is 1-based here (the site pager is 0-based — the client subtracts 1). |
| `GET /nsarchive/document/{doc_id}` | `GET /document/{doc_id}` | One document. `doc_id` is the full **`{numeric-id}-{slug}`** path from search results — numeric-only ids 404. |

### Search syntax & behavior (verified — see `tests/test_nsarchive_search.py`)

⚠️ **The site's on-page "Search Tips" are wrong about the default.** They claim a search "looks for all of the words you enter" (AND). Empirically the `search_api_fulltext` **GET param defaults to OR** — `Nixon Mao` returns the *union* (508 hits, ≈ `Nixon OR Mao`), not the intersection (`Nixon AND Mao` = 17). The site's search *form* must apply AND via extra config the raw GET doesn't inherit. Because results are also always **sorted newest-first**, a plain multi-word query mostly surfaces recent FOIA releases (EPA, PACER, cyber/Ukraine, ODNI threat assessments).

**What does work through the GET param** (all verified by the test):

- **`AND` / `OR` / `NOT`** + **parentheses** — `Nixon AND Mao` (17) vs `Nixon Mao` (508); `(Nixon AND Mao) OR NOT Kissinger` parses. A query may not *start* with `NOT`.
- **`"exact phrase"`** quoting — `"Nickel Grass"` → 2 hits (vs 147 loose).
- **`*` wildcards** — `Afghan*` ≥ `Afghanistan`; `J* Brown` matches *Jerry/John Brown*.
- **`field_date[min]` / `field_date[max]`** date bounds — `field_date[max]=1990-12-31` returns only ≤1990 documents.
- **`sort_by` is ignored** — you cannot force relevance/oldest order; it is always newest-first.

**Recipe to find a specific (e.g. Cold-War) document:** a distinctive **exact phrase** and/or explicit **`AND`**, plus a **`field_date[max]`** bound. The client's `search(q, page)` passes `q` straight through, so phrase/Boolean/wildcard all work inside `q`; the `field_date` bounds require hitting `/virtual-reading-room` directly (the client wires full-text + page only — extend if needed). The form also exposes `search_api_fulltext_searched_fields` = All/Description/Document Text/Source/Title.

> The Reading Room is **not** the same corpus as NSArchive's curated **Electronic Briefing Books**. Many classic Cold-War EBB documents (e.g. the Robert Hultslander interview, IAFEATURE files) return **0 hits** here — they live on briefing-book pages outside this search index.

## Response shapes (built by the scraper, not upstream JSON)

**Search** — `{page, per_page, total, total_pages, results: [...]}`; each result:
```json
{"id": "33452", "path": "33452-document-2-united-states-district-court-northern-district-illinois",
 "title": "United States District Court Northern District of Illinois",
 "date": "2025-08-19T12:00:00Z", "date_text": "Aug 19, 2025", "source": "PACER",
 "url": "https://nsarchive.gwu.edu/document/33452-...", "thumbnail": "https://nsarchive.gwu.edu/sites/..."}
```
**Document** — `{id, path, title, date, source, description, body, pdf_url, url}` (the PDF is the `field--name-field-media-file` link; `body` is truncated to 5,000 chars).

Errors return the standard contract dict (`{"error": true, "source": "nsarchive", "upstream_status": …, "message": …}`).

## How it was reverse-engineered (parsing anchors)

Drupal field markup (verified via chrome-devtools + curl):
- **Listing item**: `article.media--type-document` → `.field--name-field-title a` (title + `/document/{id-slug}` href), `.field--name-field-date time[datetime]`, `.field--name-field-source .field__item`, `.field--name-thumbnail img`.
- **Total**: the text `"{N} document(s) found"` on the page.
- **Document page**: `h1` (title), `.field--name-field-date time`, `.field--name-field-source`, `.field--name-field-description`, `.field--name-body`, `.field--name-field-media-file a` (PDF).
- Search filtering is the GET param `search_api_fulltext`; pagination is `page` (0-based). The form's AJAX path (`POST /views/ajax`) returns HTML-in-JSON and needs the full Drupal `ajax_page_state` payload — **not used**; the plain GET listing is simpler and works.

## Gotchas / fragility

- **HTML scrape** — any theme update changes the selectors and breaks parsing. Re-verify against a live page if results go empty.
- Numeric-only `/document/{id}` → 404; you must use the full `{id}-{slug}` path (search results provide it).
- `body` is the on-page transcription/summary when present; the authoritative content is the linked PDF (`pdf_url`).
- Bulk/advanced search and older holdings live behind the paid DNSA, not here.
