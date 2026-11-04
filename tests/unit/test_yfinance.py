"""yfinance: Yahoo failures that yfinance logs (and swallows) become error-dicts.

yf.Ticker is faked; the fakes log through the real `yfinance` logger, as
yfinance does, with messages copied from live yfinance 1.8.0 runs (2026-11-04).
"""

import asyncio
import logging
import threading

import pandas as pd
import pytest
from yfinance.exceptions import YFRateLimitError

from app.clients import yfin

pytestmark = pytest.mark.anyio

YF_LOG = logging.getLogger("yfinance")
INVALID_CRUMB = ('HTTP Error 401: Unauthorized{"finance":{"result":null,"error":'
                 '{"code":"Unauthorized","description":"Invalid Crumb"}}}')
CRUMB_429 = "Crumb fetch rate-limited (HTTP 429), continuing without crumb"
ETF_404 = ('HTTP Error 404: Not Found{"quoteSummary":{"result":null,"error":{"code":"Not Found",'
           '"description":"No fundamentals data found for symbol: SPY"}}}')
DELISTED = "$ZZZZ: No data found, symbol may be delisted"
NO_FRAME = pd.DataFrame()
HOLDERS = pd.DataFrame({"Holder": ["Vanguard Group Inc"], "Shares": [1_400_000_000]})


def fake_ticker(monkeypatch, **attrs):
    """Stand-in for yf.Ticker: `name=(value, (level, message), ...)` makes the
    attribute `name` log those records and return `value`, as yfinance does."""

    class FakeTicker:
        def __init__(self, symbol):
            self.symbol = symbol

        def __getattr__(self, name):
            value, *records = attrs[name]
            for level, message in records:
                YF_LOG.log(level, message)
            return value

    monkeypatch.setattr(yfin.yf, "Ticker", FakeTicker)


ERROR, WARNING = logging.ERROR, logging.WARNING


# ── an empty result with a logged error is the error ────────────────────

@pytest.mark.parametrize(("records", "status"), [
    ([(ERROR, INVALID_CRUMB)], 0),                          # refused session → 502
    ([(WARNING, CRUMB_429), (ERROR, INVALID_CRUMB)], 429),  # …because the crumb fetch was rate-limited
    ([(ERROR, ETF_404)], 404),                              # Yahoo has nothing for the symbol
    ([(ERROR, ETF_404), (ERROR, DELISTED)], 404),
    ([(ERROR, INVALID_CRUMB), (ERROR, DELISTED)], 0),       # partly refused: not a clean "not found"
])
async def test_empty_result_with_logged_error_is_an_error(monkeypatch, records, status):
    fake_ticker(monkeypatch, recommendations=(NO_FRAME, *records))
    result = await yfin.recommendations("AAPL")
    assert result["error"] is True and result["source"] == "yfinance"
    assert result["upstream_status"] == status
    assert result["message"].startswith("yfinance returned no data; yfinance logged: ")
    for _, message in records:
        assert message[:60] in result["message"]


async def test_empty_result_without_logged_error_stays_a_success(monkeypatch):
    # BRK-A pays no dividends: an empty answer is the right one. A WARNING alone
    # (yfinance carrying on without a crumb) doesn't make it an error either.
    fake_ticker(monkeypatch, dividends=(pd.Series(dtype=float), (WARNING, CRUMB_429)))
    assert await yfin.dividends("BRK-A") == []
    fake_ticker(monkeypatch, recommendations=(NO_FRAME,))
    assert await yfin.recommendations("SPY") == []


async def test_partial_data_is_kept_despite_logged_errors(monkeypatch):
    fake_ticker(monkeypatch, major_holders=(NO_FRAME, (ERROR, INVALID_CRUMB)),
                institutional_holders=(HOLDERS,), mutualfund_holders=(NO_FRAME,))
    result = await yfin.holders("AAPL")
    assert result["institutional"][0]["Holder"] == "Vanguard Group Inc"
    assert result["major"] == [] and result["mutual_fund"] == []


async def test_every_part_empty_is_empty(monkeypatch):
    fake_ticker(monkeypatch, major_holders=(NO_FRAME, (ERROR, ETF_404)),
                institutional_holders=(NO_FRAME,), mutualfund_holders=(NO_FRAME,))
    result = await yfin.holders("SPY")
    assert result["error"] is True and result["upstream_status"] == 404
    assert "No fundamentals data found for symbol: SPY" in result["message"]


async def test_options_expiry_echo_does_not_count_as_data(monkeypatch):
    class Chain:
        calls = puts = NO_FRAME

    class FakeTicker:
        def __init__(self, symbol):
            pass

        def option_chain(self, expiry):
            YF_LOG.error(INVALID_CRUMB)
            return Chain()

    monkeypatch.setattr(yfin.yf, "Ticker", FakeTicker)
    result = await yfin.options("AAPL", "2026-11-20")
    assert result["error"] is True and "Invalid Crumb" in result["message"]


# ── info: no name is never a quote ──────────────────────────────────────

