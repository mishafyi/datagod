---
name: treasury
description: "US federal fiscal data (Treasury) — the national / public debt (debt to the penny, debt held by the public, intragovernmental), federal deficit context, average interest rates and yields on Treasury securities, and government exchange rates. Use for the size of the national debt or US borrowing costs."
keywords: "national debt, public debt, debt to the penny, federal debt, deficit, Treasury, interest rates, yields, borrowing costs, exchange rates, fiscal data"
routes: "/treasury/debt, /treasury/exchange, /treasury/rates"
---

# Treasury

US federal fiscal data (Treasury) — the national / public debt (debt to the penny, debt held by the public, intragovernmental), federal deficit context, average interest rates and yields on Treasury securities, and government exchange rates. Use for the size of the national debt or US borrowing costs.

## Endpoints

### `GET /treasury/debt`

US national / public debt (debt to the penny): total outstanding, debt held by the public, intragovernmental holdings, by date.

**Params:** `limit` (query, integer, default 5, max 100)

### `GET /treasury/exchange`

US Treasury reporting exchange rates (foreign-currency conversion rates used by the government).

**Params:** `limit` (query, integer, default 5, max 100)

### `GET /treasury/rates`

Average interest rates on outstanding US Treasury securities.

**Params:** `limit` (query, integer, default 5, max 100)

## Quirks & notes

- No key (Treasury Fiscal Data API).
- Datasets: debt → `debt_to_penny` (v2), rates → `avg_interest_rates` (v2), exchange → `rates_of_exchange` (v1).
- Newest-first (`sort=-record_date`); paginate via `page[size]`.

> Endpoint params are generated from the live OpenAPI schema (`/openapi.json`); the Quirks section is curated. Regenerate with `python -m scripts.gen_source_docs`.
