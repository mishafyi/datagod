#!/usr/bin/env python3
"""Generate the agent-facing API guide: docs/API_GUIDE.md + docs/endpoints.csv.

Run from the project root after route changes:

    .venv/bin/python -m scripts.gen_api_guide

The guide answers "which endpoint for which information": a routing map, plus a
keyword-rich description and the parameters for every endpoint, so an agent can
both find AND call an endpoint without a second lookup. Parameters come from the
live OpenAPI schema; the keyword descriptions are curated in DESCRIPTIONS below
(fall back to the OpenAPI summary if missing). endpoints.csv is the same data,
flat, for grep/tooling. /openapi.json (Basic auth) remains the source of truth
for full response schemas.
"""

import csv
from pathlib import Path

from app.main import app

HEADER = """\
# DataGod — API Guide

Find the right endpoint for the information you need, then call it.

- **Base URL:** `https://datagod.example.com`
- **Auth:** every call needs the header `X-API-Key: <your-key>` — only `GET /health` is public.
- **Response:** read the payload from the `data` field of the `{meta, data, error}` envelope.
- **Each entry below lists its parameters.** For full response schemas use `GET /openapi.json` (HTTP Basic: user `datagod`, password = your key) or the Swagger UI at `/docs`. `docs/endpoints.csv` has the same list, flat.
- **Limits:** a valid key has **no per-key usage or rate limit** on DataGod itself. Caveats: each endpoint's `limit` query param caps results **per call** (paginate for more), SEC EDGAR is throttled to ~10 req/sec (SEC's rule, shared across callers), and each upstream enforces its own rate limits (the DEMO_KEY-backed FEC / Congress / EIA / Smithsonian are low) — DataGod passes those through.
"""

EXAMPLE = """\
## Example call

```bash
curl -H "X-API-Key: $DATAGOD_API_KEY" "https://datagod.example.com/fred/GDP?limit=2"
```

Returns the standard envelope — read the payload from `data`:

```json
{
  "meta": { "source": "fred", "endpoint": "/fred/GDP", "timestamp": "2026-06-10T12:00:00Z", "status": "success" },
  "data": {
    "units": "lin",
    "observations": [
      { "date": "2026-01-01", "value": "31819.464" },
      { "date": "2025-10-01", "value": "31422.526" }
    ]
  },
  "error": null
}
```

No key (or a wrong one) returns `401`; an upstream failure returns `meta.status: "error"` with the message in `error` (HTTP 4xx passed through, 5xx/timeout → 502).
"""

QUICK_INDEX = """\
## Which source for which information

| You need... | Source | Start with |
|-------------|--------|------------|
| Economic indicators: GDP, inflation/CPI, interest rates, money supply | FRED | `GET /fred/{series_id}` (e.g. `GDP`, `CPIAUCSL`, `FEDFUNDS`) |
| Jobs, unemployment, wages, detailed CPI/PPI | BLS | `GET /bls/{series_id}` |
| US national debt, Treasury yields, exchange rates | Treasury | `GET /treasury/debt` |
| SEC filings & XBRL financials for a company | EDGAR | `GET /edgar/financials/{cik}` |
| One financial metric across ALL public companies | EDGAR | `GET /edgar/frames/{concept}` |
| Stock quote / price | Nasdaq | `GET /nasdaq/quote/{ticker}` |
| Deep stock fundamentals, options, holders, news | yfinance | `GET /yfinance/info/{ticker}` |
| Federal contracts, grants, who got paid | USAspending | `GET /usaspending/search` |
| Population, income, demographics (ACS) | Census | `GET /census/acs` |
| Campaign finance: candidates, contributions, totals | FEC | `GET /fec/candidates` |
| Legislation: bills, members, votes | Congress | `GET /congress/bills` |
| Drug adverse events, drug & food recalls | FDA | `GET /fda/drug-recalls` |
| Clinical trials | Clinical Trials | `GET /clinical-trials` |
| Energy prices, electricity, gasoline | EIA | `GET /eia/gas-prices` |
| Disaster declarations, FEMA grants, flood claims | FEMA | `GET /fema/disasters` |
| Federal rules, notices, executive orders | Federal Register | `GET /federal-register` |
| US House members' stock trades | House Disclosures | `GET /house-disclosures/members` |
| Federal judges' financial disclosures | JEFS | `GET /jefs/search` (needs session) |
| US National Archives catalog records | NARA | `GET /nara/search` |
| Declassified national-security documents | NSArchive / Wilson Center | `GET /nsarchive/search`, `GET /wilson/documents` |
| Museum / library / archive objects | Smithsonian | `GET /smithsonian/search` |
| One company or politician across several sources | Cross-Reference | `GET /cross-reference/company/{name}` |
"""

