---
name: jefs
description: "Financial disclosures of federal judges (Judicial) — judges' financial disclosure reports and holdings. Session-based: requires Playwright registration + reCAPTCHA first. Use for the finances or holdings of federal judges and the judiciary."
keywords: "federal judges, judicial, judges financial disclosures, judiciary, court, judge holdings, financial disclosure reports"
routes: "/jefs/facets, /jefs/register, /jefs/reset, /jefs/search"
---

# JEFS API Reference

**Site**: [pub.jefs.uscourts.gov](https://pub.jefs.uscourts.gov)
**Purpose**: Federal-judge financial disclosure database (annual statements filed by every Article III judge + magistrate + bankruptcy judge).
**Auth**: **No public REST API**. The site is session-based, reCAPTCHA-protected, requires real-name registration each session.

## Why this is unusual

Every other DataGod client wraps a free, anonymous public API. JEFS is the exception:
- The site is browser-rendered (JS-heavy) with reCAPTCHA on registration
- All API calls go to `POST /index.php` with `action=` query parameter (Apache Solr backend)
- Cookies must be captured from a real browser session
- 30-minute idle timeout
- **Legal requirement**: every user must provide real name, occupation, and address **under penalty of perjury** for each session

So this client is **half-automated**: Playwright handles the browser, the user provides real credentials.

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
| `POST /jefs/register?name=&occupation=&address=&headed=true` | Opens Playwright browser, user solves reCAPTCHA + submits form, cookie captured |
| `GET /jefs/facets` | Returns filter dropdowns (requires active session) |
| `GET /jefs/search?q=&year=&court_type=&start=0` | Search filings (requires active session) |
| `POST /jefs/reset` | Clear session |

Session is a process-singleton. One DataGod server instance = one JEFS session at a time.

## Usage example

```python
import httpx

# 1. Register a session (opens browser — user solves reCAPTCHA)
r = httpx.post("http://localhost:8000/jefs/register",
               params={"name": "Real Name", "occupation": "Researcher",
                       "address": "123 Main St, City, ST 12345"})
print(r.json())  # {"registered": True, ...}

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

Methodology originally researched in `docs/CONVERSATION_LOG.md` (2026-03-16 session). The earlier `~/jefs-client/jefs_client.py` was lost; this is the rebuild inside DataGod.
