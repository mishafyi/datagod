---
name: wikipedia
description: "Wikipedia — page summaries (lead section + thumbnail), full-text article search, and daily pageview counts (attention/popularity over time). Use for encyclopedic lookups and gauging public attention on a topic."
keywords: "Wikipedia, page summary, article search, pageviews, popularity, attention, encyclopedia, Wikimedia"
routes: "/wikipedia/summary/{title}, /wikipedia/search, /wikipedia/pageviews/{title}"
---

# Wikipedia

English Wikipedia (REST + action APIs) and Wikimedia pageviews. Keyless.

## Endpoints

### `GET /wikipedia/summary/{title}`

Lead-section summary of one page: extract, description, thumbnail, canonical URLs.

### `GET /wikipedia/search`

Full-text article search (MediaWiki action API); hits under `query.search`, total in `query.searchinfo.totalhits`.

**Params:** `q` (required) · `limit` (default 10, max 50)

### `GET /wikipedia/pageviews/{title}`

Daily pageview counts (all access, all agents) from the Wikimedia metrics API.

**Params:** `start`, `end` (required, `YYYYMMDD`, inclusive)

## Quirks & notes

- **User-Agent:** Wikimedia wants a descriptive UA on all API traffic and the pageviews endpoint requires one — the client sends `DataGod/1.0 (github.com/mishafyi/datagod)` on every call.
- Use underscores in titles (`Albert_Einstein`): the summary endpoint answers exact titles directly and redirects near-misses (the shared client doesn't follow redirects → error-dict).
- Pageview timestamps come back as `YYYYMMDD00` (the trailing `00` is the hour granularity marker); data lags ~1 day.
- Three different upstream hosts: `en.wikipedia.org/api/rest_v1` (summary), `en.wikipedia.org/w/api.php` (search), `wikimedia.org/api/rest_v1/metrics` (pageviews).
