---
name: eonet
description: "NASA EONET — global natural-event tracker: open wildfires, severe storms, volcanoes, floods, sea ice, with coordinates and source links. Use for currently-burning wildfires and other ongoing natural events worldwide."
keywords: "NASA EONET, wildfires, natural events, volcanoes, severe storms, floods, natural disasters, event tracker"
routes: "/eonet/events, /eonet/categories"
---

# EONET

NASA Earth Observatory Natural Event Tracker (EONET) v3. Keyless.

## Endpoints

### `GET /eonet/events`

Curated natural events with geometry (point/polygon per date) and source links.

**Params:** `category` (e.g. `wildfires`, `severeStorms`, `volcanoes` — ids from `/eonet/categories`) · `status` (`open` | `closed` | `all`, default `open`) · `limit` (default 10, max 1000) · `days` (last N days)

### `GET /eonet/categories`

All 13 event categories with ids and descriptions.

## Quirks & notes

- This is the **keyless global-wildfire feed standing in for Copernicus EFFIS** — EFFIS's data lacks a clean public JSON API, EONET's `wildfires` category is the practical substitute.
- Events are aggregated from source feeds (InciWeb, GDACS, Smithsonian volcanism…) — each event links its `sources`.
- `geometry` is a list over time (an event can move/grow); coordinates are `[lon, lat]`.
- Open events have `closed: null`; EONET is curated, not real-time-exhaustive.
