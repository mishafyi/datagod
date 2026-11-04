"""Load environment config for all API keys."""

import os
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


def _env(name: str, default: str = "") -> str:
    """`name` from the environment; blank or whitespace-only counts as unset.

    `os.getenv(name, default)` only falls back when the variable is absent, so a
    `.env` line like `FEC_API_KEY=` (or an empty Coolify variable) used to send
    an empty key instead of the documented DEMO_KEY fallback.
    """
    return (os.getenv(name) or "").strip() or default


class Config:
    # DataGod — this service's own API key (gates every endpoint; set in env / Coolify)
    DATAGOD_API_KEY = _env("DATAGOD_API_KEY")

    # Interactive docs (/docs, /redoc, /openapi.json) — HTTP Basic auth.
    # Password falls back to DATAGOD_API_KEY when DATAGOD_DOCS_PASSWORD is unset.
    DATAGOD_DOCS_USER = _env("DATAGOD_DOCS_USER", "datagod")
    DATAGOD_DOCS_PASSWORD = _env("DATAGOD_DOCS_PASSWORD")

    # SEC EDGAR
    SEC_USER_AGENT = _env("SEC_USER_AGENT")

    # FRED
    FRED_API_KEY = _env("FRED_API_KEY")

    # FEC
    FEC_API_KEY = _env("FEC_API_KEY", "DEMO_KEY")

    # Congress.gov
    CONGRESS_API_KEY = _env("CONGRESS_API_KEY", "DEMO_KEY")

    # EIA
    EIA_API_KEY = _env("EIA_API_KEY", "DEMO_KEY")

    # Census
    CENSUS_API_KEY = _env("CENSUS_API_KEY")

    # BLS
    BLS_API_KEY = _env("BLS_API_KEY")

    # SAM.gov
    SAM_API_KEY = _env("SAM_API_KEY")

    # data.gov
    DATAGOV_API_KEY = _env("DATAGOV_API_KEY")

    # Smithsonian Open Access (EDAN) — api.data.gov key; DEMO_KEY works at low limits
    SMITHSONIAN_API_KEY = _env("SMITHSONIAN_API_KEY", "DEMO_KEY")

    # UCDP — Uppsala Conflict Data Program. The API was keyless until 2026; upstream
    # now requires a free access token (register at ucdp.uu.se) sent as the
    # x-ucdp-access-token header. Empty => request goes keyless and upstream 401s.
    UCDP_ACCESS_TOKEN = _env("UCDP_ACCESS_TOKEN")

    # NewsNow — self-hosted trending-boards aggregator (github.com/ourongxing/newsnow).
    # Base URL of the instance, e.g. http://newsnow:4444 (Coolify-internal) — required for /trending.
    NEWSNOW_BASE_URL = _env("NEWSNOW_BASE_URL").rstrip("/")


cfg = Config()

# Settings whose values must never reach an API caller. Several upstreams take
# their key as a query parameter, so a failed call's URL carries it.
_SECRET_SETTINGS = (
    "DATAGOD_API_KEY", "DATAGOD_DOCS_PASSWORD", "FRED_API_KEY", "FEC_API_KEY",
    "CONGRESS_API_KEY", "EIA_API_KEY", "CENSUS_API_KEY", "BLS_API_KEY",
    "SAM_API_KEY", "DATAGOV_API_KEY", "SMITHSONIAN_API_KEY", "UCDP_ACCESS_TOKEN",
)
# Query parameters that carry credentials (api_key=, key=, registrationkey=, …).
_SECRET_PARAM = re.compile(
    r"(?i)\b(api_key|apikey|key|registrationkey|token|access_token)=[^&#\s'\"]+")


def redact(text: str) -> str:
    """`text` with credential query parameters and every configured secret masked."""
    text = _SECRET_PARAM.sub(r"\1=***", text)
    for name in _SECRET_SETTINGS:
        secret = getattr(cfg, name)
        if len(secret) >= 4 and secret != "DEMO_KEY":
            text = text.replace(secret, "***")
    return text
