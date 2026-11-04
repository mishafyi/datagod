---
name: cia
description: "Declassified CIA documents (CIA FOIA Electronic Reading Room, read through the Wayback Machine mirror because cia.gov blocks server clients) — famous collections (STARGATE, UFOs, Bay of Pigs, President's Daily Brief, Vietnam, Berlin Tunnel, Soviet Navy, Warsaw Pact) and single documents by CREST number with body text and PDF. No full-text search: browse collections or arrive with a document number from NSArchive, NARA or FRUS."
keywords: "CIA, declassified, FOIA, reading room, CREST, intelligence, STARGATE, remote viewing, UFOs, Bay of Pigs, President's Daily Brief, Cold War, espionage, covert action"
routes: "/cia/collection/{slug}, /cia/collections, /cia/document/{doc_path}"
---

# CIA FOIA Electronic Reading Room (via the Wayback Machine)

Declassified CIA documents from the CIA FOIA Electronic Reading Room
(`www.cia.gov/readingroom`). Keyless. Client: `app/clients/cia.py`.

**Why the Wayback mirror.** cia.gov sits behind Akamai TLS-fingerprint bot
protection: every server-side HTTP client gets an infinite 302 loop or a flat
403, whatever its headers (verified 2026-08-06). The Internet Archive's crawlers
do pass, so the client reads web.archive.org's captures and returns the
**canonical cia.gov URLs** for citation alongside the archived ones. Content is
as fresh as the last crawl (days to weeks — fine for a decades-old corpus).

## Endpoints

### `GET /cia/collections`

The curated registry of famous collections (static; every slug verified against
the live mirror 2026-08-08): `stargate`, `ufos-fact-or-fiction`,
`bay-pigs-release`, `argentina-declassification-project-dirty-war-1976-83`,
`presidents-daily-brief-1969-1977`, `vietnam-histories`, `berlin-tunnel`,
`cia-analysis-soviet-navy`, `atomic-spies-ethel-and-julius-rosenberg`,
`cia-analysis-warsaw-pact-forces`. Returns `{collections: [{slug, name, url}]}`.

### `GET /cia/collection/{slug}`

One collection page: `{slug, page, title, description (≤2,000 chars),
documents: [{path, title, url}], url, archived_url}`.
**Params:** `page` — the site's own 0-based listing pager.

### `GET /cia/document/{doc_path}`

One document by its path segment, e.g. `cia-rdp96-00788r001700210016-5`:
`{path, title, meta, body (≤40,000 chars), pdf_url, pdf_archived_url, url,
archived_url}`. `meta` maps each field label to its value (document type,
dates, classification, …) as the page shows them.

## Quirks & notes

- **No full-text search** — cia.gov search pages aren't archived per query.
  Browse the collections, or arrive with a CREST document number from
  NSArchive, NARA or FRUS (all three cite CIA document numbers).
- **Capture selection** (`app/clients/_wayback.py`, shared with `/vault`): the
  CDX index lists the 10 newest status-200 captures; captures too small to be a
  real page are ignored; the newest three are tried in turn, skipping the
  2–6 KB Akamai `bm-verify` interstitials that Wayback stored as "200"s. No
  usable capture → 404.
- `id_` captures are the original bytes and are sometimes gzip-compressed
  without a `Content-Encoding` header; the client gunzips them.
- **Wayback throttles hard** (429/503). Each fetch retries twice (2 s then 5 s,
  or the `Retry-After`), via `app/resilience.get_with_retry`; when retries run
  out the error carries the real status (429 passes through, 503 → 502).
