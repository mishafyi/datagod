---
name: congress
description: "US legislation and Congress (Congress.gov) — bills and laws with status, sponsors and cosponsors, and actions; members of Congress (representatives, senators); committees; and roll-call votes. Use for tracking laws, what Congress is doing, or how members voted."
keywords: "legislation, bills, laws, Congress, House, Senate, representatives, senators, members of Congress, votes, roll call, sponsors, cosponsors, committees"
routes: "/congress/bill/{congress_num}/{bill_type}/{number}, /congress/bills, /congress/members, /congress/votes"
---

# Congress

US legislation and Congress (Congress.gov) — bills and laws with status, sponsors and cosponsors, and actions; members of Congress (representatives, senators); committees; and roll-call votes. Use for tracking laws, what Congress is doing, or how members voted.

## Endpoints

### `GET /congress/bill/{congress_num}/{bill_type}/{number}`

Full detail for one bill: sponsors, actions, latest status, summary.

**Params:** `congress_num` (path, integer, required) · `bill_type` (path, string, required) · `number` (path, integer, required)

### `GET /congress/bills`

Recent bills introduced in Congress. Legislation tracking.

**Params:** `limit` (query, integer, default 10, max 250) · `congress_num` (query, integer, default 0)

### `GET /congress/members`

Members of Congress (representatives and senators), with party and state.

**Params:** `limit` (query, integer, default 10, max 250)

### `GET /congress/votes`

Roll-call votes by chamber and session.

**Params:** `chamber` (query, string, default house) · `congress_session` (query, integer, default 118) · `limit` (query, integer, default 10, max 250)

## Quirks & notes

- `CONGRESS_API_KEY` with a `DEMO_KEY` fallback.
- Base `api.congress.gov/v3`. **The votes endpoint is `house-vote/{congress}` (House only).**

> Endpoint params are generated from the live OpenAPI schema (`/openapi.json`); the Quirks section is curated. Regenerate with `python -m scripts.gen_source_docs`.
