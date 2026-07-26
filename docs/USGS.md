---
name: usgs
description: "USGS Earthquake Hazards — worldwide earthquake catalog: magnitude, place, time, coordinates, depth for recent and historical quakes. Use for any earthquake query, global."
keywords: "USGS, earthquake, seismic, magnitude, quake catalog, GeoJSON, natural disasters"
routes: "/usgs/earthquakes"
---

# USGS

USGS Earthquake Hazards Program — FDSN event web service. Keyless.

## Endpoints

### `GET /usgs/earthquakes`

Worldwide earthquake catalog as GeoJSON.

**Params:** `starttime` / `endtime` (`YYYY-MM-DD`; default window is the last 30 days) · `minmagnitude` · `orderby` (`time` | `time-asc` | `magnitude` | `magnitude-asc`) · `limit` (default 10, max 1000)

## Quirks & notes

- Upstream `earthquake.usgs.gov/fdsnws/event/1/query`; the client pins `format=geojson`.
- Quakes are GeoJSON `features`: magnitude in `properties.mag`, human-readable `properties.place`, epoch-ms `properties.time`, `[lon, lat, depth-km]` in `geometry.coordinates`.
- Upstream hard-caps `limit` at 20000 and 400s on wider requests; also supports bounding-box/radius params not exposed here.
