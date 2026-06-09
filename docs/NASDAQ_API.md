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

## Field parsing gotchas

- **`MarketCap`** is a string with commas: `"5,553,872,968,719"`. Strip commas + cast to int.
- **Prices** are strings with dollar signs: `"$228.40"`. Strip + cast to float.
- **`historical.tradesTable.rows`** is newest-first.

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
  'https://api.nasdaq.com/api/quote/NVDA/historical?assetclass=stocks&fromdate=2026-04-15&todate=2026-05-15&limit=30'
```

## Other endpoints worth knowing

Discoverable via DevTools → Network on `nasdaq.com`:

- `/api/quote/{TICKER}/financials?frequency=A` — annual income statement, balance sheet, cash flow
- `/api/company/{TICKER}/insider-trades?limit=N`
- `/api/company/{TICKER}/earnings-surprise?limit=N`
- `/api/calendar/earnings?date=YYYY-MM-DD`
- `/api/calendar/ipo?date=YYYY-MM-DD`
- `/api/screener/stocks?tableonly=true&limit=N` — full stock screener output

Not currently wired into datagod.

## Rate limits

Not published. Observed ~90 calls/sleep(0.25s) in a single session with no throttling. Aggressive use (10+ req/sec) is known to trigger blocks.
