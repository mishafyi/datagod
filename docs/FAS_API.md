---
name: fas
description: "FAS Intelligence Resource Program (irp.fas.org) — the Federation of American Scientists' mirror of US intelligence and military documents: NSA, CIA and DIA agency pages, surveillance and collection programs, official documents, DoD directives, congressional oversight, foreign intelligence services. Full-text pages plus PDF links."
keywords: "FAS, Federation of American Scientists, Intelligence Resource Program, IRP, NSA, CIA, DIA, surveillance, intelligence programs, DoD directives, military, congressional oversight"
routes: "/fas/index/{path}, /fas/page/{path}, /fas/sections"
---

# FAS — Intelligence Resource Program (irp.fas.org)

The Federation of American Scientists' Intelligence Resource Program: the
working mirror of US intelligence and military documents that the official
reading rooms wall off — agency pages (NSA, CIA, DIA…), collection programs,
official documents, DoD directives, congressional oversight, foreign
intelligence services. Many pages are full-text mirrors of primary documents.
Keyless, no bot wall. Client: `app/clients/fas.py`.

## Endpoints

### `GET /fas/sections`

The curated registry of verified sections (all probed 200 on 2026-08-08):
`nsa`, `cia`, `dia`, `agency`, `program/collect`, `offdocs`, `doddir`,
`world`, `congress`, `ops`. Returns `{sections: [{path, name, url}]}`.

### `GET /fas/index/{path}`

An index page's links: `{path, title, url, links: [{path, title, url, is_pdf,
is_index}]}` — every same-site link at or below the page's directory, including
child sub-indexes (`uk/index.html`, which is what `/world` and `/congress` are
made of). Navigation links that point up or out (`../index.html`, fas.org) and
anchors are dropped.

### `GET /fas/page/{path}`

A content page: `{path, title, text (≤16,000 chars), pdfs: [{title, url}] (≤15),
url}`.

## Quirks & notes

- Two page shapes — index (a list of links) and content (text + PDFs); both
  routes parse either, so pick by what you need.
- A path without a file extension gets a trailing slash (directory index).
- **Documents are not pages:** index pages link PDFs, spreadsheets and images
  (`/fas/index/nsa` alone lists ~77 PDFs). Asking `/fas/page` for one answers
  **415** with the direct URL — download it yourself (before 2026-11-04 the
  route returned the file's bytes as "text").
- Static HTML scraped with selectolax; redirects are followed.
