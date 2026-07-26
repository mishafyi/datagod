"""UN Comtrade — global goods-trade flows (keyless public preview: ≤500 records, rate-limited)."""

from . import UpstreamJSON, safe_get

BASE = "https://comtradeapi.un.org/public/v1/preview"


async def preview(reporter_code: str = "", period: str = "", partner_code: str = "",
                  cmd_code: str = "", flow_code: str = "") -> UpstreamJSON:
    """Annual HS goods trade (C/A/HS). Country codes are UN M49 numeric
    (842 = USA, 156 = China, 0 = World); cmd_code is an HS code or TOTAL;
    flow_code M = imports, X = exports."""
    params: dict = {}
    if reporter_code:
        params["reporterCode"] = reporter_code
    if period:
        params["period"] = period
    if partner_code:
        params["partnerCode"] = partner_code
    if cmd_code:
        params["cmdCode"] = cmd_code
    if flow_code:
        params["flowCode"] = flow_code
    return await safe_get(f"{BASE}/C/A/HS", "comtrade", params=params)
