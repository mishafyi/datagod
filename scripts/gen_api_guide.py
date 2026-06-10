#!/usr/bin/env python3
"""Generate the agent-facing API guide: docs/API_GUIDE.md + docs/endpoints.csv.

Run from the project root after route changes:

    .venv/bin/python -m scripts.gen_api_guide

API_GUIDE.md answers "which endpoint for which information" (a routing map plus a
one-line description per endpoint). endpoints.csv is the same endpoint list for
programmatic / grep / embedding use. The live /docs (and /openapi.json for full
parameters) remains the source of truth.
"""

import csv
from pathlib import Path

from app.main import app

HEADER = """\
# DataGod — API Guide

Pick the right endpoint for the information you need.

- **Base URL:** `https://datagod.example.com`
- **Auth:** every call needs the header `X-API-Key: <your-key>` — only `GET /health` is public.
- **Response:** read the payload from the `data` field of the `{meta, data, error}` envelope.
- **Full parameters & schemas:** `GET /openapi.json` (HTTP Basic: user `datagod`, password = your key) or the Swagger UI at `/docs`. A flat machine-readable list is in `docs/endpoints.csv`.
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

_HTTP_METHODS = ("get", "post", "put", "delete", "patch")


def _grouped() -> tuple[list[str], dict[str, str], dict[str, list[tuple[str, str, str]]]]:
    schema = app.openapi()
    order = [tag["name"] for tag in schema.get("tags", [])]
    descriptions = {tag["name"]: tag.get("description", "") for tag in schema.get("tags", [])}
    grouped: dict[str, list[tuple[str, str, str]]] = {}
    for path, operations in schema["paths"].items():
        for method, operation in operations.items():
            if method not in _HTTP_METHODS:
                continue
            tag = (operation.get("tags") or ["(untagged)"])[0]
            grouped.setdefault(tag, []).append((method.upper(), path, operation.get("summary", "")))
    return order, descriptions, grouped


def render_md() -> str:
    order, descriptions, grouped = _grouped()
    out = [HEADER, "", QUICK_INDEX, "", "## All endpoints by source", ""]
    for tag in order:
        rows = grouped.get(tag)
        if not rows:
            continue
        out.append(f"### {tag}")
        if descriptions.get(tag):
            out += ["", f"_{descriptions[tag]}_"]
        out.append("")
        for method, path, summary in sorted(rows, key=lambda row: row[1]):
            out.append(f"- `{method} {path}` — {summary}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def write_csv(path: Path) -> int:
    order, _descriptions, grouped = _grouped()
    count = 0
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["source", "method", "path", "summary"])
        for tag in order:
            for method, route, summary in sorted(grouped.get(tag, []), key=lambda row: row[1]):
                writer.writerow([tag, method, route, summary])
                count += 1
    return count


def main() -> None:
    docs = Path(__file__).parent.parent / "docs"
    (docs / "API_GUIDE.md").write_text(render_md())
    rows = write_csv(docs / "endpoints.csv")
    print(f"wrote docs/API_GUIDE.md and docs/endpoints.csv ({rows} endpoints)")


if __name__ == "__main__":
    main()