@pytest.mark.parametrize("info", [{"shortName": "Apple Inc.", "symbol": "AAPL"}, {"longName": "S&P 500"}])
async def test_info_with_a_name_is_returned_unchanged(monkeypatch, info):
    fake_ticker(monkeypatch, info=(info,))
    assert await yfin.info("AAPL") == info


async def test_info_without_a_name_reports_what_yfinance_logged(monkeypatch):
    fake_ticker(monkeypatch, info=({"trailingPegRatio": None}, (ERROR, INVALID_CRUMB)))
    result = await yfin.info("AAPL")
    assert result["error"] is True and result["upstream_status"] == 0
    assert "Invalid Crumb" in result["message"]


@pytest.mark.parametrize("info", [{"trailingPegRatio": None}, {}])
async def test_info_without_a_name_is_an_error_even_when_nothing_was_logged(monkeypatch, info):
    fake_ticker(monkeypatch, info=(info,))
    result = await yfin.info("ZZZZ")
    assert result["error"] is True and result["upstream_status"] == 0
    assert result["message"] == "Yahoo returned no quote for 'ZZZZ' (yfinance logged no reason)"


# ── exceptions ──────────────────────────────────────────────────────────

async def test_rate_limit_exception_is_429(monkeypatch):
    class FakeTicker:
        def __init__(self, symbol):
            pass

        @property
        def news(self):
            YF_LOG.warning(CRUMB_429)
            raise YFRateLimitError()

    monkeypatch.setattr(yfin.yf, "Ticker", FakeTicker)
    result = await yfin.news("AAPL")
    assert result["error"] is True and result["upstream_status"] == 429
    assert "Too Many Requests" in result["message"] and CRUMB_429 in result["message"]


# ── the log capture ─────────────────────────────────────────────────────

async def test_logged_lines_are_deduplicated_and_capped(monkeypatch):
    page = "<html>" + "x" * 5000 + "</html>"
    fake_ticker(monkeypatch, recommendations=(NO_FRAME, (ERROR, INVALID_CRUMB),
                                              (ERROR, INVALID_CRUMB), (ERROR, f"HTTP Error 503: {page}")))
    message = (await yfin.recommendations("AAPL"))["message"]
    assert message.count("Invalid Crumb") == 1
    assert len(message) < 800


async def test_concurrent_calls_only_see_their_own_logs(monkeypatch):
    both_running = threading.Barrier(2, timeout=5)

    class FakeTicker:
        def __init__(self, symbol):
            self.symbol = symbol

        @property
        def recommendations(self):
            both_running.wait()  # the two calls are in flight at once…
            if self.symbol == "BAD":
                YF_LOG.error(INVALID_CRUMB)
            both_running.wait()  # …and neither returns before the other has run
            return NO_FRAME

    monkeypatch.setattr(yfin.yf, "Ticker", FakeTicker)
    bad, ok = await asyncio.gather(yfin.recommendations("BAD"), yfin.recommendations("OK"))
    assert bad["error"] is True and "Invalid Crumb" in bad["message"]
    assert ok == []


async def test_capture_lets_yfinance_records_through(monkeypatch, caplog):
    fake_ticker(monkeypatch, recommendations=(NO_FRAME, (ERROR, INVALID_CRUMB)))
    with caplog.at_level(logging.WARNING, logger="yfinance"):
        await yfin.recommendations("AAPL")
    assert [r.getMessage() for r in caplog.records if r.name == "yfinance"] == [INVALID_CRUMB]


async def test_capture_survives_a_malformed_record(monkeypatch):
    # Keep the record away from handlers: pytest's own fails a test on a bad record.
    monkeypatch.setattr(YF_LOG, "propagate", False)
    monkeypatch.setattr(logging, "lastResort", logging.NullHandler())

    class FakeTicker:
        def __init__(self, symbol):
            pass

        @property
        def recommendations(self):
            YF_LOG.error("bad format %d", "not-a-number")  # getMessage() raises
            return NO_FRAME

    monkeypatch.setattr(yfin.yf, "Ticker", FakeTicker)
    assert await yfin.recommendations("AAPL") == []


def test_nothing_is_collected_outside_a_call():
    YF_LOG.error(INVALID_CRUMB)  # e.g. yfinance used directly, not through _run
    assert yfin._logged.get() is None


# ── through the API ─────────────────────────────────────────────────────

@pytest.mark.parametrize(("records", "http_status"), [
    ([(ERROR, INVALID_CRUMB)], 502),
    ([(WARNING, CRUMB_429), (ERROR, INVALID_CRUMB)], 429),
    ([(ERROR, ETF_404)], 404),
])
def test_route_answers_the_logged_failure(api, monkeypatch, records, http_status):
    fake_ticker(monkeypatch, recommendations=(NO_FRAME, *records))
    r = api.get("/yfinance/recommendations/AAPL")
    assert r.status_code == http_status
    body = r.json()
    assert body["meta"]["status"] == "error" and body["data"]["source"] == "yfinance"
    assert records[-1][1][:40] in body["error"]
