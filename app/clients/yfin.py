"""yfinance — Yahoo Finance wrapper. Deep fundamentals, news, analyst data.

This module imports the third-party `yfinance` package unchanged so it can
track upstream updates. yfinance is synchronous; every call is dispatched
to a worker thread via asyncio.to_thread() to keep the event loop free.

yfinance does not raise when Yahoo refuses a request (`hide_exceptions`, its
default): it logs the failure and returns empty data. `_run` collects what
yfinance logs during each call, and an empty result that came with a logged
error becomes the error-dict carrying those lines (e.g. Yahoo's
`401 … "Invalid Crumb"`), so a refused request no longer reads as "no data".
"""

import asyncio
import contextlib
import contextvars
import logging
import re
from collections.abc import Callable
from typing import Any

import pandas as pd
import yfinance as yf
from yfinance.exceptions import YFRateLimitError

from . import UpstreamJSON, clean_text, error_dict
from . import _error as _base_error

SOURCE = "yfinance"


def _error(exc: BaseException) -> dict:
    return _base_error(SOURCE, exc)


# ── What yfinance logs during a call ────────────────────────────────────
# (level, message) of each WARNING+ record yfinance logs while the call runs.
# A ContextVar keeps concurrent calls apart: asyncio.to_thread runs each call
# in its own copy of the context, and yfinance logs from that same thread.
_logged: contextvars.ContextVar[list[tuple[int, str]] | None] = contextvars.ContextVar(
    "yfinance_logged", default=None)