# Curated keyword-rich descriptions, keyed by route path. These power agent
# routing — pack in synonyms and the concrete things each endpoint returns.
DESCRIPTIONS = {
    "/": "Service index: lists every data source and its endpoint groups. Use to discover what is available.",
    "/health": "Health / liveness check. Public, no key. Use for uptime monitoring and readiness probes.",
    "/fred/{series_id}": "One US macroeconomic time series by FRED series ID. Use for: GDP, inflation, consumer prices/CPI (CPIAUCSL), unemployment rate (UNRATE), Fed funds / interest rates (FEDFUNDS), Treasury yields (DGS10), money supply (M2), S&P 500 (SP500), industrial production, recession indicators — any US macro indicator.",
    "/fred": "Keyword search across FRED's 800K-series catalog; returns series IDs to fetch above. Use when you don't know the exact series ID.",
    "/edgar/company/{cik}": "SEC company profile and filing history (10-K, 10-Q, 8-K, S-1, etc.) by CIK or ticker (e.g. AAPL). Use for: company metadata, recent filings, fiscal year end, SIC industry, exchange, addresses, former names.",
    "/edgar/financials/{cik}": "All XBRL financial facts for a company across years. Use for: revenue, net income, assets, liabilities, cash, equity, EPS, R&D spend — the full financial-statement dataset.",
    "/edgar/concept/{cik}/{concept}": "History of one XBRL concept for one company (e.g. Revenues, NetIncomeLoss, Assets, CashAndCashEquivalents). Use to track a single financial metric over time.",
    "/edgar/frames/{concept}": "One financial concept across ALL public companies for a period — cross-company comparison in a single call. Use to rank or compare revenue / assets / net income across thousands of filers.",
    "/edgar/search": "Full-text search inside SEC filing documents. Use for: which companies mention a topic (AI, climate risk, layoffs, a competitor, a product) in their filings; filter by form type.",
    "/nasdaq/quote/{ticker}": "Stock quote summary: market cap, sector, industry, P/E, dividend yield, 52-week high/low. Quick snapshot of a listed company.",
    "/nasdaq/price/{ticker}": "Current price, bid/ask, day volume, and percent change for a ticker.",
    "/nasdaq/history/{ticker}": "Daily OHLCV price history (open, high, low, close, volume) between two dates.",
    "/nasdaq/dividends/{ticker}": "Dividend payment history (ex-date and amount) for a ticker.",
    "/yfinance/info/{ticker}": "Deepest single-call company profile (~140 fields): market cap, P/E, EPS, beta, profit margins, ROE, debt, free cash flow, analyst price targets, sector, employees, business summary.",
    "/yfinance/history/{ticker}": "OHLCV price history with flexible period (1d..max) and interval (1m..1mo). Use for charts, returns, volatility.",
    "/yfinance/news/{ticker}": "Recent news headlines and article links tied to a ticker.",
    "/yfinance/recommendations/{ticker}": "Analyst recommendation history (buy / hold / sell ratings over time).",
    "/yfinance/holders/{ticker}": "Ownership: major holders, institutional holders, and mutual-fund holders.",
    "/yfinance/financials/{ticker}": "Income statement, balance sheet, and cash-flow statement (annual + quarterly).",
    "/yfinance/dividends/{ticker}": "Dividend payment history (amounts and dates).",
    "/yfinance/options/{ticker}": "Options chain: expiry dates, calls and puts, strikes, implied volatility, open interest.",
    "/usaspending/agencies": "List of federal agencies (names and IDs) for filtering spending queries.",
    "/usaspending/search": "Search federal awards (contracts and grants) by keyword. Use for: who received federal money, contractors/recipients, award amounts, defense or agency spending.",
    "/usaspending/by-agency": "Federal spending totals grouped by agency for a fiscal year / quarter.",
    "/census/population": "Population by US state.",
    "/census/income": "Median household income by US state.",
    "/census/acs": "Raw American Community Survey query — any ACS variables and geography (state / county / tract). Use for: demographics, race, age, sex, education, income, poverty, housing, commute — any ACS table by variable code.",
    "/bls/{series_id}": "US labor statistics series by ID. Use for: unemployment rate, nonfarm payroll employment, CPI inflation, PPI, average hourly earnings. Shortcut IDs: unemployment, cpi, nonfarm_employment, ppi, hourly_earnings.",
    "/treasury/debt": "US national / public debt (debt to the penny): total outstanding, debt held by the public, intragovernmental holdings, by date.",
    "/treasury/rates": "Average interest rates on outstanding US Treasury securities.",
    "/treasury/exchange": "US Treasury reporting exchange rates (foreign-currency conversion rates used by the government).",
    "/fec/candidates": "Search federal candidates (President, Senate, House) by office and state. Campaign finance.",
    "/fec/contributions": "Campaign contributions — itemized donations by or for a candidate or donor name.",
    "/fec/totals": "Candidate financial totals (money raised / receipts), ranked, by office and election year.",
    "/congress/bills": "Recent bills introduced in Congress. Legislation tracking.",
    "/congress/bill/{congress_num}/{bill_type}/{number}": "Full detail for one bill: sponsors, actions, latest status, summary.",
    "/congress/members": "Members of Congress (representatives and senators), with party and state.",
    "/congress/votes": "Roll-call votes by chamber and session.",
    "/fda/drug-events": "Drug adverse-event reports (side effects, reactions) from openFDA / FAERS.",
    "/fda/drug-recalls": "Drug recall enforcement reports — recalled medications, reasons, recall class.",
    "/fda/food-recalls": "Food recall enforcement reports — recalled foods, contamination, allergens, reasons.",
    "/clinical-trials": "Search ClinicalTrials.gov by condition, intervention, and status (recruiting, completed). Medical and drug trials.",
    "/clinical-trials/{nct_id}": "Full record for one clinical trial by its NCT ID.",
    "/eia": "List the EIA energy datasets available to query.",
    "/eia/gas-prices": "Gasoline and fuel prices over time.",
    "/eia/electricity": "Electricity data: generation, retail sales, and prices.",
    "/eia/{route}": "Generic EIA dataset query by route path — any energy series (crude oil, natural gas, coal, renewables, CO2 emissions, consumption).",
    "/fema/disasters": "Federal disaster declarations (hurricanes, floods, wildfires, severe storms) by date and state.",
    "/fema/grants": "FEMA grant and assistance awards.",
    "/fema/flood-claims": "NFIP (National Flood Insurance Program) flood insurance claims data.",
    "/federal-register": "Search the Federal Register: proposed and final rules, notices, executive orders, and presidential documents; filter by type and agency.",
    "/federal-register/{doc_number}": "One Federal Register document by its document number.",
    "/jefs/register": "Open a JEFS session for judicial financial disclosures — drives a Playwright browser through registration + reCAPTCHA. Requires a real name, occupation, and address.",
    "/jefs/facets": "Available JEFS filters (years, courts, positions, report types). Requires an active session.",
    "/jefs/search": "Search federal judges' financial disclosure reports. Requires an active session (call /jefs/register first).",
    "/jefs/reset": "Clear the JEFS session; you must re-register before the next call.",
    "/house-disclosures/members": "US House members' financial disclosures — congressional stock trades and holdings.",
    "/house-disclosures/candidates": "US House candidates' financial disclosures.",
    "/nara/search": "Search the US National Archives Catalog — historical government records across all record groups and the 14 presidential libraries.",
    "/nara/record/{na_id}": "One National Archives catalog record by its National Archives Identifier (NAID).",
    "/nsarchive/search": "Search the National Security Archive (GWU NGO) Virtual Reading Room — declassified documents on foreign policy, intelligence, and defense.",
    "/nsarchive/document/{doc_id}": "One declassified Virtual Reading Room document by its id-slug.",
    "/smithsonian/search": "Search Smithsonian Open Access — 11M+ museum, library, and archive objects (art, history, science specimens, photographs).",
    "/smithsonian/object/{object_id}": "Full metadata record for one Smithsonian object by EDAN id.",
    "/smithsonian/category/{category}/search": "Search within a Smithsonian category: art_design, history_culture, or science_technology.",
    "/smithsonian/terms/{category}": "Controlled-vocabulary terms for a facet: culture, topic, place, object_type, data_source, date, or name.",
    "/smithsonian/stats": "Smithsonian Open Access dataset statistics (counts by unit, type, etc.).",
    "/wilson/documents": "Full-text search the Wilson Center Digital Archive (local mirror) — 16,756 declassified Cold War and international-history documents.",
    "/wilson/document/{slug}": "One Wilson Center document by slug: title, source, subjects, download availability.",
    "/cross-reference/company/{name}": "Aggregate a company across EDGAR + USAspending + FEC in one call: SEC filings + federal contracts + political contributions.",
    "/cross-reference/politician/{last_name}": "Aggregate a politician across House disclosures + FEC: stock trades + campaign finance.",
    "/admin/clear-cache": "Clear the in-memory cache (operational endpoint).",
}

