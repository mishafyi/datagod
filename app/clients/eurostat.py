"""Eurostat — official EU statistics (JSON-stat 2.0); dimension filters pass through."""

from . import UpstreamJSON, safe_get

BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"


async def dataset(dataset_id: str, filters: list[tuple[str, str]]) -> UpstreamJSON:
    """One dataset (e.g. tps00001 = population) as JSON-stat. `filters` are
    (dimension, value) pairs forwarded verbatim (geo=DE, time=2024, …); a
    dimension may repeat (geo=DE&geo=FR). Unfiltered big datasets are rejected
    upstream with an explanatory error."""
    params = [("format", "JSON"), ("lang", "EN"), *filters]
    return await safe_get(f"{BASE}/{dataset_id}", "eurostat", params=params)
