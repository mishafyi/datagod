---
name: nasa_images
description: "NASA Image and Video Library — public-domain space/science videos, images, and audio (launches, Apollo/Artemis/ISS, planets, astronauts) with direct downloadable mp4 renditions per asset. Use for keyless public-domain space footage."
keywords: "NASA, space video, footage, images, audio, public domain, launches, Apollo, Artemis, ISS, Mars, astronauts, mp4"
routes: "/nasa/search, /nasa/asset/{nasa_id}"
---

# NASA Image and Video Library

`images-api.nasa.gov` — the API behind images.nasa.gov. Keyless, no account.

## Endpoints

### `GET /nasa/search`

Search the library. Hits under `collection.items[]`; each item has `data[0]`
(title, `nasa_id`, description, date_created, keywords) and preview `links`.

**Params:** `q` (required) · `media_type` (`video` | `image` | `audio`, default `video`) · `year_start` / `year_end` (YYYY) · `page` (default 1) · `page_size` (default 10, max 100)

### `GET /nasa/asset/{nasa_id}`

The asset manifest for one `nasa_id` (from search): `collection.items[].href`
are **direct downloadable file URLs** — for videos usually `~orig.mp4`,
`~large.mp4`, `~medium.mp4`, `~small.mp4`, a `.srt` caption file, and thumbnails.

## Quirks & notes

- **Everything is public domain** (NASA media is not copyrighted); crediting
  "NASA" is courteous. The rare third-party items note it in their description.
- Search matches all metadata fields; `media_type` also accepts comma-separated
  values upstream, but the DataGod route pins one of `video|image|audio`.
- Upstream pagination caps out at 10,000 total results (`page * page_size`).
- Asset URLs live on `images-assets.nasa.gov` and need no auth or headers.
