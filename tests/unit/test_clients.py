"""Regression tests for client fixes — every upstream is faked (no network)."""

import json
import sqlite3
from datetime import date

import httpx2
import pytest

from app.clients import (
    bls, cia, congress_gov, cross_reference, edgar, fas, fema, frus, house_fd, nasdaq, scholar,
    wilson,
)
from app.config import cfg

pytestmark = pytest.mark.anyio

# Trimmed from a live ViewMemberSearchResult response (2026-11-04): the header row
# has <th> cells only, names carry HTML entities.
HOUSE_HTML = """<table><thead><tr role="row">
    <th scope="col">Name</th><th scope="col">Office</th>
    <th scope="col">Filing Year</th><th scope="col">Filing</th></tr></thead><tbody>
<tr role="row">
    <td data-label="Name" class="memberName">
        <a href="public_disc/financial-pdfs/2017/10025019.pdf" target="_blank">O&#x27;Halleran, Hon.. Tom </a>
    </td>
    <td data-label="Office">AZ01</td><td data-label="Filing Year">2017</td>
    <td data-label="Filing">FD Amendment</td></tr>
<tr role="row">
    <td data-label="Name" class="memberName"><a href="public_disc/ptr-pdfs/2024/20024542.pdf"
        target="_blank">Smith &amp; Jones, Hon.. A</a></td>
    <td data-label="Office">CA11</td><td data-label="Filing Year">2024</td>
    <td data-label="Filing"></td></tr>
</tbody></table>"""


# ── house_fd ────────────────────────────────────────────────────────────

def test_house_parser_skips_header_and_decodes_entities():
    rows = house_fd._parse_html_table(HOUSE_HTML)
    assert rows == [
        {"name": "O'Halleran, Hon.. Tom", "office": "AZ01", "filing_year": "2017",
         "filing": "FD Amendment",
         "pdf_url": "https://disclosures-clerk.house.gov/public_disc/financial-pdfs/2017/10025019.pdf"},
        {"name": "Smith & Jones, Hon.. A", "office": "CA11", "filing_year": "2024", "filing": None,
         "pdf_url": "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2024/20024542.pdf"},
    ]


# ── nasdaq: failures arrive as HTTP 200 + status.rCode ───────────────────

def _nasdaq_body(code: int, message: str | None = None) -> dict:
    return {"data": None if message else {"ok": 1}, "message": None,
            "status": {"rCode": code, "developerMessage": None,
                       "bCodeMessage": [{"code": 1001, "errorMessage": message}] if message else None}}


async def test_nasdaq_in_body_failure_becomes_error_dict(upstream):
    upstream.add("https://api.nasdaq.com/", httpx2.Response(200, json=_nasdaq_body(400, "Symbol not exists.")))
    err = await nasdaq.summary("NOTATICKER")
    assert err == {"error": True, "source": "nasdaq", "upstream_status": 400,
                   "message": "Symbol not exists."}


async def test_nasdaq_success_passes_through(upstream):
    upstream.add("https://api.nasdaq.com/", httpx2.Response(200, json=_nasdaq_body(200)))
    assert (await nasdaq.info("AAPL"))["data"] == {"ok": 1}


@pytest.mark.parametrize(("given", "sent"), [
    ("annual", "1"), ("A", "1"), ("1", "1"), ("quarterly", "2"), ("q", "2"), ("2", "2"),
])
async def test_nasdaq_financials_frequency_mapping(upstream, given, sent):
    upstream.add("https://api.nasdaq.com/", httpx2.Response(200, json=_nasdaq_body(200)))
    await nasdaq.financials("NVDA", given)
    assert upstream.requests[-1].url.params["frequency"] == sent


async def test_nasdaq_financials_rejects_unknown_frequency_locally(upstream):
    err = await nasdaq.financials("NVDA", "weekly")
    assert err["upstream_status"] == 400 and upstream.requests == []


async def test_nasdaq_ipo_calendar_sends_a_month(upstream):
    upstream.add("https://api.nasdaq.com/", httpx2.Response(200, json=_nasdaq_body(200)))
    await nasdaq.calendar_ipo("2026-06-15")
    assert upstream.requests[-1].url.params["date"] == "2026-06"


# ── bls ─────────────────────────────────────────────────────────────────

