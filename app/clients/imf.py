"""IMF macroeconomic data from the IMF's own SDMX API (api.imf.org) — WEO,
CPI, BOP, IMTS, FM and every other IMF dataflow, keyless SDMX-JSON.

Transport history: the legacy SDMX host (dataservices.imf.org) went NXDOMAIN
in 2026, so this client moved to DBnomics — which stopped indexing the IMF in
September 2025, leaving /imf frozen at the April 2025 WEO. api.imf.org answers
SDMX-JSON 1.0 when asked with `Accept: application/json` (the sdmx+json media
types get XML back) and carries the current releases.

Keys are SDMX keys: dimension codes in the dataflow's order joined by ".", "+"
between alternatives, an empty position for "all"; trailing dimensions may be
left off. WEO is COUNTRY.INDICATOR.FREQUENCY, e.g. USA.NGDP_RPCH.A — or
USA+CHN.NGDP_RPCH+PCPIPCH (both countries, both indicators, every frequency).
See docs/IMF.md for common keys and how to read the response.
"""

from . import UpstreamJSON, safe_get

BASE = "https://api.imf.org/external/sdmx/2.1"
HEADERS = {"Accept": "application/json"}


async def series(dataset: str, key: str, start_period: str = "",
                 end_period: str = "") -> UpstreamJSON:
    """Observations for the series `key` matches in dataflow `dataset` (e.g. WEO,
    CPI, BOP, or a frozen vintage like WEO_2025_OCT_VINTAGE). Periods are
    YYYY, YYYY-MM or YYYY-Qn; WEO runs ~5 forecast years ahead."""
    params: dict = {}
    if start_period:
        params["startPeriod"] = start_period
    if end_period:
        params["endPeriod"] = end_period
    return await safe_get(f"{BASE}/data/{dataset}/{key}", "imf", params=params, headers=HEADERS)


async def structure(dataset: str) -> UpstreamJSON:
    """The dataflow's structure: its data structure definition (dimension order)
    plus the codelists of every dimension (codes the key may use). Large — the
    WEO answer is ~2 MB."""
    return await safe_get(f"{BASE}/dataflow/all/{dataset}/latest", "imf",
                          params={"references": "descendants", "detail": "referencepartial"},
                          headers=HEADERS)
