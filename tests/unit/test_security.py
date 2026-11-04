"""Credential redaction, the House-PDF SSRF guard, and API-key / docs auth."""

import httpx2
import pytest

from app.clients import _error, house_fd
from app.config import cfg, redact

pytestmark = pytest.mark.anyio


# ── secrets never reach the caller ──────────────────────────────────────

def test_redact_masks_credential_query_params():
    text = ("400 from https://x/api?series_id=GDP&api_key=abc123&file_type=json"
            " https://y/?key=k1&registrationkey=r2&token=t3")
    out = redact(text)
    for secret in ("abc123", "k1", "r2", "t3"):
        assert secret not in out
    assert "api_key=***" in out and "series_id=GDP" in out


def test_redact_masks_configured_secret_values_anywhere(monkeypatch):
    monkeypatch.setattr(cfg, "FRED_API_KEY", "s3cr3t-fred-value")
    assert redact("upstream echoed s3cr3t-fred-value in its body") == "upstream echoed *** in its body"


async def test_upstream_error_message_does_not_leak_api_key(upstream, monkeypatch):
    from app.clients import fred

    monkeypatch.setattr(cfg, "FRED_API_KEY", "real-fred-key-123")
    upstream.add("https://api.stlouisfed.org/", httpx2.Response(
        400, json={"error_code": 400, "error_message": "Bad Request. Series does not exist."}))
    err = await fred.get_series("NOPE")
    assert err["error"] is True and err["upstream_status"] == 400
    assert "real-fred-key-123" not in err["message"]
    assert "api_key=***" in err["message"]
    assert "Series does not exist" in err["message"]  # the upstream's own reason is kept


def test_error_message_is_never_empty():
    request = httpx2.Request("GET", "https://example.org/x?api_key=zzz")
    err = _error("src", httpx2.ReadTimeout("", request=request))
    assert err["upstream_status"] == 0
    assert err["message"].startswith("ReadTimeout for https://example.org/x")
    assert "zzz" not in err["message"]


# ── SSRF: /house-disclosures/pdf only fetches the disclosures host ──────

@pytest.mark.parametrize("path", [
    "public_disc/ptr-pdfs/2024/1.pdf",
    "/public_disc/ptr-pdfs/2024/1.pdf",
    "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2024/1.pdf",
    "http://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2024/1.pdf",
])
def test_pdf_url_accepts_disclosure_paths(path):
    assert house_fd._pdf_url(path) == "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2024/1.pdf"


@pytest.mark.parametrize("path", [
    "http://127.0.0.1:8000/health",
    "http://169.254.169.254/latest/meta-data/",
    "http://newsnow:4444/api/s?id=x",
    "//evil.example/x.pdf",
    "https://disclosures-clerk.house.gov@evil.example/x.pdf",
    "https://disclosures-clerk.house.gov:8443/x.pdf",
    "https://disclosures-clerk.house.gov.evil.example/x.pdf",
    "file:///etc/passwd",
])
def test_pdf_url_rejects_other_hosts(path):
    assert house_fd._pdf_url(path) is None


async def test_fetch_pdf_refuses_foreign_url_without_requesting_it(upstream):
    err = await house_fd.fetch_pdf("http://169.254.169.254/latest/meta-data/")
    assert err["error"] is True and err["upstream_status"] == 400
    assert upstream.requests == []


def test_pdf_route_returns_400_envelope_for_foreign_url(api, upstream):
    r = api.get("/house-disclosures/pdf", params={"path": "http://127.0.0.1:8000/health"})
    assert r.status_code == 400
    assert r.json()["meta"]["status"] == "error"
    assert upstream.requests == []


# ── API-key and docs auth ───────────────────────────────────────────────

def test_missing_and_wrong_keys_are_401(api):
    assert api.get("/fred", headers={"X-API-Key": ""}).status_code == 401
    assert api.get("/fred", headers={"X-API-Key": "wrong"}).status_code == 401


def test_non_ascii_key_is_401_not_500(api):
    # Starlette decodes header bytes as latin-1; compare_digest on non-ASCII str raised TypeError.
    r = api.get("/fred", headers={"X-API-Key": "café".encode()})
    assert r.status_code == 401
    assert r.json()["meta"]["status"] == "error"


def test_health_is_public_and_correct_key_passes(api):
    assert api.get("/health", headers={"X-API-Key": ""}).status_code == 200
    assert api.get("/fred").status_code == 200  # no q → static hint, no upstream call


def test_docs_need_basic_auth(api, monkeypatch):
    monkeypatch.setattr(cfg, "DATAGOD_DOCS_PASSWORD", "docs-pw")
    assert api.get("/openapi.json").status_code == 401
    assert api.get("/openapi.json", auth=("datagod", "wrong")).status_code == 401
    assert api.get("/openapi.json", auth=("datagod", "pässwörd")).status_code == 401
    assert api.get("/openapi.json", auth=("datagod", "docs-pw")).status_code == 200