_HTTP_METHODS = ("get", "post", "put", "delete", "patch")


def _type(schema: dict) -> str:
    if not schema:
        return ""
    if "type" in schema:
        if schema["type"] == "array":
            item = (schema.get("items") or {}).get("type", "")
            return f"array[{item}]" if item else "array"
        return schema["type"]
    if "anyOf" in schema:
        types = [s.get("type") for s in schema["anyOf"] if s.get("type") and s.get("type") != "null"]
        return "|".join(dict.fromkeys(types))
    return ""


def _params(operation: dict) -> list[tuple[str, str]]:
    """Return [(name, "in, type, required|default X, max N"), ...]."""
    out: list[tuple[str, str]] = []
    for param in operation.get("parameters", []):
        schema = param.get("schema", {}) or {}
        bits = [param.get("in", "")]
        ptype = _type(schema)
        if ptype:
            bits.append(ptype)
        if param.get("required"):
            bits.append("required")
        elif schema.get("default", "") != "":
            bits.append(f"default {schema['default']}")
        if schema.get("maximum") is not None:
            bits.append(f"max {schema['maximum']}")
        out.append((param["name"], ", ".join(str(b) for b in bits)))
    return out


def _grouped() -> tuple[list[str], dict[str, str], dict[str, list[tuple[str, str, dict]]]]:
    schema = app.openapi()
    order = [tag["name"] for tag in schema.get("tags", [])]
    descriptions = {tag["name"]: tag.get("description", "") for tag in schema.get("tags", [])}
    grouped: dict[str, list[tuple[str, str, dict]]] = {}
    for path, operations in schema["paths"].items():
        for method, operation in operations.items():
            if method not in _HTTP_METHODS:
                continue
            tag = (operation.get("tags") or ["(untagged)"])[0]
            grouped.setdefault(tag, []).append((method.upper(), path, operation))
    return order, descriptions, grouped


