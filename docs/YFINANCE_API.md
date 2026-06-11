---
name: yfinance
description: "Deep data for stocks, shares, and equities (Yahoo Finance) by ticker/symbol — ~140 fundamental fields (market cap, P/E, EPS, beta, margins, ROE), full financial statements (income statement, balance sheet, cash flow), options chains (calls, puts, implied volatility), institutional and fund holders/ownership, analyst recommendations and price targets, dividends, earnings, news, and OHLCV price history. Use for thorough single-ticker stock analysis beyond a basic quote."
keywords: "stocks, shares, equities, ticker, symbol, stock price, fundamentals, market cap, P/E, EPS, beta, profit margin, ROE, income statement, balance sheet, cash flow, financial statements, options, options chain, calls, puts, implied volatility, holders, ownership, institutional holders, analyst ratings, recommendations, price targets, dividends, earnings, news, OHLCV, history"
routes: "/yfinance/dividends/{ticker}, /yfinance/financials/{ticker}, /yfinance/history/{ticker}, /yfinance/holders/{ticker}, /yfinance/info/{ticker}, /yfinance/news/{ticker}, /yfinance/options/{ticker}, /yfinance/recommendations/{ticker}"
---

# yfinance API Reference

**Library**: [ranaroussi/yfinance](https://github.com/ranaroussi/yfinance) (installed from PyPI, unmodified)
**Auth**: None — uses Yahoo Finance's unofficial endpoints with the library's built-in crumb+cookie handling
**Status**: Unofficial. yfinance scrapes Yahoo Finance; Yahoo periodically changes shape, yfinance patches it. Pin a version in `requirements.txt` if you want reproducibility.

## Why yfinance alongside Nasdaq

| | Nasdaq.com | yfinance |
|--|------|------|
| Coverage | US listed only | Global: equities, OTC, ADRs, ETFs, funds, FX, crypto |
| Fundamentals | Basic (mcap, P/E, dividend, 52w) | Deep: income statement, balance sheet, cash flow, ratios |
| Analyst data | None | Recommendations history, price targets |
| Holders | None | Major, institutional, mutual fund |
| Options | None | Full chain (calls + puts per expiry) |
| News | None | Recent headlines |
| History depth | ~10 years | Back to 1970 for established names |
| Latency | Real-time | 15-min delayed |

Use Nasdaq for fast US quotes, yfinance for everything else.

## Endpoints

| Path | Returns |
|------|---------|
| `GET /yfinance/info/{ticker}` | ~140-field info dict: marketCap, trailingPE, forwardPE, beta, dividendYield, profitMargins, returnOnEquity, targetMeanPrice, recommendationKey, etc. |
| `GET /yfinance/history/{ticker}?period=1mo&interval=1d` | OHLCV records |
| `GET /yfinance/news/{ticker}` | Recent news items |
| `GET /yfinance/recommendations/{ticker}` | Analyst recommendation history (strongBuy/buy/hold/sell/strongSell counts per period) |
| `GET /yfinance/holders/{ticker}` | `{major, institutional, mutual_fund}` |
| `GET /yfinance/financials/{ticker}` | Annual + quarterly income statement, balance sheet, cash flow |
| `GET /yfinance/dividends/{ticker}` | Dividend payment history |
| `GET /yfinance/options/{ticker}?expiry=YYYY-MM-DD` | Empty expiry lists available expiries; with expiry returns `{calls, puts}` |

## Parameter values

**`period`**: `1d`, `5d`, `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`, `10y`, `ytd`, `max`
**`interval`**: `1m`, `2m`, `5m`, `15m`, `30m`, `60m`, `90m`, `1h`, `1d`, `5d`, `1wk`, `1mo`, `3mo`
Constraint: intraday intervals (`<1d`) only work for recent windows (`<60d`).

## Implementation notes

- yfinance is **synchronous**; the client wraps each call in `asyncio.to_thread()` to avoid blocking the FastAPI event loop.
- DataFrames are converted via `df.reset_index().to_dict(orient='records')` to JSON-serializable lists.
- NaN values become JSON `null`.
- yfinance is imported unmodified so upstream updates propagate via `pip install --upgrade yfinance`. The version pin in `requirements.txt` is `>=0.2.40`.

## Curl examples

```bash
# Full fundamentals
curl http://localhost:8000/yfinance/info/NVDA | jq '.data | {mcap: .marketCap, pe: .trailingPE, eps: .trailingEps, beta: .beta, target: .targetMeanPrice}'

# 5-year monthly history
curl 'http://localhost:8000/yfinance/history/AAPL?period=5y&interval=1mo'

# Analyst recommendations
curl http://localhost:8000/yfinance/recommendations/TSLA

# Options chain for next Friday's expiry
curl http://localhost:8000/yfinance/options/SPY  # lists expiries
curl 'http://localhost:8000/yfinance/options/SPY?expiry=2026-05-22'

# Institutional ownership
curl http://localhost:8000/yfinance/holders/NVDA
```

## Caveats

- Yahoo rate-limits aggressively. yfinance has retries built in, but bursts can still trigger blocks.
- `.info` makes multiple internal HTTP calls; expect 1–3 seconds per ticker.
- `period=max` history can return 50+ years of daily bars; payload size matters.
- For batch quotes across many tickers, yfinance has `yf.Tickers("AAPL MSFT TSLA")` — not currently exposed via the API.
