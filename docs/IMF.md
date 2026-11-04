---
name: imf
description: "IMF macroeconomic data from the IMF's own SDMX API — World Economic Outlook (WEO) history and forecasts (real GDP growth, inflation, unemployment, government debt, current account by country, ~5 years ahead), monthly CPI, balance of payments, trade (IMTS), Fiscal Monitor. Use for IMF projections and cross-country macro series."
keywords: "IMF, International Monetary Fund, World Economic Outlook, WEO, forecasts, projections, real GDP growth, inflation, unemployment, government debt, current account, CPI, balance of payments, SDMX"
routes: "/imf/structure/{dataset}, /imf/{dataset}/{key}"
---

# IMF (IMF SDMX API)

IMF macroeconomic data — World Economic Outlook (WEO) history and forecasts,
CPI, balance of payments (BOP), trade (IMTS), Fiscal Monitor (FM) and every
other IMF dataflow — from the IMF's own SDMX API, keyless, as SDMX-JSON.

**Transport history.** The legacy SDMX host (`dataservices.imf.org`) went
NXDOMAIN in 2026, so the client moved to DBnomics — which stopped indexing the
IMF in September 2025 (`api.db.nomics.world/v22/providers/IMF` → `indexed_at`
2025-09-04), leaving `/imf` frozen at the **April 2025** WEO. Since 2026-11-04
the client reads `api.imf.org`, which carries the current releases (its WEO
dataflow, v9.0.0, projects to 2031).

## Routes

- `GET /imf/{dataset}/{key}` — the series `key` matches in dataflow `dataset`.
  Params: `start_period`, `end_period` (`YYYY`, `YYYY-MM`, `YYYY-Qn`).
  Example: `/imf/WEO/USA.NGDP_RPCH.A?start_period=2024&end_period=2027` → US real
  GDP growth, %, 2024–2027 (the later years are IMF forecasts).
- `GET /imf/structure/{dataset}` — the dataflow, its data structure definition
  (dimension order) and the codelists of every dimension — the codes a key may
  use. Large: ~2 MB for WEO.

## Keys

SDMX keys: dimension codes **in the dataflow's order** joined by `.`; `+`
between alternatives; an empty position means "all"; trailing dimensions may be
left off.

| Dataflow | Dimension order | Example |
| --- | --- | --- |
| `WEO` | COUNTRY.INDICATOR.FREQUENCY | `USA.NGDP_RPCH.A`, `USA+CHN.NGDP_RPCH+PCPIPCH` |
| `CPI` | COUNTRY.INDEX_TYPE.COICOP_1999.TYPE_OF_TRANSFORMATION.FREQUENCY | `USA.CPI._T.IX.M` (all-items CPI index, monthly) |

Common WEO indicators (all verified 2026-11-04):

| Indicator | Meaning |
| --- | --- |
| `NGDP_RPCH` | Real GDP growth, % |
| `NGDPD` | GDP, current US$ (in units — see the `SCALE` attribute) |
| `PCPIPCH` | Inflation, average consumer prices, % |
| `LUR` | Unemployment rate, % |
| `GGXWDG_NGDP` | General government gross debt, % of GDP |
| `BCA_NGDPD` | Current account balance, % of GDP |

Countries are ISO3 codes: USA, CHN, DEU, FRA, GBR, IND, JPN, …

**Vintages.** Frozen releases are their own dataflows — `WEO_2025_OCT_VINTAGE`,
`WEO_2026_APR_VINTAGE` — and take the same keys
(`/imf/WEO_2025_OCT_VINTAGE/USA.NGDP_RPCH.A`). Compare one with `WEO` to see how a
forecast was revised.

## Reading the response (SDMX-JSON 1.0)

- `structure.dimensions.series[]` — each dimension with its `values[]` (`id`, `name`).
- `dataSets[0].series` — keyed `"i:j:k"`: the indexes of each dimension's value.
- `…series[key].observations` — keyed by the index of the period in
  `structure.dimensions.observation[0].values`; each value is a list whose first
  element is the observation **as a string** (`"2.327686"`).
- Series attributes (`SCALE`, `DECIMALS_DISPLAYED`, `COUNTRY_UPDATE_DATE`) under
  `structure.attributes.series`.

This is the same SDMX-JSON shape `/ecb` returns.

## Upstream quirks

- Base `https://api.imf.org/external/sdmx/2.1`, keyless. **Ask for
  `Accept: application/json`** — the SDMX media types
  (`application/vnd.sdmx.data+json`) and `format=jsondata` get XML back. The
  client sends it.
- `data/{dataflow}/{key}` resolves the dataflow without an agency
  (`WEO` = `IMF.RES,WEO,latest`).
- Errors: an unknown dataflow is a 404 ("No such dataflow found"); an unknown
  code inside the key is a 400 with an unhelpful message ("Current context not
  Object but Array") — check the codes with `/imf/structure/{dataset}`.
