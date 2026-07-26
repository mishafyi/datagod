---
name: eurostat
description: "Eurostat — official EU statistics: population, GDP, inflation (HICP), unemployment, energy, trade for EU members and aggregates. Use for any EU/euro-area country statistic."
keywords: "Eurostat, EU statistics, Europe GDP, HICP, EU population, unemployment Europe, JSON-stat, EU27"
routes: "/eurostat/{dataset}"
---

# Eurostat

Eurostat dissemination API — official EU statistics as JSON-stat 2.0. Keyless.

## Endpoints

### `GET /eurostat/{dataset}`

One dataset, e.g. `tps00001` (population on 1 January), `nama_10_gdp` (GDP aggregates).

**Params:** every query param passes through verbatim as a dimension filter — e.g. `?geo=EU27_2020&time=2024`, `?geo=DE&geo=FR&time=2023` (dimensions may repeat).

## Quirks & notes

- Upstream base `ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data`; the client pins `format=JSON&lang=EN`.
- Response is JSON-stat 2.0: values in the flat `value` map, decoded via `dimension` + `size` (not row records).
- Unfiltered large datasets are rejected upstream with an explanatory error — always filter big ones by `geo`/`time`.
- Dataset codes are browsable in Eurostat's data navigation tree ("data browser" codes work as-is).
