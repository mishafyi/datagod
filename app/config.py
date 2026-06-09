"""Load environment config for all API keys."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


class Config:
    # DataGod — this service's own API key (gates every endpoint; set in env / Coolify)
    DATAGOD_API_KEY = os.getenv("DATAGOD_API_KEY", "")

    # SEC EDGAR
    SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "")

    # FRED
    FRED_API_KEY = os.getenv("FRED_API_KEY", "")

    # FEC
    FEC_API_KEY = os.getenv("FEC_API_KEY", "DEMO_KEY")

    # Congress.gov
    CONGRESS_API_KEY = os.getenv("CONGRESS_API_KEY", "DEMO_KEY")

    # EIA
    EIA_API_KEY = os.getenv("EIA_API_KEY", "DEMO_KEY")

    # Census
    CENSUS_API_KEY = os.getenv("CENSUS_API_KEY", "")

    # BLS
    BLS_API_KEY = os.getenv("BLS_API_KEY", "")

    # SAM.gov
    SAM_API_KEY = os.getenv("SAM_API_KEY", "")

    # data.gov
    DATAGOV_API_KEY = os.getenv("DATAGOV_API_KEY", "")

    # Smithsonian Open Access (EDAN) — api.data.gov key; DEMO_KEY works at low limits
    SMITHSONIAN_API_KEY = os.getenv("SMITHSONIAN_API_KEY", "DEMO_KEY")


cfg = Config()
