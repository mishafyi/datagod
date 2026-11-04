"""Cross-source queries — combine data from multiple government APIs.

Clients never raise: a failed source comes back as the error-dict. Each failed
source is reported under `errors` (source → message), left out of
`source_count`, and its slot holds None / [] instead of the error-dict.
"""

import asyncio
from datetime import date
from typing import Any

from . import _error, edgar, error_dict, fec, house_fd, usaspending

# ASC 606 (2018+) filers report revenue under the first tag; older filings and
# some issuers use the second. Both are read and the newest full year wins.
REVENUE_CONCEPTS = ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues")


def _ok(name: str, result: Any, errors: dict[str, str]) -> Any:
    """`result`, or None with `errors[name]` set when it is an error-dict."""
    if isinstance(result, dict) and result.get("error") is True:
        errors[name] = str(result.get("message") or "Unknown error")
        return None
    return result


def _latest_annual(concept: dict) -> dict | None:
    """Newest full-year (~12-month) USD fact in a companyconcept payload.

    10-Ks also tag quarterly breakdowns and prior-year comparatives as fp=FY,
    so the period length decides — not the list order, which put Apple's Q4-2018
    quarter forward as its "latest" revenue."""
    best = None
    for fact in (concept.get("units") or {}).get("USD", []):
        try:
            days = (date.fromisoformat(fact["end"]) - date.fromisoformat(fact["start"])).days
        except (KeyError, TypeError, ValueError):
            continue
        key = (fact["end"], fact.get("filed", ""))
        if 350 <= days <= 380 and (best is None or key > (best["end"], best.get("filed", ""))):
            best = fact
    return best


async def _edgar_side(name_or_ticker: str) -> tuple[Any, list[Any]]:
    """(company submissions, [one companyconcept per REVENUE_CONCEPTS]) for the
    filer `name_or_ticker` resolves to — error-dicts when it doesn't resolve."""
    try:
        cik = await edgar.resolve_company(name_or_ticker)
        failure = None if cik else error_dict("edgar", 404, f"No SEC filer matches {name_or_ticker!r}")
    except Exception as exc:  # SEC's ticker map unreachable
        cik, failure = None, _error("edgar", exc)
    if failure is not None or cik is None:
        return failure, [failure for _ in REVENUE_CONCEPTS]
    company, *concepts = await asyncio.gather(
        edgar.company(cik), *(edgar.concept(cik, c) for c in REVENUE_CONCEPTS))
    return company, concepts


async def company_profile(name_or_ticker: str) -> dict:
    """Combined company profile from SEC EDGAR (CIK, ticker or company name) + USAspending."""
    (company, concepts), contracts = await asyncio.gather(
        _edgar_side(name_or_ticker), usaspending.search_awards([name_or_ticker]))

    errors: dict[str, str] = {}
    company = _ok("edgar", company, errors)
    contracts = _ok("usaspending", contracts, errors)

    financials: dict[str, Any] | None = None
    concept_errors: dict[str, str] = {}
    for concept_name, payload in zip(REVENUE_CONCEPTS, concepts, strict=True):
        payload = _ok(concept_name, payload, concept_errors)
        latest = _latest_annual(payload) if isinstance(payload, dict) else None
        if latest and (financials is None or latest["end"] > financials["latest"]["end"]):
            financials = {"concept": concept_name, "latest": latest}
    if financials is None and company is not None:  # neither tag had a full-year fact
        errors["edgar_revenue"] = "; ".join(concept_errors.values()) or "No full-year revenue fact"

    return {
        "company": company,
        "financials": financials,
        "federal_contracts": (contracts or {}).get("results", []) if isinstance(contracts, dict) else [],
        "source_count": sum(x is not None for x in (company, financials, contracts)),
        "errors": errors,
    }


async def politician_profile(last_name: str, first_name: str = "") -> dict:
    """Combined politician profile from House disclosures + FEC (searched by name)."""
    name = f"{first_name} {last_name}".strip()
    trades, fec_data = await asyncio.gather(
        house_fd.search_members(last_name=last_name),
        fec.candidates(name=name, per_page=100),
    )

    errors: dict[str, str] = {}
    trades = _ok("house_disclosures", trades, errors)
    fec_data = _ok("fec", fec_data, errors)

    # FEC's name search is fuzzy (full-text); keep candidates whose name has the
    # last name (and first name, when given).
    matched_candidates: list[dict] = []
    if isinstance(fec_data, dict):
        target, first_target = last_name.upper(), first_name.upper()
        for c in fec_data.get("results", []):
            cand_name = (c.get("name") or "").upper()
            if target in cand_name and (not first_target or first_target in cand_name):
                matched_candidates.append(c)

    return {
        "name": name or last_name,
        "house_trades": trades or [],
        "campaign_finance": matched_candidates,
        "errors": errors,
    }
