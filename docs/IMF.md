---
name: imf
description: "IMF SDMX-JSON — macroeconomic time series from IMF databases (IFS International Financial Statistics, DOT Direction of Trade, BOP Balance of Payments, GFS…): CPI, exchange rates, reserves, trade. Use for IMF-sourced country macro series."
keywords: "IMF, International Financial Statistics, IFS, CPI, balance of payments, direction of trade, SDMX, macroeconomic time series"
routes: "/imf/{database}/{key}, /imf/structure/{database}"
---

# IMF

IMF SDMX-JSON service — CompactData time series + dataflow structures. Keyless.

## Endpoints

### `GET /imf/{database}/{key}`

Time series by SDMX key, e.g. `/imf/IFS/M.US.PCPI_IX` (monthly US CPI index).

**Params:** `start_period`, `end_period` (years like `2020`, or `2020-01`)

### `GET /imf/structure/{database}`

Data structure (dimensions + code lists) for a database, e.g. `IFS`.

## Quirks & notes

- Upstream base `http://dataservices.imf.org/REST/SDMX_JSON.svc` (plain HTTP).
- **Slow and flaky by reputation** — long stalls and frequent 5xx; calls ride the shared 30s timeout and surface failures as the standard error-dict (502).
- **Currently DNS-dead (checked 2026-07-25):** `dataservices.imf.org` no longer resolves (NXDOMAIN on 1.1.1.1 and 8.8.8.8). The IMF migrated to its new data portal (data.imf.org); the legacy SDMX_JSON host appears decommissioned. Routes stay wired to the documented contract and return 502 until the host answers again — rewire to the new portal's API if it stays dead.
- Series data lives under `CompactData.DataSet.Series.Obs`; keys are frequency-prefixed (`M.` monthly, `Q.`, `A.`).
