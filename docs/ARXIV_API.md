---
name: arxiv
description: "Scientific preprints / e-prints (arXiv.org) — full-text search across physics, math, computer science (incl. cs.AI / cs.LG / cs.CL machine-learning papers), quantitative biology, finance, statistics, and economics, by topic, author, title, abstract, or category; plus fetch a paper by its arXiv id. Use for academic papers, preprints, or research publications."
keywords: "arXiv, preprints, e-prints, scientific papers, academic papers, research papers, publications, physics, mathematics, computer science, machine learning, AI, cs.LG, cs.AI, quantitative biology, statistics, abstracts, authors, DOI, arXiv id"
routes: "/arxiv/search, /arxiv/{arxiv_id}"
---

# arXiv

Scientific preprints / e-prints (arXiv.org) — full-text search across physics, math, computer science (incl. machine-learning papers), quantitative biology, finance, statistics, and economics, by topic, author, title, abstract, or category; plus fetch a paper by its arXiv id. Use for academic papers, preprints, or research publications.

arXiv has no JSON API: its single query endpoint returns **Atom 1.0 XML**, which the client parses with `feedparser` and flattens into the response shape below. This is an intentional exception to DataGod's pass-through rule (the upstream payload is XML, not JSON).

## Upstream

- Endpoint: `https://export.arxiv.org/api/query` (the `http://` form 301-redirects to `https://`).
- Format: Atom 1.0 XML with OpenSearch (`opensearch:totalResults`, `startIndex`, `itemsPerPage`) and arXiv (`arxiv:primary_category`, `arxiv:doi`, `arxiv:journal_ref`, `arxiv:comment`) extension elements.
- Auth: none.
- Manual: https://info.arxiv.org/help/api/user-manual.html · Terms of Use: https://info.arxiv.org/help/api/tou.html

## Endpoints

### `GET /arxiv/search`

Full-text search arXiv. Maps to `arxiv.search(...)` → upstream `search_query`.

**Params:**
- `query` (query, string, required) — forwarded as `search_query`. A bare term (e.g. `electron`) searches all fields. Field prefixes work: `ti:` (title), `au:` (author), `abs:` (abstract), `cat:` (category, e.g. `cat:cs.LG`), `all:`. Boolean operators `AND` / `OR` / `ANDNOT` and quoted `"exact phrases"` work, e.g. `ti:"quantum computing" AND cat:cs.LG`.
- `start` (query, integer, default 0) — result offset for paging.
- `max_results` (query, integer, default 10, max 100) — page size.
- `sort_by` (query, string, default `relevance`) — one of `relevance`, `lastUpdatedDate`, `submittedDate`. Invalid values fall back to the arXiv default.
- `sort_order` (query, string, default `descending`) — one of `ascending`, `descending`.

### `GET /arxiv/{arxiv_id}`

Fetch one paper (or several, comma-separated) by arXiv id. Maps to `arxiv.get_by_id(...)` → upstream `id_list`.

**Params:**
- `arxiv_id` (path, string, required) — new-style `2301.00001` (optionally version-pinned `2301.00001v2`) or old-style `cond-mat/0011267`. Comma-separate to fetch several.

## Response shape

Both endpoints return the same envelope (then wrapped by DataGod's standard `{meta, data, error}` middleware):

```json
{
  "total_results": 182585,
  "start": 0,
  "items_per_page": 10,
  "entries": [
    {
      "arxiv_id": "cond-mat/0011267v1",
      "title": "The electronic structure of cuprates ...",
      "summary": "We report studies of the electronic structure ...",
      "authors": ["Mark S. Golden", "Christian Duerr", "..."],
      "published": "2000-11-15T16:19:15Z",
      "updated": "2000-11-15T16:19:15Z",
      "primary_category": "cond-mat.supr-con",
      "categories": ["cond-mat.supr-con", "cond-mat.str-el"],
      "pdf_url": "https://arxiv.org/pdf/cond-mat/0011267v1",
      "abstract_url": "http://arxiv.org/abs/cond-mat/0011267v1",
      "doi": "10.1166/jctn.2008.002",
      "journal_ref": "J. Comput. Theor. Nanosci. 5, 422-448 (2008)",
      "comment": "8 pages, 4 figures"
    }
  ]
}
```

Field mapping from the Atom entry: `arxiv_id` is the bare id parsed from `<id>` (`.../abs/{id}`, version kept); `pdf_url` is the `rel="related"` `application/pdf` link; `doi`, `journal_ref`, `comment` come from the `arxiv:` extension elements and are often `null`; `categories` is every `<category>` term, `primary_category` is `arxiv:primary_category`.

On failure the client returns the error-dict instead: `{"error": true, "source": "arxiv", "upstream_status": <int>, "message": "<str>"}`.

## Quirks

- **3-second rate limit.** arXiv's legacy-API Terms of Use ask callers to make no more than **one request every three seconds** on a single connection. The client enforces this with a module-level `RateLimiter(rate=1, period=3.0)`, so back-to-back calls (and the test suite) self-throttle.
- **Redirect required.** httpx does not follow redirects by default; the `http://` host 301s to `https://`. The client uses the `https://` BASE *and* passes `follow_redirects=True` — without it the response body would be the empty 301 page and `total_results`/`entries` would come back empty.
- **Malformed id → HTTP 400.** A badly-formed `id_list` value returns HTTP 400 with an error feed (surfaced as the error-dict, `upstream_status=400`). A well-formed but nonexistent id (e.g. `2301.99999`) returns HTTP 200 with `entries: []` and `total_results` 0.
- **Paging.** `start` is an offset (not a page number) and `max_results` is the page size. arXiv allows up to 2000 results per request and recommends paging via `start` for large result sets; DataGod caps `max_results` at 100 to match sibling routes. The total available is `total_results` (OpenSearch `totalResults`).
- **Sort.** `sortBy=relevance` is the default; `lastUpdatedDate` / `submittedDate` sort by the v-latest update / original submission date respectively. `sortOrder` defaults to `descending`.
- **Timestamps** (`published`, `updated`) are ISO-8601 UTC (`...Z`) strings, passed through verbatim from the Atom feed.
