"""yfinance — Yahoo Finance wrapper. Deep fundamentals, news, analyst data.

This module imports the third-party `yfinance` package unchanged so it can
track upstream updates. yfinance is synchronous; every call is dispatched
to a worker thread via asyncio.to_thread() to keep the event loop free.
"""

import asyncio
from typing import Any

import pandas as pd
import yfinance as yf

from . import UpstreamJSON


def _error(exc: BaseException) -> dict:
    upstream_status = getattr(getattr(exc, "response", None), "status_code", 0)
    return {"error": True, "source": "yfinance",
            "upstream_status": upstream_status, "message": str(exc)}


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


async def _run(fn) -> UpstreamJSON:
    try:
        return await asyncio.to_thread(fn)
    except Exception as exc:
        return _error(exc)


async def info(ticker: str) -> UpstreamJSON:
    """Full ticker info: ~140 fields incl. mcap, P/E, EPS, beta, margins, ROE, analyst targets."""
    def _do() -> dict:
        data = yf.Ticker(ticker).info
        if not data:
            raise ValueError(f"No data for ticker '{ticker}'")
        return data
    return await _run(_do)


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


async def options(ticker: str, expiry: str = "") -> UpstreamJSON:
    """Options chain. expiry blank → list available expiries; else returns calls+puts for that date."""
    def _do() -> dict:
        t = yf.Ticker(ticker)
        if not expiry:
            return {"expirations": list(t.options)}
        chain = t.option_chain(expiry)
        return {"expiry": expiry,
                "calls": _df_to_records(chain.calls),
                "puts": _df_to_records(chain.puts)}
    return await _run(_do)
