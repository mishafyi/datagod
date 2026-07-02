---
name: jefs
description: "Financial disclosures of federal judges (Judicial) — judges' financial disclosure reports and holdings. Session-based: requires Playwright registration + reCAPTCHA first. Use for the finances or holdings of federal judges and the judiciary."
keywords: "federal judges, judicial, judges financial disclosures, judiciary, court, judge holdings, financial disclosure reports"
routes: "/jefs/facets, /jefs/register, /jefs/reset, /jefs/search"
---

# JEFS API Reference

> **⚠️ DISABLED ON THE API (2026-06-11).** The four `/jefs/*` routes are commented out in
> `app/main.py` and are not served. Registration needs a headed browser + a human-solved
> reCAPTCHA, so it can't run on the headless server. The client and flow documented below
> remain valid and verified — re-enable by uncommenting the JEFS route block, the `jefs`
> import, and the JEFS `API_TAGS` entry in `app/main.py` (then restore the JEFS row in
> `scripts/gen_api_guide.py`'s QUICK_INDEX and regenerate the guide).

**Site**: [pub.jefs.uscourts.gov](https://pub.jefs.uscourts.gov)
**Purpose**: Federal-judge financial disclosure database (annual statements filed by every Article III judge + magistrate + bankruptcy judge).
**Auth**: **No public REST API**. The site is session-based, reCAPTCHA-protected, requires real-name registration each session.

## Why this is unusual

Every other DataGod client wraps a free, anonymous public API. JEFS is the exception:
- The site is browser-rendered (JS-heavy) with an **invisible** reCAPTCHA v2 on registration (`data-size="invisible"`, fires on submit via `data-callback="rcResults"`)
- All API calls go to `POST /index.php` with `action=` query parameter (Apache Solr backend)
- Cookies must be captured from a real browser session (including the F5/`TS…` WAF cookies, which must be sent back on every later request)
- 30-minute idle timeout
- **Legal requirement**: every user must check a box that reads *"I certify under penalty of perjury that the foregoing is true and correct. (28 U.S.C. § 1746)."* — supplying real name, occupation, email, phone, and mailing address for each session

So this client is **half-automated**: Playwright fills the form, the user solves the reCAPTCHA and submits.

> **Verified against the live DOM 2026-06-10.** The registration form is `#registration-form` inside the `#register-dialog` (opened by the "Begin Registration" button). Required inputs: `name`, `occupation`, `email`, `phone`, the five address fields `address-line-1` / `address-line-2` / `address-city` / `address-state` / `address-postalcode`, and the `certified` checkbox — plus a hidden `_csrf` token and the reCAPTCHA token, both of which ride along automatically because the site's own JS submits `$('#registration-form').serialize()`. There is **no single `name="address"` field** (an earlier version of this client assumed one and could never register). On success the JS runs `Metro.dialog.close('#register-dialog'); location.href = "/"`, so the success signal is the form disappearing — not a URL change.
>
> **Local-only by nature.** Registration needs a visible browser window + a human-solved reCAPTCHA, so it can only run where someone is at the keyboard. It cannot work on the headless Coolify deployment. Playwright is therefore a **local dev dependency, deliberately not in `requirements.txt`** (install with `.venv/bin/pip install playwright && .venv/bin/playwright install chromium`); on the server `/jefs/register` returns a clear "Playwright not installed" error, which is the correct behavior there.

## Discovered endpoints

All POST to `/index.php` with `action=X`:

| Action | Params | What it does |
|--------|--------|--------------|
| `search` | `q`, `facet_string` (JSON), `sort_by`, `sort_dir`, `start`, `page_size` | Solr search over filings |
| `get_facets` | — | Returns filter dropdowns (years, court types, positions, report types) |
| `add` | `id` | Add filing to download queue |
| `rem` | `id` | Remove from queue |
| `download` | (GET) | Returns ZIP of queued filings (max 100) |
| `verify_recaptcha` | `token` | Server-side reCAPTCHA verification |
| `reset` | — | Clear session |

## Search response structure

```json
{
  "count": 1234,
  "rows": [{
    "filer_id_FK": "...",
    "name_s": "Judge Name",
    "position_s": "District Judge",
    "court_type_s": "District",
    "district_s": "...",
    "circuit_s": "...",
    "operating_year_s": "2023",
    "report_type_s": "Annual",
    "published_dt": "..."
  }, ...]
}
```

## DataGod integration

| Route | What it does |
|-------|-------------|
| `POST /jefs/register?name=&occupation=&email=&phone=&address_line1=&city=&state=&postalcode=&address_line2=&headed=true` | Opens Playwright browser, fills the form, user solves reCAPTCHA + clicks "Enter Database", authorized cookies captured; the response includes a `get_facets` probe as proof the session works |
| `GET /jefs/facets` | Returns filter dropdowns (requires active session) |
| `GET /jefs/search?q=&year=&court_type=&start=0` | Search filings (requires active session) |
| `POST /jefs/reset` | Clear session |

Session is a process-singleton. One DataGod server instance = one JEFS session at a time.

## Usage example

```python
import httpx

# 1. Register a session (opens browser — user solves reCAPTCHA + clicks "Enter Database")
r = httpx.post("http://localhost:8000/jefs/register",
               params={"name": "Real Name", "occupation": "Researcher",
                       "email": "you@example.com", "phone": "(202) 555-0100",
                       "address_line1": "123 Main St", "city": "Washington",
                       "state": "DC", "postalcode": "20001"})
print(r.json())  # {"registered": True, "cookies_captured": 4, "session_check": "..."}

# 2. Search for disclosures
r = httpx.get("http://localhost:8000/jefs/search",
              params={"q": "John Roberts", "year": "2024"})
print(r.json()["data"]["count"], "results")
```

## Caveats

- **Headed browser required** for reCAPTCHA — user must be at the keyboard
- **Real credentials required** — JEFS terms make false registration a federal crime
- **Per-session re-register** — sessions expire after 30 min idle, then need to re-do the browser flow
- **Selectors may break** — JEFS DOM may change; client may need adjustment
- **Download cap 100/call** — for batch use, paginate
- **No bulk export** — the public site is the only access path

## Why this matters

JEFS lets you check whether a federal judge held stock in a company that appeared in a case before them. Combined with EDGAR, USAspending, and FEC, it's the missing piece for a complete picture of US-government-financial conflict-of-interest analysis.

## Build history

Methodology originally researched in a 2026-03-16 exploration session (private research log). The earlier standalone `jefs_client.py` was lost; this is the rebuild inside DataGod.