async def test_bls_uses_v1_without_key_and_v2_with_key(upstream, monkeypatch):
    upstream.add("https://api.bls.gov/", httpx2.Response(200, json={"status": "REQUEST_SUCCEEDED"}))
    monkeypatch.setattr(cfg, "BLS_API_KEY", "")
    await bls.series("cpi", 2024, 2025)
    assert "/publicAPI/v1/" in str(upstream.requests[-1].url)
    monkeypatch.setattr(cfg, "BLS_API_KEY", "k" * 32)
    await bls.series("cpi", 2024, 2025)
    assert "/publicAPI/v2/" in str(upstream.requests[-1].url)
    await bls.multiple(["cpi"], 2024, 2025)
    assert "/publicAPI/v2/" in str(upstream.requests[-1].url)


@pytest.mark.parametrize(("message", "status"), [
    ("Request could not be serviced, as the daily threshold for total number of requests ... reached.", 429),
    ("The key:bogus provided by the User is invalid.", 400),
])
async def test_bls_request_not_processed_is_an_error(upstream, message, status):
    upstream.add("https://api.bls.gov/", httpx2.Response(
        200, json={"status": "REQUEST_NOT_PROCESSED", "message": [message], "Results": {}}))
    err = await bls.series("cpi", 2024, 2025)
    assert err["error"] is True and err["upstream_status"] == status


# ── fema ────────────────────────────────────────────────────────────────

async def test_fema_dataset_versions_and_odata_quoting(upstream):
    upstream.add("https://www.fema.gov/", httpx2.Response(200, json={}))
    await fema.flood_claims(1)
    await fema.grants(1)
    await fema.disasters(1, state="C'A")
    urls = [str(r.url) for r in upstream.requests]
    assert "/api/open/v3/NfipClaims" in urls[0]
    assert "/api/open/v3/HazardMitigationGrantProgramDisasterSummaries" in urls[1]
    assert upstream.requests[2].url.params["$filter"] == "state eq 'C''A'"


# ── congress ────────────────────────────────────────────────────────────

@pytest.mark.parametrize(("day", "congress"), [
    ("2023-01-02", 117), ("2023-01-03", 118), ("2025-01-02", 118),
    ("2025-01-03", 119), ("2026-11-04", 119), ("2027-01-03", 120),
])
def test_current_congress(day, congress):
    assert congress_gov.current_congress(date.fromisoformat(day)) == congress


async def test_votes_default_to_current_congress(upstream):
    upstream.add("https://api.congress.gov/", httpx2.Response(200, json={}))
    await congress_gov.votes()
    assert upstream.requests[-1].url.path == f"/v3/house-vote/{congress_gov.current_congress()}"


# ── imf: the IMF's own SDMX API (DBnomics stopped updating in 2025-09) ──

async def test_imf_series_asks_api_imf_org_for_json(upstream):
    from app.clients import imf

    upstream.add("https://api.imf.org/", httpx2.Response(200, json={"dataSets": [], "structure": {}}))
    await imf.series("WEO", "USA+CHN.NGDP_RPCH.A", "2024", "2027")
    request = upstream.requests[-1]
    assert request.url.path == "/external/sdmx/2.1/data/WEO/USA+CHN.NGDP_RPCH.A"
    assert dict(request.url.params) == {"startPeriod": "2024", "endPeriod": "2027"}
    assert request.headers["accept"] == "application/json"  # sdmx+json media types get XML back


async def test_imf_structure_includes_codelists(upstream):
    from app.clients import imf

    upstream.add("https://api.imf.org/", httpx2.Response(200, json={"data": {}}))
    await imf.structure("WEO")
    request = upstream.requests[-1]
    assert request.url.path == "/external/sdmx/2.1/dataflow/all/WEO/latest"
    assert request.url.params["references"] == "descendants"


async def test_ucdp_defaults_to_latest_ged_release(upstream):
    from app.clients import ucdp

    upstream.add("https://ucdpapi.pcr.uu.se/", httpx2.Response(200, json={"Result": []}))
    await ucdp.gedevents("369")
    assert upstream.requests[-1].url.path == "/api/gedevents/26.1"


# ── yfinance: a quote without a name means Yahoo returned nothing ───────

@pytest.mark.parametrize(("info", "ok"), [
    ({"shortName": "Apple Inc.", "symbol": "AAPL"}, True),
    ({"longName": "S&P 500"}, True),
    ({"trailingPegRatio": None}, False),  # throttled session / unknown symbol
    ({}, False),
])
async def test_yfinance_info_requires_a_quote(monkeypatch, info, ok):
    from app.clients import yfin

    class FakeTicker:
        def __init__(self, symbol):
            self.info = info

    monkeypatch.setattr(yfin.yf, "Ticker", FakeTicker)
    result = await yfin.info("AAPL")
    if ok:
        assert result == info
    else:
        assert result["error"] is True and "throttling" in result["message"]


