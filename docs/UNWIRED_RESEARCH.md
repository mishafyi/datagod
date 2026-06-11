---
name: unwired-research
description: "Researched US-gov APIs NOT yet wired into DataGod (no client module, no route): SAM.gov (federal contracting opportunities, entity registration, exclusions, wage determinations) and PatentsView (USPTO patents, inventors, assignees). Reference for future wiring."
keywords: "SAM.gov, federal contracting, RFP, bids, opportunities, entity registration, UEI, exclusions, debarred, wage determinations, PatentsView, patents, USPTO, inventors, assignees, citations, not wired"
routes: "(none — not exposed by DataGod)"
---

# Unwired research — APIs not yet exposed by DataGod

These US-government APIs were researched but are **not** wired into DataGod (no client
module, no route). Kept as a reference for future wiring. Every *wired* source now has
its own per-source doc — see `docs/API_GUIDE.md` (the router) and `docs/<SOURCE>.md`.

## SAM.gov — System for Award Management

**What:** Federal contracting opportunities (RFPs/bids), entity registrations, wage determinations, exclusions.

**Auth:** Free key from https://sam.gov/content/entity-information (DEMO_KEY does NOT work)

**Endpoints:**

```bash
# Search contracting opportunities
curl -s "https://api.sam.gov/opportunities/v2/search?api_key=YOUR_KEY&limit=5&postedFrom=01/01/2026&postedTo=03/16/2026"

# Entity (company) information
curl -s "https://api.sam.gov/entity-information/v3/entities?api_key=YOUR_KEY&ueiSAM=ENTITY_UEI"

# Exclusions (debarred entities)
curl -s "https://api.sam.gov/entity-information/v3/exclusions?api_key=YOUR_KEY&limit=5"

# Wage determinations
curl -s "https://api.sam.gov/wage-determination/v1/sca?api_key=YOUR_KEY"
```

## PatentsView — USPTO Patent Analytics

**What:** Patent data — inventors, assignees, citations, classifications, claims. Searchable and filterable.

**Auth:** Free key from https://patentsview.org/apis/purpose

**Endpoints:**

```bash
# Search patents (new v1 API)
curl -s "https://search.patentsview.org/api/v1/patent/?q={\"_gte\":{\"patent_date\":\"2024-01-01\"}}&f=patent_id,patent_title,patent_date&per_page=5" \
  -H "X-Api-Key: YOUR_KEY"

# Search by assignee (company)
curl -s "https://search.patentsview.org/api/v1/patent/?q={\"assignee_organization\":\"Apple Inc.\"}&f=patent_id,patent_title,patent_date&per_page=5" \
  -H "X-Api-Key: YOUR_KEY"

# Inventor search
curl -s "https://search.patentsview.org/api/v1/inventor/?q={\"inventor_last_name\":\"Musk\"}&f=inventor_first_name,inventor_last_name&per_page=5" \
  -H "X-Api-Key: YOUR_KEY"
```

**Note:** Legacy `api.patentsview.org` POST endpoint is discontinued (returns 410). Use the new `search.patentsview.org/api/v1/` with an API key.
