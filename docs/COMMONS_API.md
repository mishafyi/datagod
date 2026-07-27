---
name: commons
description: "Wikimedia Commons — video-file search returning direct file URLs plus per-file license metadata (LicenseShortName: CC-BY / CC-BY-SA / PD) and author. Use for free-licensed reusable video clips; credit per file."
keywords: "wikimedia commons, video, clips, footage, creative commons, CC-BY, CC-BY-SA, public domain, webm, direct file URL, attribution"
routes: "/commons/search"
---

# Wikimedia Commons

MediaWiki action API at `commons.wikimedia.org/w/api.php`. Keyless; DataGod
sends the polite `DataGod/1.0 (github.com/mishafyi/datagod)` User-Agent
(Wikimedia asks for one on all API traffic).

## Endpoints

### `GET /commons/search`

`generator=search` over the File: namespace with `filetype:video` forced into
the query, `prop=imageinfo&iiprop=url|extmetadata|size|mime`. Results under
`query.pages{}` (keyed by pageid), each with `title` (File:…) and
`imageinfo[0]`: `url` (**direct file URL** on upload.wikimedia.org), `size`,
`width/height`, `duration`, `mime`, and `extmetadata`.

**Params:** `q` (required) · `limit` (default 10, max 50)

## Quirks & notes

- **License varies per file** — the caller must read
  `imageinfo[0].extmetadata.LicenseShortName.value` (e.g. `CC BY-SA 4.0`,
  `CC0`, `Public domain`) plus `Artist` / `Attribution`, and credit
  accordingly. CC-BY-SA also requires share-alike on adaptations.
- Commons video is mostly **webm/ogv** (patent-free formats) — expect
  `video/webm`, not mp4; transcode downstream if the pipeline needs mp4.
- `query.pages` is an **object keyed by pageid**, not a list; iterate values.
- Search relevance is meh — combine terms (`gsrsearch` supports quoted phrases
  and `incategory:`) rather than paging deep.
