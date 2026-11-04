---
name: nasdaq
description: "Stock-market quotes for stocks, shares, and equities (Nasdaq.com, unofficial) — price, quote, bid/ask, volume, market cap, sector, industry, P/E, 52-week range, dividends, and daily OHLCV price history by ticker/symbol. Use for a quick quote or price snapshot of a listed ticker."
keywords: "stocks, shares, equities, stock price, quote, ticker, symbol, market cap, sector, industry, P/E ratio, 52-week range, bid, ask, volume, dividends, OHLC, price history, real-time quote"
routes: "/nasdaq/calendar/earnings, /nasdaq/calendar/ipo, /nasdaq/dividends/{ticker}, /nasdaq/earnings-surprise/{ticker}, /nasdaq/financials/{ticker}, /nasdaq/history/{ticker}, /nasdaq/insider-trades/{ticker}, /nasdaq/price/{ticker}, /nasdaq/quote/{ticker}, /nasdaq/screener"
---

# Nasdaq.com API Reference

**Base URL**: `https://api.nasdaq.com`
**Auth**: None. A browser-like `User-Agent` header is required — without it the API returns HTTP 401. No API key, no signup, no cookie or crumb.
**Status**: Unofficial. This is the same JSON the nasdaq.com frontend calls when rendering quote pages. Not published or supported by Nasdaq. Could change shape or block at any time.

## Endpoints used by datagod

| Path | Route | What it returns |
|------|-------|-----------------|
| `/api/quote/{TICKER}/summary?assetclass=stocks` | `GET /nasdaq/quote/{ticker}` | Market cap, sector, industry, P/E, dividend, 52-week range |
| `/api/quote/{TICKER}/info?assetclass=stocks` | `GET /nasdaq/price/{ticker}` | Real-time price, bid/ask, volume, percent change |
| `/api/quote/{TICKER}/historical?assetclass=stocks&fromdate=YYYY-MM-DD&todate=YYYY-MM-DD&limit=N` | `GET /nasdaq/history/{ticker}` | Daily OHLCV between two dates |
| `/api/quote/{TICKER}/dividends?assetclass=stocks` | `GET /nasdaq/dividends/{ticker}` | Dividend history |

## Asset classes

The `assetclass` query param picks the dataset. Wrong class returns `data: null`.

`stocks`, `etf`, `mutualfunds`, `index`, `currencies`, `commodities`, `crypto`

## Coverage

US-listed only: Nasdaq, NYSE, AMEX, and select ADRs.
**Not covered**: OTC (e.g., `THPTF`), international exchanges, pre-IPO, options chains.

## Response shape

All responses follow:

```json
{
  "data": { ... },
  "message": null,
  "status": {"rCode": 200, "bCodeMessage": null, "developerMessage": null}
}
```

Pull from `data` and ignore the upstream envelope. Datagod's `ResponseEnvelopeMiddleware` then wraps the whole thing in its own envelope (`{meta, data, error}`).

**Failures come back as HTTP 200** with the real status in the body — e.g. an unknown ticker is
`{"data": null, "status": {"rCode": 400, "bCodeMessage": [{"code": 1001, "errorMessage": "Symbol not exists."}]}}`.
The client turns any `rCode` other than 200 into the error-dict (`upstream_status` = rCode, message =
the `errorMessage`s), so DataGod answers 400 with `meta.status: "error"` instead of a fake success.

## Field parsing gotchas

- **`MarketCap`** is a string with commas: `"5,553,872,968,719"`. Strip commas + cast to int.
- **Prices** are strings with dollar signs: `"$228.40"`. Strip + cast to float.
- **`historical.tradesTable.rows`** is newest-first.
- **History only answers windows that reach the present** (observed 2026-11-04): `fromdate=2026-01-01&todate=2026-11-03` returned all 211 sessions back to Jan 2, but every one-month window that ended before October — even `2026-09-01..2026-09-28` — returned `totalRecords: 0` with `rows: null`. For an older range, request it with `todate` = today and slice, or use `/yfinance/history`.

## Curl examples

```bash
# Market cap + summary stats
curl -sH 'User-Agent: Mozilla/5.0' \
  'https://api.nasdaq.com/api/quote/NVDA/summary?assetclass=stocks'

# Real-time price
curl -sH 'User-Agent: Mozilla/5.0' \
  'https://api.nasdaq.com/api/quote/NVDA/info?assetclass=stocks'

# 30-day daily OHLCV
curl -sH 'User-Agent: Mozilla/5.0' \
  'https://api.nasdaq.com/api/quote/NVDA/historical?assetclass=stocks&fromdate=2026-10-05&todate=2026-11-04&limit=30'  # todate must be recent
```

## Other endpoints worth knowing

Discoverable via DevTools → Network on `nasdaq.com`:

- `/api/company/{TICKER}/financials?frequency=1` — income statement, balance sheet, cash flow. `frequency` is **`1` (annual) or `2` (quarterly) only**; `A`/`Q` answer rCode 400 "The value 'A' is not valid." (the DataGod route accepts `annual`/`A`/`1` and `quarterly`/`Q`/`2` and maps them)
- `/api/company/{TICKER}/insider-trades?limit=N`
- `/api/company/{TICKER}/earnings-surprise?limit=N`
- `/api/calendar/earnings?date=YYYY-MM-DD`
- `/api/ipo/calendar?date=YYYY-MM` — a **month** (priced/upcoming/filed/withdrawn); a full `YYYY-MM-DD` is rCode 400, so the client trims it to the month
- `/api/screener/stocks?tableonly=true&limit=N` — full stock screener output

All of these are wired into datagod (`/nasdaq/financials`, `/nasdaq/insider-trades`, `/nasdaq/earnings-surprise`, `/nasdaq/calendar/earnings`, `/nasdaq/calendar/ipo`, `/nasdaq/screener`).

## Rate limits

Not published. Observed ~90 calls/sleep(0.25s) in a single session with no throttling. Aggressive use (10+ req/sec) is known to trigger blocks.