def render_md() -> tuple[str, list[str]]:
    order, descriptions, grouped = _grouped()
    missing: list[str] = []
    out = [HEADER, "", EXAMPLE, "", QUICK_INDEX, "", "## All endpoints by source", ""]
    for tag in order:
        rows = grouped.get(tag)
        if not rows:
            continue
        out.append(f"### {tag}")
        if descriptions.get(tag):
            out += ["", f"_{descriptions[tag]}_"]
        out.append("")
        for method, path, op in sorted(rows, key=lambda row: row[1]):
            desc = DESCRIPTIONS.get(path)
            if desc is None:
                missing.append(path)
                desc = op.get("summary", "")
            out.append(f"- **`{method} {path}`** — {desc}")
            params = _params(op)
            if params:
                out.append("  - _params:_ " + " · ".join(f"`{n}` ({m})" for n, m in params))
            else:
                out.append("  - _params:_ none")
        out.append("")
    return "\n".join(out).rstrip() + "\n", missing


def write_csv(path: Path) -> int:
    order, _descriptions, grouped = _grouped()
    count = 0
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["source", "method", "path", "description", "params"])
        for tag in order:
            for method, route, op in sorted(grouped.get(tag, []), key=lambda row: row[1]):
                desc = DESCRIPTIONS.get(route, op.get("summary", ""))
                params = "; ".join(f"{n} ({m})" for n, m in _params(op))
                writer.writerow([tag, method, route, desc, params])
                count += 1
    return count


def main() -> None:
    docs = Path(__file__).parent.parent / "docs"
    markdown, missing = render_md()
    (docs / "API_GUIDE.md").write_text(markdown)
    rows = write_csv(docs / "endpoints.csv")
    print(f"wrote docs/API_GUIDE.md and docs/endpoints.csv ({rows} endpoints)")
    if missing:
        print(f"WARNING: {len(missing)} routes missing curated descriptions: {missing}")


if __name__ == "__main__":
    main()
