#!/usr/bin/env python3
"""Generate per-source skill docs (docs/<SOURCE>.md) — splits the bundled GOV_APIS.md
into one file per source. Run from the project root:

    .venv/bin/python -m scripts.gen_source_docs

Each doc = YAML frontmatter (name, description, keywords, routes) + endpoints with
params from the LIVE OpenAPI schema + a curated Quirks section (the only
hand-maintained part — it bakes in the audit corrections). The interactive /docs
remains the source of truth; deep upstream quirks are curated below.
"""

from pathlib import Path

from scripts.gen_api_guide import (
    DESCRIPTIONS,
    SOURCE_DESC,
    SOURCE_KEYWORDS,
    _grouped,
    _params,
)

# The 12 bundled-gov sources to split out, and their output filename.
SOURCE_FILE = {
    "FRED": "FRED.md",
    "BLS": "BLS.md",
    "Census": "CENSUS.md",
    "Treasury": "TREASURY.md",
    "FEC": "FEC.md",
    "Congress": "CONGRESS.md",
    "FDA": "FDA.md",
    "Clinical Trials": "CLINICAL_TRIALS.md",
    "EIA": "EIA.md",
    "FEMA": "FEMA.md",
    "Federal Register": "FEDERAL_REGISTER.md",
    "USAspending": "USASPENDING.md",
}

# Curated upstream quirks per source — verified against the client code 2026-06-11.
# This is where the audit corrections live (BLS v1, Census key, FEMA grants, Congress votes).
QUIRKS = {
    "FRED": "- Requires a real `FRED_API_KEY` (no DEMO_KEY fallback).\n- Response is the FRED observations envelope; `value` fields are strings.\n- Handy series IDs: `GDP`, `UNRATE`, `CPIAUCSL`, `FEDFUNDS`, `DGS10`, `M2SL`, `SP500`.",
    "BLS": "- Uses the BLS public API **v1** (`api.bls.gov/publicAPI/v1/timeseries/data`) — not v2. `BLS_API_KEY` is optional (raises limits).\n- The client accepts shortcut series IDs: `unemployment`, `cpi`, `nonfarm_employment`, `ppi`, `hourly_earnings`.\n- Data is under `Results.series[].data`.",
    "Census": "- **Requires a valid `CENSUS_API_KEY`** (free signup: https://api.census.gov/data/key_signup.html). A missing or invalid key 302-redirects to an HTML `invalid_key.html` page → JSON parse error → 502.\n- The client sends `cfg.CENSUS_API_KEY` as `key=`. Uses ACS 1-year (`acs/acs1`).\n- Response is a 2-D array: a header row followed by data rows.",
    "Treasury": "- No key (Treasury Fiscal Data API).\n- Datasets: debt → `debt_to_penny` (v2), rates → `avg_interest_rates` (v2), exchange → `rates_of_exchange` (v1).\n- Newest-first (`sort=-record_date`); paginate via `page[size]`.",
    "FEC": "- `FEC_API_KEY` with a `DEMO_KEY` fallback (low limits).\n- Base `api.open.fec.gov/v1`: `candidates/`, `schedules/schedule_a/` (contributions), `candidates/totals/`.\n- Results under `results`; paginated.",
    "Congress": "- `CONGRESS_API_KEY` with a `DEMO_KEY` fallback.\n- Base `api.congress.gov/v3`. **The votes endpoint is `house-vote/{congress}` (House only).**",
    "FDA": "- No key (openFDA). Base `api.fda.gov`.\n- Datasets: `drug/event.json` (adverse events), `drug/enforcement.json` (drug recalls), `food/enforcement.json` (food recalls).\n- `search=` uses Lucene-style queries; results under `results`.",
    "Clinical Trials": "- No key. Base `clinicaltrials.gov/api/v2`: `studies` and `studies/{nct}`.\n- Filters: `query.cond` (condition), `query.intr` (intervention), `filter.overallStatus`.",
    "EIA": "- `EIA_API_KEY` with a `DEMO_KEY` fallback. Base `api.eia.gov/v2`.\n- `/` lists datasets; gas → `petroleum/pri/gnd`; electricity → `electricity/retail-sales`; generic `{route}/data/` takes `frequency`, `data[0]`, `sort[0][...]`, `length`.",
    "FEMA": "- No key (OpenFEMA).\n- Datasets: disasters → `DisasterDeclarationsSummaries`, grants → `HazardMitigationGrantProgramDisasterSummaries`, flood-claims → `FimaNfipClaims`.",
    "Federal Register": "- No key. Base `federalregister.gov/api/v1`: `documents.json`, `documents/{n}.json`.\n- Filters: `conditions[type][]` (RULE | PRORULE | NOTICE | PRESDOCU), `conditions[agencies][]`, `conditions[term]`, `order=newest`.",
    "USAspending": "- No key. Base `api.usaspending.gov/api/v2`.\n- `agencies` → `references/toptier_agencies/`; `search` → POST `search/spending_by_award/`; `by-agency` → POST `spending/`.",
}


def render(tag: str, rows: list[tuple[str, str, dict]]) -> str:
    desc = SOURCE_DESC.get(tag, "")
    keywords = SOURCE_KEYWORDS.get(tag, "")
    paths = sorted(path for _m, path, _op in rows)
    name = tag.lower().replace(" ", "-")
    lines = [
        "---",
        f"name: {name}",
        f'description: "{desc}"',
        f'keywords: "{keywords}"',
        f'routes: "{", ".join(paths)}"',
        "---",
        "",
        f"# {tag}",
        "",
        desc,
        "",
        "## Endpoints",
        "",
    ]
    for method, path, op in sorted(rows, key=lambda row: row[1]):
        lines.append(f"### `{method} {path}`")
        lines.append("")
        lines.append(DESCRIPTIONS.get(path, op.get("summary", "")))
        params = _params(op)
        if params:
            lines.append("")
            lines.append("**Params:** " + " · ".join(f"`{n}` ({m})" for n, m in params))
        lines.append("")
    if QUIRKS.get(tag):
        lines += ["## Quirks & notes", "", QUIRKS[tag], ""]
    lines.append(
        "> Endpoint params are generated from the live OpenAPI schema "
        "(`/openapi.json`); the Quirks section is curated. "
        "Regenerate with `python -m scripts.gen_source_docs`."
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    docs = Path(__file__).parent.parent / "docs"
    _order, _tag_desc, grouped = _grouped()
    written: list[str] = []
    for tag, filename in SOURCE_FILE.items():
        rows = grouped.get(tag)
        if not rows:
            print(f"WARNING: no routes found for source '{tag}'")
            continue
        (docs / filename).write_text(render(tag, rows))
        written.append(filename)
    print(f"wrote {len(written)} per-source docs: {', '.join(written)}")


if __name__ == "__main__":
    main()
