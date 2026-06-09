"""Cross-source queries — combine data from multiple government APIs."""

import asyncio
from typing import Awaitable, TypeVar

from . import edgar, fec, house_fd, usaspending

T = TypeVar("T")


async def _safe(coro: Awaitable[T]) -> T | None:
    """Run a coroutine, returning None on any failure."""
    try:
        return await coro
    except Exception:
        return None


async def company_profile(name_or_ticker: str) -> dict:
    """Build a combined company profile from SEC + USAspending."""
    company_data, revenue, contracts = await asyncio.gather(
        _safe(edgar.company(name_or_ticker)),
        _safe(edgar.concept(name_or_ticker, "Revenues")),
        _safe(usaspending.search_awards([name_or_ticker])),
    )

    sources = sum(v is not None for v in [company_data, revenue, contracts])

    financials = None
    if revenue and "units" in revenue:
        units = revenue["units"]
        values = next(iter(units.values()), [])
        if values:
            financials = {"concept": "Revenues", "latest": values[-1]}

    return {
        "company": company_data,
        "financials": financials,
        "federal_contracts": (contracts or {}).get("results", []),
        "source_count": sources,
    }


async def politician_profile(last_name: str, first_name: str = "") -> dict:
    """Build a combined politician profile from House disclosures + FEC."""
    trades, fec_data = await asyncio.gather(
        _safe(house_fd.search_members(last_name=last_name)),
        _safe(fec.candidates()),
    )

    # Filter FEC candidates by name if we got results
    matched_candidates: list[dict] = []
    if fec_data and "results" in fec_data:
        target = last_name.upper()
        first_target = first_name.upper() if first_name else ""
        for c in fec_data["results"]:
            cand_name = (c.get("name") or "").upper()
            if target not in cand_name:
                continue
            if first_target and first_target not in cand_name:
                continue
            matched_candidates.append(c)

    display = f"{first_name} {last_name}" if first_name else last_name

    return {
        "name": display,
        "house_trades": trades or [],
        "campaign_finance": matched_candidates,
    }
