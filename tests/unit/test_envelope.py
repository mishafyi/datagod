"""ResponseEnvelopeMiddleware: status mapping, framework errors, headers, redaction."""

import httpx2
import pytest

from app.middleware import envelope


@pytest.mark.parametrize(("upstream_status", "http_status"), [
    (400, 400), (404, 404), (429, 429), (500, 502), (503, 502), (0, 502), ("junk", 502),
])
def test_error_dict_status_mapping(upstream_status, http_status):
    data = {"error": True, "source": "x", "upstream_status": upstream_status, "message": "m"}
    wrapped, status = envelope("/fred/GDP", data, 200)
    assert status == http_status
    assert wrapped["meta"] == {**wrapped["meta"], "source": "fred", "status": "error"}
    assert wrapped["error"] == "m"


def test_success_keeps_status_and_payload():
    wrapped, status = envelope("/usgs/earthquakes", {"features": []}, 200)
    assert status == 200 and wrapped["meta"]["status"] == "success"
    assert wrapped["data"] == {"features": []} and wrapped["error"] is None


def test_envelope_redacts_credentials_in_any_error_message():
    data = {"error": True, "source": "x", "upstream_status": 0,
            "message": "ConnectError for https://api.eia.gov/v2/?api_key=hunter2"}
    wrapped, _ = envelope("/eia", data, 200)
    assert "hunter2" not in wrapped["error"] and "hunter2" not in wrapped["data"]["message"]


def test_validation_error_is_an_error_envelope(api):
    r = api.get("/fred/GDP", params={"limit": "abc"})
    assert r.status_code == 422
    body = r.json()
    assert body["meta"]["status"] == "error"
    assert body["error"].startswith("query.limit:")


def test_unknown_route_is_an_error_envelope(api):
    r = api.get("/no/such/route")
    assert r.status_code == 404
    assert r.json()["meta"]["status"] == "error" and r.json()["error"] == "Not Found"


def test_method_not_allowed_keeps_allow_header(api):
    r = api.delete("/health")
    assert r.status_code == 405
    assert r.headers["allow"] == "GET"
    assert r.json()["meta"]["status"] == "error"


def test_upstream_4xx_passes_through_and_5xx_becomes_502(api, upstream):
    upstream.add("https://api.fda.gov/drug/event", httpx2.Response(404, json={"error": {"code": "NOT_FOUND"}}))
    upstream.add("https://api.fda.gov/drug/enforcement", httpx2.Response(500, text="boom"))
    assert api.get("/fda/drug-events").status_code == 404
    r = api.get("/fda/drug-recalls")
    assert r.status_code == 502 and r.json()["meta"]["status"] == "error"


def test_non_json_upstream_body_is_a_named_error(api, upstream):
    upstream.add("https://api.fda.gov/", httpx2.Response(200, text="<html>maintenance</html>",
                                                        headers={"content-type": "text/html"}))
    r = api.get("/fda/food-recalls")
    assert r.status_code == 502
    assert r.json()["error"].startswith("Non-JSON response (text/html)")


def test_raw_bytes_routes_are_not_wrapped(api, upstream):
    upstream.add("https://disclosures-clerk.house.gov/", httpx2.Response(
        200, content=b"%PDF-1.7 ...", headers={"content-type": "application/pdf"}))
    r = api.get("/house-disclosures/pdf", params={"path": "public_disc/ptr-pdfs/2024/1.pdf"})
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    assert r.headers["content-type"] == "application/pdf"


def test_unhandled_exception_is_a_500_envelope(api, monkeypatch):
    from fastapi.testclient import TestClient

    from app.clients import fred
    from app.main import app

    async def boom(*args, **kwargs):
        raise RuntimeError("bug")

    monkeypatch.setattr(fred, "series_info", boom)
    with TestClient(app, headers={"X-API-Key": api.headers["X-API-Key"]},
                    raise_server_exceptions=False) as client:
        r = client.get("/fred/series/GDP")
    assert r.status_code == 500
    assert r.json()["meta"]["status"] == "error"
    assert r.json()["error"] == "Internal error (RuntimeError)"