class _Collect(logging.Filter):
    """Copies yfinance's WARNING+ records into the running call's list.

    A filter, not a handler, so it lets every record through: yfinance's
    messages still reach stderr as before (a handler on its logger would stop
    logging's last-resort output). It must never raise into yfinance.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        logged = _logged.get()
        if logged is not None and record.levelno >= logging.WARNING:
            with contextlib.suppress(Exception):  # a malformed record (getMessage raises)
                logged.append((record.levelno, record.getMessage()))
        return True


logging.getLogger("yfinance").addFilter(_Collect())

_LINE_CAP = 300  # per logged line; Yahoo error bodies can be whole HTML pages
# Lines that mean Yahoo has nothing for the symbol: an HTTP 404 ("Quote not
# found", "No fundamentals data found") or yfinance's "possibly delisted" /
# "symbol may be delisted" verdicts (an unknown symbol, or an ETF's missing data).
_NOT_FOUND = re.compile(r"HTTP Error 404\b|delisted", re.IGNORECASE)
# yfinance's "Crumb fetch rate-limited (HTTP 429)", an HTTP Error 429, or its
# YFRateLimitError text "Too Many Requests. Rate limited."
_RATE_LIMITED = re.compile(r"\b429\b|rate[- ]limit|too many requests", re.IGNORECASE)


def _logged_status(logged: list[tuple[int, str]]) -> int:
    """upstream_status for a call that returned nothing and logged errors:
    404 when every error says Yahoo has no such data, 429 when anything logged
    shows rate limiting, else 0 (→ 502: Yahoo refused or failed)."""
    errors = [msg for level, msg in logged if level >= logging.ERROR]
    if errors and all(_NOT_FOUND.search(msg) for msg in errors):
        return 404
    if any(_RATE_LIMITED.search(msg) for _, msg in logged):
        return 429
    return 0


def _with_log(message: str, logged: list[tuple[int, str]]) -> str:
    """`message`, then each distinct logged line (whitespace collapsed, capped)."""
    lines: list[str] = []
    for _, msg in logged:
        line = (clean_text(msg) or "")[:_LINE_CAP]
        if line and line not in lines:
            lines.append(line)
    return f"{message}; yfinance logged: {' | '.join(lines)}" if lines else message


def _is_empty(data: Any) -> bool:
    """No data at all: an empty list, or a dict every part of which is empty."""
    if isinstance(data, dict):
        return not any(data.values())
    return not data


def _call(fn: Callable[[], Any], empty: Callable[[Any], bool], no_data: str | None) -> UpstreamJSON:
    """Run `fn` (in the worker thread), collecting what yfinance logs meanwhile.

    Data is returned as is, even when yfinance logged errors on the way (a
    partial result, e.g. holders without the mutual-fund table, stays a
    success). An empty result is an error only when yfinance logged one, or —
    for calls where empty is never a valid answer (`no_data`) — always.
    """
    logged: list[tuple[int, str]] = []
    token = _logged.set(logged)
    try:
        data = fn()
    except YFRateLimitError as exc:  # raised even under hide_exceptions
        return error_dict(SOURCE, 429, _with_log(str(exc), logged))
    except Exception as exc:
        return _error(exc)
    finally:
        _logged.reset(token)
    if not empty(data):
        return data
    if any(level >= logging.ERROR for level, _ in logged):
        return error_dict(SOURCE, _logged_status(logged),
                          _with_log("yfinance returned no data", logged))
    if no_data:
        return error_dict(SOURCE, 0, no_data)
    return data


async def _run(fn: Callable[[], Any], *, empty: Callable[[Any], bool] = _is_empty,
               no_data: str | None = None) -> UpstreamJSON:
    return await asyncio.to_thread(_call, fn, empty, no_data)


def _df_to_records(obj: Any) -> list[dict]:
    """Convert a DataFrame or Series to a list of records (date-aware)."""
    if obj is None:
        return []
    if isinstance(obj, pd.Series):
        obj = obj.to_frame()
    if not isinstance(obj, pd.DataFrame) or obj.empty:
        return []
    obj = obj.reset_index()
    obj.columns = [str(c) for c in obj.columns]
    return obj.astype(object).where(obj.notna(), None).to_dict(orient="records")


def _no_quote(data: Any) -> bool:
    # Every real quote (equity, ETF, index, FX, crypto) carries a name. A failed
    # info call comes back as a 1-key dict ({"trailingPegRatio": None}), not empty.
    return not data or not (data.get("shortName") or data.get("longName"))


async def info(ticker: str) -> UpstreamJSON:
    """Full ticker info: ~140 fields incl. mcap, P/E, EPS, beta, margins, ROE, analyst targets."""
    return await _run(lambda: yf.Ticker(ticker).info, empty=_no_quote,
                      no_data=f"Yahoo returned no quote for '{ticker}' (yfinance logged no reason)")


async def history(ticker: str, period: str = "1mo",
                  interval: str = "1d") -> UpstreamJSON:
    """OHLCV history. period: 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max. interval: 1m,5m,1h,1d,1wk,1mo."""
    def _do() -> list[dict]:
        df = yf.Ticker(ticker).history(period=period, interval=interval)
        return _df_to_records(df)
    return await _run(_do)


async def news(ticker: str) -> UpstreamJSON:
    """Recent news headlines linked to the ticker."""
    return await _run(lambda: yf.Ticker(ticker).news or [])


async def recommendations(ticker: str) -> UpstreamJSON:
    """Analyst recommendation history (strong-buy, buy, hold, sell, strong-sell counts)."""
    return await _run(lambda: _df_to_records(yf.Ticker(ticker).recommendations))


async def holders(ticker: str) -> UpstreamJSON:
    """Major, institutional, and mutual-fund holders."""
    def _do() -> dict:
        t = yf.Ticker(ticker)
        return {
            "major": _df_to_records(t.major_holders),
            "institutional": _df_to_records(t.institutional_holders),
            "mutual_fund": _df_to_records(t.mutualfund_holders),
        }
    return await _run(_do)


async def financials(ticker: str) -> UpstreamJSON:
    """Annual + quarterly income statement, balance sheet, cash flow."""
    def _do() -> dict:
        t = yf.Ticker(ticker)
        return {
            "income_stmt": _df_to_records(t.income_stmt),
            "balance_sheet": _df_to_records(t.balance_sheet),
            "cashflow": _df_to_records(t.cashflow),
            "income_stmt_quarterly": _df_to_records(t.quarterly_income_stmt),
            "balance_sheet_quarterly": _df_to_records(t.quarterly_balance_sheet),
            "cashflow_quarterly": _df_to_records(t.quarterly_cashflow),
        }
    return await _run(_do)


async def dividends(ticker: str) -> UpstreamJSON:
    """Dividend payment history."""
    return await _run(lambda: _df_to_records(yf.Ticker(ticker).dividends))


async def earnings(ticker: str, limit: int = 12) -> UpstreamJSON:
    """Earnings history + next-earnings calendar.

    `earnings_dates`: past/upcoming earnings dates with EPS estimate, reported
    EPS, and surprise % (yfinance `get_earnings_dates(limit=...)`, a DataFrame).
    `calendar`: next earnings/dividend dates and EPS/revenue estimate ranges
    (yfinance `calendar`, already a plain dict — returned unchanged).
    """
    def _do() -> dict:
        t = yf.Ticker(ticker)
        return {
            "earnings_dates": _df_to_records(t.get_earnings_dates(limit=limit)),
            "calendar": t.calendar,
        }
    return await _run(_do)


async def options(ticker: str, expiry: str = "") -> UpstreamJSON:
    """Options chain. expiry blank → list available expiries; else returns calls+puts for that date.

    yfinance logs nothing when Yahoo refuses the options request (it drops the
    error body), so a refused call still reads as "no options listed".
    """
    def _do() -> dict:
        t = yf.Ticker(ticker)
        if not expiry:
            return {"expirations": list(t.options)}
        chain = t.option_chain(expiry)
        return {"expiry": expiry,
                "calls": _df_to_records(chain.calls),
                "puts": _df_to_records(chain.puts)}
    return await _run(_do, empty=lambda d: not (d.get("expirations") or d.get("calls") or d.get("puts")))
