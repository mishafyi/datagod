---
name: vault
description: "FBI Vault (vault.fbi.gov, via the Wayback mirror) — the FBI's FOIA library of released files on famous subjects: COINTELPRO, Roswell and UFOs, Majestic 12, Watergate, VENONA, the Rosenbergs, Alger Hiss, Martin Luther King Jr., the KKK. Browse subject → folders → files → PDFs."
keywords: "FBI, FBI Vault, FOIA, FBI files, COINTELPRO, Roswell, UFO, Majestic 12, Watergate, VENONA, Rosenberg, Martin Luther King, KKK, declassified"
routes: "/vault/page/{path}, /vault/subjects"
---

# FBI Vault (via the Wayback Machine)

The FBI's FOIA library (`vault.fbi.gov`): released files on famous subjects.
Keyless. Client: `app/clients/vault.py`.

**Why the Wayback mirror.** vault.fbi.gov answers every server-side client with
403 — the same Akamai wall as cia.gov — so the client reads web.archive.org's
captures through the shared `app/clients/_wayback.py` (capture selection,
interstitial skipping, gunzip, throttle retries: see `docs/CIA_API.md`).

## Endpoints

### `GET /vault/subjects`

The curated registry of famous subjects (static): `cointel-pro`, `roswell`,
`majestic-12`, `unusual-phenomena`, `watergate`, `solo`, `venona`,
`rosenberg-case`, `alger-hiss`, `julius-and-ethel-rosenberg`,
`martin-luther-king-jr`, `the-ku-klux-klan`. Returns
`{subjects: [{path, name, url}]}`.

### `GET /vault/page/{path}`

One Vault page — a subject, a folder or a file page:
`{path, title, description (≤16,000 chars), folders: [{path, title, url}],
files: [{path, title, url}], pdfs: [{title, url}] (≤20), url, archived_url}`.

## Quirks & notes

- The Vault is a Plone site that **nests**: a subject page lists sub-folders
  (`a.contenttype-folder`) and file pages (`a.contenttype-file`); a file page
  carries the document PDF (`/at_download/` links). Walk it page by page —
  subject → folders → files — feeding each `path` back into `/vault/page`.
- No per-query search (Vault search pages aren't archived per query): start
  from `/vault/subjects`.
- A 404 means Wayback has no usable capture of that path; pick another.
