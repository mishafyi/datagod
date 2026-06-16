"""EIA — Energy production, prices, forecasts."""

from . import UpstreamJSON, safe_get
from ..config import cfg

BASE = "https://api.eia.gov/v2"


async def datasets() -> UpstreamJSON:
    """List all available EIA datasets."""
    return await safe_get(f"{BASE}/", "eia", params={"api_key": cfg.EIA_API_KEY})


async def query(route: str, frequency: str = "annual", data_field: str = "value",
                length: int = 10, offset: int = 0, sort_col: str = "period",
                sort_dir: str = "desc") -> UpstreamJSON:
    """Query any EIA dataset. route e.g. 'petroleum/pri/gnd' or 'electricity/retail-sales'."""
    return await safe_get(f"{BASE}/{route}/data/", "eia", params={
        "api_key": cfg.EIA_API_KEY,
        "frequency": frequency,
        "data[0]": data_field,
        "sort[0][column]": sort_col,
        "sort[0][direction]": sort_dir,
        "length": length,
        "offset": offset,
    })


async def gas_prices(length: int = 10) -> UpstreamJSON:
    """Shortcut: retail gasoline/diesel prices."""
    return await query("petroleum/pri/gnd", "weekly", "value", length)


async def electricity(length: int = 10, data_field: str = "revenue",
                      frequency: str = "annual") -> UpstreamJSON:
    """Shortcut: electricity retail sales. data_field e.g. 'revenue', 'sales', 'price', 'customers'."""
    return await query("electricity/retail-sales", frequency, data_field, length)
