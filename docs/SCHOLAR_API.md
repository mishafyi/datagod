---
name: scholar
description: "Academic literature search (Google Scholar, unofficial scrape) — finds scholarly papers, articles, and citations for a keyword and ranks them by citation count or citations-per-year. Returns Author, Title, Citations, Year, Publisher, Venue, snippet, source URL, and PDF link. Use to find the most-cited or most-influential papers in a research field. Brittle: Google blocks automated access (CAPTCHA / 429), so it often returns an error or empty result without a clean IP."
keywords: "Google Scholar, academic papers, scholarly articles, research papers, citations, citation count, cited by, bibliometrics, literature search, most cited, publications, authors, venue, journal, PDF, cit/year, ranking"
routes: "/scholar/search"
---

# Google Scholar API Reference

**Upstream**: `https://scholar.google.com/scholar` (HTML search results page).
**Auth**: None / not possible. Google Scholar has **no public API**; this is an HTML scrape.
**Status**: Unofficial and **brittle**. Vendored and adapted from [WittmannF/sort-google-scholar](https://github.com/WittmannF/sort-google-scholar) (MIT). See `app/clients/scholar.py`.

> ## ⚠️ CAVEAT — Google Scholar aggressively blocks automated access
>
> Google Scholar fingerprints and rate-limits non-browser traffic. From a
> datacenter / cloud IP (e.g. the production server) it will frequently serve a
> **robot / CAPTCHA wall** or **HTTP 429** instead of results, and may IP-block
> after a few requests. When that happens this client returns the standard
> **error-dict** (it does **not** raise, hang, or attempt to solve a CAPTCHA).
>
> Consequences:
> - Expect intermittent `502` responses (the middleware maps the connect/parse
>   error and the explicit block to a Bad Gateway) or an error envelope.
> - Larger `nresults` (more pages = more requests) triggers blocking sooner.
> - A **clean / residential IP** (or a VPN) is effectively required for reliable
>   results. There is no API key that fixes this.
>
> Unlike the upstream `sortgs` CLI, this wrapper has **no Selenium CAPTCHA
> fallback** — that fallback blocks on an interactive `input()` prompt and is
> unusable in a server. A block is surfaced as an error, not solved.

## Endpoint

### `GET /scholar/search`

Search Google Scholar for a keyword and rank the resulting papers.

**Params:**

| Param | In | Type | Default | Notes |
|-------|----|------|---------|-------|
| `keyword` | query | string | — (required) | Search query. Scholar operators work: `OR`, `-term`, and `"exact phrase"`. |
| `nresults` | query | integer | 20 | Papers to fetch. Scholar paginates by 10, so this is rounded **up** to a multiple of 10 of pages fetched. Higher = more requests = blocked sooner. Suggested cap `le=100`. |
| `sort_by` | query | string | `Citations` | Column to sort by, descending. `Citations` or `cit/year`. Any other value falls back to `Citations`. |
| `start_year` | query | integer | none | Lower publication-year bound (Scholar `as_ylo`). Omit for no lower bound. |
| `end_year` | query | integer | none | Upper publication-year bound (Scholar `as_yhi`). Omit for current year. |

## Response shape (success)

The client does **not** pass the upstream HTML through; it parses it into a
records list (the one intentional exception to the pass-through rule, like
`wilson`/`nsarchive`). After the DataGod envelope wraps it, `data` is:

```json
{
  "results": [
    {
      "Rank": 1,
      "Author": "S Shalev-Shwartz, S Ben-David",
      "Title": "Understanding machine learning: From theory to algorithms",
      "Citations": 3166,
      "Year": 2014,
      "Publisher": " cambridge.org",
      "Venue": "books.google.com",
      "Content": "…snippet/preview text from the result…",
      "Source": "https://…",
      "PDF": "https://…/foreword.pdf",
      "cit/year": 352
    }
  ],
  "count": 1,
  "keyword": "machine learning"
}
```

Field notes (extracted from each `<div class="gs_or">` result):

- **Rank** — original Scholar result order (1-based) before sorting.
- **Citations** — parsed from the "Cited by N" link; `0` if absent.
- **Year** — first 4-digit year in the byline; `0` if not found.
- **Author / Publisher / Venue** — split out of the grey byline (`gs_a`). Missing
  parts get sentinel strings (`"Author not found"`, `"Publisher not found"`,
  `"Venue not found"`).
- **Content** — the result snippet (`gs_rs`); `"Content not found"` if absent.
- **Source** — the title link's `href`.
- **PDF** — direct PDF link if Scholar exposes one (`gs_ggs`), else `"No PDF link"`.
- **cit/year** — `Citations / (end_year + 1 - min(Year, end_year))`, rounded.

A successful-but-empty search (Scholar returned a page with no `gs_or` results)
yields `{"results": [], "count": 0, "keyword": "…"}` — distinct from a block,
which returns the error-dict.

## Response shape (error / blocked)

Per the repo contract, failures return:

```json
{ "error": true, "source": "scholar", "upstream_status": <int>, "message": "<str>" }
```

- A CAPTCHA / robot wall → `message` says Google served a robot/CAPTCHA wall (and
  how many results were collected before the block), `upstream_status` `0`.
- An HTTP error from Google (e.g. `429`, `403`) → `upstream_status` is that code.
- A network / parse failure → `upstream_status` `0`.

## Implementation notes

- Sync scrape (`requests` + `BeautifulSoup`) dispatched via `asyncio.to_thread`
  (same sync-wrapping pattern as `yfin.py`); the DataFrame is converted to
  records with NaN → `null`.
- A browser-like `User-Agent` + `Accept-Language` is sent; bare `requests` with
  no UA is blocked faster.
- Dropped from the upstream `sortgs` tool: the Selenium CAPTCHA fallback,
  matplotlib plotting, CSV export, and the argparse CLI.
- **Citation-count fix vs upstream**: the vendored `sortgs` 1.0.7 calls
  `get_citations(str(div.format_string))`, but `format_string` is a bound
  BeautifulSoup *method*, so the "Cited by N" regex never matches and every
  citation count comes back `0`. This client uses the correct `str(div)`, so
  citation counts are populated.
