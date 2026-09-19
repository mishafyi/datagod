---
name: wikipedia
description: "Wikipedia — page summaries (lead section + thumbnail), whole articles as plain text, full-text article search, and daily pageview counts (attention/popularity over time). Use for encyclopedic lookups, background research, and gauging public attention on a topic."
keywords: "Wikipedia, page summary, article search, pageviews, popularity, attention, encyclopedia, Wikimedia"
routes: "/wikipedia/summary/{title}, /wikipedia/article/{title}, /wikipedia/search, /wikipedia/pageviews/{title}"
---

# Wikipedia

English Wikipedia (REST + action APIs) and Wikimedia pageviews. Keyless.

## Endpoints

### `GET /wikipedia/summary/{title}`

Lead-section summary of one page: extract, description, thumbnail, canonical URLs.

### `GET /wikipedia/article/{title}`

The whole article as plain text (MediaWiki TextExtracts, `explaintext`), redirects followed: the text is under `query.pages[0].extract`, section headings kept as `== Heading ==`, and `query.redirects` says where a redirect went. A title with no article answers **404** (error-dict), as the summary endpoint does. Titles may contain `/` (`AC/DC`).

### `GET /wikipedia/search`

Full-text article search (MediaWiki action API); hits under `query.search`, total in `query.searchinfo.totalhits`.

**Params:** `q` (required) · `limit` (default 10, max 50)

### `GET /wikipedia/pageviews/{title}`

Daily pageview counts (all access, all agents) from the Wikimedia metrics API.

**Params:** `start`, `end` (required, `YYYYMMDD`, inclusive)

## Quirks & notes

- **User-Agent:** Wikimedia wants a descriptive UA on all API traffic and the pageviews endpoint requires one — the client sends `DataGod/1.0 (github.com/mishafyi/datagod)` on every call.
- **Throttling:** Wikimedia answers bursts with 429 (sometimes 503). Every call waits it out — the response's `Retry-After` (capped at 20s), else 2s then 5s — and only a third refusal comes back as the error-dict (`upstream_status` 429). A caller reading several articles in a row no longer fails on the second one.
- Use underscores in titles (`Albert_Einstein`): the summary endpoint answers exact titles directly and redirects near-misses (the shared client doesn't follow redirects → error-dict).
- Pageview timestamps come back as `YYYYMMDD00` (the trailing `00` is the hour granularity marker); data lags ~1 day.
- Three different upstream hosts: `en.wikipedia.org/api/rest_v1` (summary), `en.wikipedia.org/w/api.php` (article, search), `wikimedia.org/api/rest_v1/metrics` (pageviews).