# ── scholar: the query is percent-encoded ───────────────────────────────

@pytest.mark.parametrize("keyword", ["R&D spending", "C++ templates", "attention #1", '"exact phrase"'])
def test_scholar_url_round_trips_the_keyword(keyword):
    url = httpx2.URL(scholar._build_url(keyword, 10, 2020, 2024))
    assert url.params["q"] == keyword
    assert url.params["start"] == "10" and url.params["as_ylo"] == "2020" and url.params["as_yhi"] == "2024"
    assert url.params["as_sdt"] == "0,5" and url.fragment == ""


# ── edgar ───────────────────────────────────────────────────────────────

TICKERS = {"0": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"},
           "1": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
           "2": {"cik_str": 1418121, "ticker": "APLE", "title": "Apple Hospitality REIT, Inc."},
           "3": {"cik_str": 6951, "ticker": "AMAT", "title": "APPLIED MATERIALS INC /DE"}}


@pytest.fixture
def fresh_ticker_map(monkeypatch):
    monkeypatch.setattr(edgar, "_ticker_map", None)
    monkeypatch.setattr(edgar, "_titles", [])


@pytest.mark.parametrize(("query", "cik"), [
    ("320193", "0000320193"), ("aapl", "0000320193"), ("apple", "0000320193"),
    ("Apple Inc", "0000320193"), ("apple hospitality", "0001418121"), ("nvidia", "0001045810"),
    ("appl", None), ("zz-no-such-co", None),
])
async def test_resolve_company(upstream, fresh_ticker_map, query, cik):
    upstream.add("https://www.sec.gov/files/company_tickers.json", httpx2.Response(200, json=TICKERS))
    assert await edgar.resolve_company(query) == cik


async def test_ticker_map_failure_keeps_secs_status(upstream, fresh_ticker_map):
    upstream.add("https://www.sec.gov/files/", httpx2.Response(403, text="Undeclared Automated Tool"))
    err = await edgar.company("AAPL")
    assert err["error"] is True and err["upstream_status"] == 403  # was 0 → 502 "Expecting value"


# ── cross_reference ─────────────────────────────────────────────────────

def test_latest_annual_prefers_newest_full_year_over_list_order():
    concept = {"units": {"USD": [
        {"start": "2024-09-29", "end": "2025-09-27", "val": 416, "fp": "FY", "filed": "2025-10-31"},
        {"start": "2025-09-28", "end": "2026-09-26", "val": 478, "fp": "FY", "filed": "2026-11-03"},
        {"start": "2026-06-28", "end": "2026-09-26", "val": 102, "fp": "FY", "filed": "2026-11-03"},  # Q4
        {"end": "2026-09-26", "val": 1, "fp": "FY"},  # instant — no start
    ]}}
    assert cross_reference._latest_annual(concept)["val"] == 478


async def test_company_profile_counts_only_successes(upstream, fresh_ticker_map):
    upstream.add("https://www.sec.gov/files/company_tickers.json", httpx2.Response(200, json=TICKERS))
    upstream.add("https://data.sec.gov/submissions/", httpx2.Response(200, json={"name": "Apple Inc."}))
    upstream.add("https://data.sec.gov/api/xbrl/companyconcept/", httpx2.Response(404, text="NoSuchKey"))
    upstream.add("https://api.usaspending.gov/", httpx2.Response(200, json={"results": [{"Award ID": "X"}]}))
    profile = await cross_reference.company_profile("apple")
    assert profile["company"] == {"name": "Apple Inc."}
    assert profile["financials"] is None
    assert profile["federal_contracts"] == [{"Award ID": "X"}]
    assert profile["source_count"] == 2
    assert set(profile["errors"]) == {"edgar_revenue"}


async def test_politician_profile_searches_fec_by_name(upstream):
    upstream.add("https://disclosures-clerk.house.gov/", httpx2.Response(200, text=HOUSE_HTML))
    upstream.add("https://api.open.fec.gov/", httpx2.Response(200, json={"results": [
        {"name": "PELOSI, NANCY"}, {"name": "PELOSI, PAUL"}, {"name": "SMITH, JOHN"}]}))
    profile = await cross_reference.politician_profile("pelosi", "nancy")
    fec_request = next(r for r in upstream.requests if r.url.host == "api.open.fec.gov")
    assert fec_request.url.params["q"] == "nancy pelosi"
    assert profile["campaign_finance"] == [{"name": "PELOSI, NANCY"}]
    assert len(profile["house_trades"]) == 2 and profile["errors"] == {}


