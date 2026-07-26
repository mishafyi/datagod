# IMF (via DBnomics)

IMF macroeconomic time series — WEO, IFS, BOP, GFS and the rest of the IMF
catalog — served keyless as JSON.

**Why DBnomics:** the IMF's legacy SDMX host (`dataservices.imf.org`) went
NXDOMAIN in 2026 and its replacement (`api.imf.org`) renamed every dataflow
behind an XML-first interface. DBnomics (db.nomics.world, CEPREMAP's open
macro-data aggregator) mirrors the full IMF catalog with stable codes. The
numbers and semantics are the IMF's; DBnomics is transport.

## Routes

- `GET /imf/{dataset}/{key}` — one series with observations.
  `dataset` = IMF dataset code (latest vintage is used), `key` = the series
  mask. Example: `/imf/WEO/USA.NGDP_RPCH` → US real GDP growth (%), annual,
  including IMF forecast years (~5 ahead).
- `GET /imf/structure/{dataset}` — dataset metadata: dimensions, code lists.

## Common WEO series keys

| Key | Meaning |
| --- | --- |
| `{ISO3}.NGDP_RPCH` | Real GDP growth, % |
| `{ISO3}.PCPIPCH` | Inflation, average CPI, % |
| `{ISO3}.LUR` | Unemployment rate, % |
| `{ISO3}.GGXWDG_NGDP` | Gross government debt, % of GDP |
| `{ISO3}.BCA_NGDPD` | Current account balance, % of GDP |

ISO3 examples: USA, CHN, DEU, FRA, GBR, IND, JPN.

## Upstream

- Base: `https://api.db.nomics.world/v22`
- Keyless; `:latest` dataset refs redirect to the newest vintage
  (`follow_redirects` is on in the client).
