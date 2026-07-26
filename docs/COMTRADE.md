---
name: comtrade
description: "UN Comtrade — global goods-trade flows between countries: annual imports/exports by HS commodity code, reporter and partner country. Use for bilateral trade values and commodity-level trade."
keywords: "UN Comtrade, trade flows, imports, exports, bilateral trade, HS code, trade statistics, world trade"
routes: "/comtrade"
---

# Comtrade

UN Comtrade public **preview** — annual HS goods trade. Keyless.

## Endpoints

### `GET /comtrade`

Annual HS goods-trade records (upstream `public/v1/preview/C/A/HS`).

**Params (pass through verbatim):** `reporterCode` (UN M49 numeric, e.g. 842=USA, 156=China) · `period` (year) · `partnerCode` (M49; 0=World) · `cmdCode` (HS code or `TOTAL`) · `flowCode` (`M`=imports, `X`=exports)

## Quirks & notes

- This is the **keyless public preview**: capped at ≤500 records per call and rate-limited — for bulk pulls register a (free) subscription key against the full API instead.
- Response: `{elapsedTime, count, data, error}`; trade value in `data[].primaryValue` (US$).
- Preview rows carry numeric codes only — the `reporterDesc`/`partnerDesc`/`flowDesc` label fields come back `null` (verified live); map codes yourself.
- Country codes are UN M49 numeric, not ISO2/ISO3.
