---
name: ecb
description: "ECB Data Portal — euro-area statistics via SDMX: EXR daily reference exchange rates (USD/EUR and all pairs), ICP inflation, interest rates, money supply. Use for euro FX rates and euro-area monetary data."
keywords: "ECB, euro exchange rate, USD/EUR, reference rate, euro area, inflation ICP, SDMX, European Central Bank"
routes: "/ecb/{flow_ref}/{key}"
---

# ECB

ECB Data Portal — euro-area statistics via SDMX (jsondata). Keyless.

## Endpoints

### `GET /ecb/{flow_ref}/{key}`

One series from a dataflow, e.g. `/ecb/EXR/D.USD.EUR.SP00.A` (daily USD/EUR reference rate).

**Params:** `start_period`, `end_period` (`YYYY-MM-DD`, or `YYYY` / `YYYY-MM` per series frequency)

## Quirks & notes

- Upstream base `data-api.ecb.europa.eu/service/data`; the client pins `format=jsondata` (SDMX-JSON).
- Observations live under `dataSets[0].series["0:0:0:0:0"].observations`; dimension labels under `structure.dimensions`.
- Wildcard key positions work (`D..EUR.SP00.A` = all currencies against EUR).
- An empty result for a valid key (e.g. weekend-only date range for daily FX) returns 200 with no series.
