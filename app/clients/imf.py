"""IMF macroeconomic series via DBnomics — WEO, IFS, BOP, GFS and every other
IMF dataset, keyless JSON.

The IMF's legacy SDMX host (dataservices.imf.org) was decommissioned in 2026
(NXDOMAIN), and its replacement (api.imf.org) renamed every dataflow behind an
XML-first interface. DBnomics (db.nomics.world — the open macroeconomic data
aggregator run by CEPREMAP) mirrors the full IMF catalog with stable dataset
codes, so it is the transport; the data and the series semantics are the IMF's.

Series keys are DBnomics masks, e.g. dataset WEO, series USA.NGDP_RPCH
(US real GDP growth, %) — see docs/IMF.md for the common ones.
"""

from . import UpstreamJSON, safe_get

BASE = "https://api.db.nomics.world/v22"


async def series(dataset: str, key: str, limit: int = 100) -> UpstreamJSON:
    """One IMF series with observations. dataset e.g. WEO (latest vintage),
    key e.g. USA.NGDP_RPCH. Periods include IMF forecast years where the
    dataset carries them (WEO runs ~5 years ahead)."""
    return await safe_get(
        f"{BASE}/series/IMF/{dataset}:latest/{key}",
        "imf",
        params={"observations": 1, "limit": limit},
        follow_redirects=True,
    )


async def structure(dataset: str) -> UpstreamJSON:
    """Dataset metadata (dimensions, code lists) for an IMF dataset code."""
    return await safe_get(
        f"{BASE}/datasets/IMF/{dataset}:latest",
        "imf",
        follow_redirects=True,
    )
