"""Treasury Fiscal Data — Debt, revenue, spending, rates."""

from . import UpstreamJSON, safe_get

BASE = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"


async def debt(limit: int = 5) -> UpstreamJSON:
    """National debt to the penny."""
    return await safe_get(f"{BASE}/v2/accounting/od/debt_to_penny", "treasury", params={
        "sort": "-record_date", "page[size]": str(limit),
    })


async def interest_rates(limit: int = 5) -> UpstreamJSON:
    """Average interest rates on Treasury securities."""
    return await safe_get(f"{BASE}/v2/accounting/od/avg_interest_rates", "treasury", params={
        "sort": "-record_date", "page[size]": str(limit),
    })


async def exchange_rates(limit: int = 5) -> UpstreamJSON:
    """Treasury exchange rates."""
    return await safe_get(f"{BASE}/v1/accounting/od/rates_of_exchange", "treasury", params={
        "sort": "-record_date", "page[size]": str(limit),
    })
