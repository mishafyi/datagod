---
name: nws
description: "US National Weather Service — active weather alerts (warnings, watches, advisories) by state: severe storms, floods, heat, fire weather. Use for current US weather hazards."
keywords: "NWS, weather alerts, warnings, watches, severe weather, storm, flood, heat advisory, api.weather.gov"
routes: "/nws/alerts"
---

# NWS

US National Weather Service (api.weather.gov) — active alerts. Keyless, but User-Agent required.

## Endpoints

### `GET /nws/alerts`

Active alerts as GeoJSON features (headline, severity, affected areas, effective/expires).

**Params:** `area` (two-letter state or marine code, e.g. `CA`) · `severity` (`Extreme`, `Severe`, `Moderate`, `Minor`, `Unknown`)

## Quirks & notes

- **The API 403s without a User-Agent header.** The client always sends `DataGod/1.0 (github.com/mishafyi/datagod)` (NWS asks for contact info in the UA).
- Alerts in `features[].properties`: `event`, `headline`, `severity`, `areaDesc`, `effective`, `expires`.
- More filters exist upstream (`zone`, `point`, `status`, `urgency`) — only `area`/`severity` are exposed here.