async def test_politician_profile_reports_failed_sources(upstream):
    upstream.add("https://disclosures-clerk.house.gov/", httpx2.Response(503, text="down"))
    upstream.add("https://api.open.fec.gov/", httpx2.Response(429, json={"error": "OVER_RATE_LIMIT"}))
    profile = await cross_reference.politician_profile("pelosi")
    assert profile["house_trades"] == [] and profile["campaign_finance"] == []
    assert set(profile["errors"]) == {"house_disclosures", "fec"}


# ── wilson: paging is clamped (SQLite reads LIMIT -1 as "no limit") ─────

def test_wilson_negative_page_size_is_clamped(tmp_path, monkeypatch):
    db_path = tmp_path / "wilson.db"
    db = sqlite3.connect(db_path)
    db.executescript("CREATE TABLE documents(slug, title, record_id, node_id, subjects,"
                     " download_available, info, names);"
                     "CREATE VIRTUAL TABLE documents_fts USING fts5(slug UNINDEXED, title, body);")
    db.executemany("INSERT INTO documents VALUES (?,?,?,?,?,?,?,?)",
                   [(f"s{i:03}", f"T{i:03}", i, i, "[]", 0, "{}", "[]") for i in range(150)])
    db.commit()
    db.close()
    monkeypatch.setattr(wilson, "DB_PATH", db_path)
    result = wilson._search("", 1, -1)
    assert len(result["list"]) == 1 and result["pagination"]["totalPages"] == 150
    assert len(wilson._search("", 0, 1000)["list"]) == 100


# ── scrapers survive odd markup instead of raising (→ 500) ──────────────

async def test_cia_document_tolerates_empty_label_and_valueless_href(monkeypatch):
    html = ('<h1>Doc</h1><div class="field"><div class="field-label"></div>'
            '<div class="field-item">x</div></div><a href>empty</a>'
            '<a href="/web/2024/https://www.cia.gov/readingroom/docs/X.pdf">pdf</a>')

    async def fake_capture(url, min_bytes=8000):
        return html, "https://web.archive.org/web/2024id_/" + url, None

    monkeypatch.setattr(cia, "fetch_capture", fake_capture)
    doc = await cia.document("x")
    assert doc["title"] == "Doc" and doc["pdf_url"] == "https://www.cia.gov/readingroom/docs/X.pdf"


async def test_fas_page_with_empty_body(monkeypatch):
    async def fake_get(path):
        return "<html><body></body></html>", "https://irp.fas.org/x/"

    monkeypatch.setattr(fas, "_get", fake_get)
    page = await fas.page("x")
    assert page["text"] == "" and page["pdfs"] == []


async def test_fas_refuses_non_html_documents(upstream):
    xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    upstream.add("https://irp.fas.org/", httpx2.Response(200, content=b"PK\x03\x04...",
                                                        headers={"content-type": xlsx}))
    err = await fas.page("nsa/stinfo-finding-aid.xlsx")  # returned the zip bytes as "text"
    assert err["error"] is True and err["upstream_status"] == 415
    assert "https://irp.fas.org/nsa/stinfo-finding-aid.xlsx" in err["message"]


def test_frus_document_with_empty_content():
    doc = frus._parse_document('<div class="content"></div>', "frus1969-76v21", 7)
    assert doc["body"] == ""


def test_config_blank_values_fall_back(monkeypatch):
    from app import config

    monkeypatch.setenv("FEC_API_KEY", "   ")
    assert config._env("FEC_API_KEY", "DEMO_KEY") == "DEMO_KEY"
    monkeypatch.setenv("FEC_API_KEY", " real ")
    assert config._env("FEC_API_KEY", "DEMO_KEY") == "real"
    monkeypatch.delenv("FEC_API_KEY")
    assert config._env("FEC_API_KEY", "DEMO_KEY") == "DEMO_KEY"


def test_env_example_has_no_inline_comments():
    """`KEY=   # note` is read as the value '# note' (python-dotenv) and docker
    --env-file keeps inline comments in every value."""
    from pathlib import Path

    from dotenv import dotenv_values

    example = Path(__file__).resolve().parents[2] / ".env.example"
    values = dotenv_values(example)
    assert values and all(not (v or "").lstrip().startswith("#") for v in values.values())
    assert all("#" not in line for line in example.read_text().splitlines()
               if line and not line.startswith("#"))
    assert json.dumps(values)  # parseable
