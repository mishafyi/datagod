---
name: internetarchive
description: "Internet Archive — keyless search of archival films, newsreels, and public-domain footage (prelinger, newsreels collections) plus per-item metadata with direct download paths. License is per item (licenseurl)."
keywords: "internet archive, archive.org, newsreels, prelinger, public domain footage, archival film, movies, download, licenseurl"
routes: "/archive/search, /archive/item/{identifier}"
---

# Internet Archive

`archive.org` advanced search + metadata APIs. Keyless, no account.

## Endpoints

### `GET /archive/search`

`advancedsearch.php` pass-through. Hits under `response.docs[]` with
`identifier`, `title`, `year`, `licenseurl`, `mediatype`.

**Params:** `q` (required; Lucene syntax — free text is auto-scoped to
`(q) AND mediatype:movies` unless the query already contains `mediatype:`) ·
`rows` (default 10, max 50) · `page` (default 1)

Useful query filters: `collection:prelinger`, `collection:newsreels`,
`year:[1940 TO 1959]`, `licenseurl:*publicdomain*`.

### `GET /archive/item/{identifier}`

`https://archive.org/metadata/{identifier}` — full item record: `metadata`
(title, description, `licenseurl`, collection) + `files[]` (name, format,
size). Download a file as
`https://archive.org/download/{identifier}/{file.name}` (URL-encode the name).

## Quirks & notes

- **License is PER ITEM** — always check `licenseurl` (or its absence) before
  reuse. The public-domain collections (`prelinger`, `newsreels`,
  `classic_tv`…) are the harvest target; plenty of items on archive.org are
  still under copyright.
- `licenseurl` is empty for many genuinely-PD items (uploader never set it) —
  collection membership is the stronger signal.
- `files[]` mixes derivatives (h.264 mp4, ogv, thumbnails) with originals and
  XML sidecars; filter by `format` (e.g. "h.264", "MPEG4").
- Download URLs 302-redirect to a datanode — follow redirects.
