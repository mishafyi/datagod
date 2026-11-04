#!/usr/bin/env python3
"""Comprehensive test suite for all EDGAR endpoints."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

BASE_URL = "http://localhost:8000"
API_KEY = os.getenv("DATAGOD_API_KEY", "")
# DataGod gates every endpoint behind the X-API-Key header (see app/auth.py).
HEADERS = {"X-API-Key": API_KEY}

# Test results storage
results = []


def log_test(endpoint, params, status, check):
    """Log a test result."""
    result = {
        "endpoint": endpoint,
        "params": params,
        "status": status,
        "check": check,
        "timestamp": datetime.now().isoformat()
    }
    results.append(result)
    status_icon = "✓" if status == "PASS" else "✗"
    print(f"{status_icon} {endpoint:40} | {params:50} | {check}")


async def test_edgar_company():
    """Test GET /edgar/company/{cik}"""
    print("\n=== Testing GET /edgar/company/{cik} ===")
    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:

        # Valid ticker tests
        for ticker in ["AAPL", "MSFT", "TSLA", "GOOG", "AMZN"]:
            try:
                resp = await client.get(f"{BASE_URL}/edgar/company/{ticker}")
                has_data = resp.status_code == 200 and "data" in resp.json()
                status = "PASS" if resp.status_code == 200 and has_data else "FAIL"
                log_test("/edgar/company/{cik}", f"ticker={ticker}", status,
                        f"Status: {resp.status_code}, Has data: {has_data}")
            except Exception as e:
                log_test("/edgar/company/{cik}", f"ticker={ticker}", "FAIL", str(e)[:50])

        # Valid CIK number tests
        for cik in ["320193", "789019", "0000320193"]:
            try:
                resp = await client.get(f"{BASE_URL}/edgar/company/{cik}")
                has_data = resp.status_code == 200 and "data" in resp.json()
                status = "PASS" if resp.status_code == 200 and has_data else "FAIL"
                log_test("/edgar/company/{cik}", f"cik={cik}", status,
                        f"Status: {resp.status_code}, Has data: {has_data}")
            except Exception as e:
                log_test("/edgar/company/{cik}", f"cik={cik}", "FAIL", str(e)[:50])

        # Invalid tests
        for invalid_input in ["ZZZZZZ", "999999999", ""]:
            try:
                endpoint = f"{BASE_URL}/edgar/company/{invalid_input}" if invalid_input else f"{BASE_URL}/edgar/company/"
                if not invalid_input:
                    resp = await client.get(f"{BASE_URL}/edgar/company/")
                else:
                    resp = await client.get(endpoint)
                has_error = resp.status_code != 200 or "error" in resp.json().get("data", {})
                status = "PASS" if (resp.status_code != 200 or has_error) else "FAIL"
                log_test("/edgar/company/{cik}", f"invalid={invalid_input or 'empty'}", status,
                        f"Status: {resp.status_code}, Properly rejected: {has_error}")
            except Exception as e:
                log_test("/edgar/company/{cik}", f"invalid={invalid_input or 'empty'}", "PASS",
                        f"Properly errored: {type(e).__name__}")


async def test_edgar_financials():
    """Test GET /edgar/financials/{cik}"""
    print("\n=== Testing GET /edgar/financials/{cik} ===")
    async with httpx.AsyncClient(timeout=60, headers=HEADERS) as client:

        for ticker in ["AAPL", "MSFT"]:
            try:
                resp = await client.get(f"{BASE_URL}/edgar/financials/{ticker}")
                has_data = resp.status_code == 200 and "data" in resp.json()
                status = "PASS" if resp.status_code == 200 and has_data else "FAIL"
                data_size = len(str(resp.json())) if resp.status_code == 200 else 0
                log_test("/edgar/financials/{cik}", f"{ticker}", status,
                        f"Status: {resp.status_code}, Data size: {data_size:,} chars")
            except Exception as e:
                log_test("/edgar/financials/{cik}", f"{ticker}", "FAIL", str(e)[:50])


async def test_edgar_concept():
    """Test GET /edgar/concept/{cik}/{concept}"""
    print("\n=== Testing GET /edgar/concept/{cik}/{concept} ===")
    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:

        # Valid concept tests
        for cik, concept in [("AAPL", "Revenues"), ("AAPL", "NetIncomeLoss"), ("AAPL", "Assets")]:
            try:
                resp = await client.get(f"{BASE_URL}/edgar/concept/{cik}/{concept}")
                has_data = resp.status_code == 200 and "data" in resp.json()
                status = "PASS" if resp.status_code == 200 and has_data else "FAIL"
                log_test("/edgar/concept/{cik}/{concept}", f"{cik}/{concept}", status,
                        f"Status: {resp.status_code}, Has data: {has_data}")
            except Exception as e:
                log_test("/edgar/concept/{cik}/{concept}", f"{cik}/{concept}", "FAIL", str(e)[:50])

        # Invalid concept test
        try:
            resp = await client.get(f"{BASE_URL}/edgar/concept/AAPL/InvalidConcept")
            has_error = resp.status_code != 200 or "error" in resp.json().get("data", {})
            status = "PASS" if (resp.status_code != 200 or has_error) else "FAIL"
            log_test("/edgar/concept/{cik}/{concept}", "AAPL/InvalidConcept", status,
                    f"Status: {resp.status_code}, Properly rejected: {has_error}")
        except Exception:
            log_test("/edgar/concept/{cik}/{concept}", "AAPL/InvalidConcept", "PASS",
                    "Properly errored")

        # Taxonomy parameter tests — a concept exists in one taxonomy only; SEC's 404
        # for the wrong one must pass through as 404.
        for concept, taxonomy, expected in [("Revenues", "us-gaap", 200),
                                            ("EntityCommonStockSharesOutstanding", "dei", 200),
                                            ("Revenues", "dei", 404)]:
            label = f"AAPL/{concept}?taxonomy={taxonomy}"
            try:
                resp = await client.get(f"{BASE_URL}/edgar/concept/AAPL/{concept}?taxonomy={taxonomy}")
                status = "PASS" if resp.status_code == expected and "data" in resp.json() else "FAIL"
                log_test("/edgar/concept/{cik}/{concept}", label, status,
                        f"Status: {resp.status_code} (want {expected})")
            except Exception as e:
                log_test("/edgar/concept/{cik}/{concept}", label, "FAIL", str(e)[:50])


async def test_edgar_frames():
    """Test GET /edgar/frames/{concept}"""
    print("\n=== Testing GET /edgar/frames/{concept} ===")
    async with httpx.AsyncClient(timeout=60, headers=HEADERS) as client:

        # Period tests. Balance-sheet (instant) concepts like Assets exist only for
        # instant periods (the trailing "I"); a duration period is SEC's 404.
        for concept, period, expected in [("Revenues", "CY2023", 200), ("Revenues", "CY2023Q4I", 200),
                                          ("NetIncomeLoss", "CY2023", 200),
                                          ("NetIncomeLoss", "CY2023Q4I", 200),
                                          ("Assets", "CY2023Q4I", 200), ("Assets", "CY2023", 404)]:
            label = f"{concept}?period={period}"
            try:
                resp = await client.get(f"{BASE_URL}/edgar/frames/{concept}?period={period}")
                status = "PASS" if resp.status_code == expected and "data" in resp.json() else "FAIL"
                log_test("/edgar/frames/{concept}", label, status,
                        f"Status: {resp.status_code} (want {expected})")
            except Exception as e:
                log_test("/edgar/frames/{concept}", label, "FAIL", str(e)[:50])

        # Unit tests — each concept is reported in its own unit; a mismatched unit is a 404.
        for query, expected in [("Revenues?unit=USD&period=CY2023", 200),
                                ("EarningsPerShareBasic?unit=USD-per-shares&period=CY2023", 200),
                                ("EntityCommonStockSharesOutstanding?taxonomy=dei&unit=shares&period=CY2023Q4I", 200),
                                ("Revenues?unit=shares&period=CY2023", 404)]:
            try:
                resp = await client.get(f"{BASE_URL}/edgar/frames/{query}")
                status = "PASS" if resp.status_code == expected and "data" in resp.json() else "FAIL"
                log_test("/edgar/frames/{concept}", query, status,
                        f"Status: {resp.status_code} (want {expected})")
            except Exception as e:
                log_test("/edgar/frames/{concept}", query, "FAIL", str(e)[:50])

        # Invalid period test
        try:
            resp = await client.get(f"{BASE_URL}/edgar/frames/Revenues?period=CY9999")
            has_error = resp.status_code != 200 or "error" in resp.json().get("data", {})
            status = "PASS" if (resp.status_code != 200 or has_error) else "FAIL"
            log_test("/edgar/frames/{concept}", "Revenues?period=CY9999", status,
                    f"Status: {resp.status_code}, Properly rejected: {has_error}")
        except Exception:
            log_test("/edgar/frames/{concept}", "Revenues?period=CY9999", "PASS",
                    "Properly errored")


async def test_edgar_search():
    """Test GET /edgar/search"""
    print("\n=== Testing GET /edgar/search ===")
    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:

        # Valid search tests
        for query, forms in [
            ("artificial+intelligence", "10-K"),
            ("climate+risk", "10-Q"),
            ("technology", "")
        ]:
            try:
                params = {"q": query, "forms": forms} if forms else {"q": query}
                resp = await client.get(f"{BASE_URL}/edgar/search", params=params)
                has_data = resp.status_code == 200 and "data" in resp.json()
                status = "PASS" if resp.status_code == 200 and has_data else "FAIL"
                log_test("/edgar/search", f"q={query}&forms={forms or 'any'}", status,
                        f"Status: {resp.status_code}, Has data: {has_data}")
            except Exception as e:
                log_test("/edgar/search", f"q={query}&forms={forms or 'any'}", "FAIL", str(e)[:50])

        # Limit parameter tests
        for limit in [1, 50]:
            try:
                resp = await client.get(f"{BASE_URL}/edgar/search", params={"q": "artificial+intelligence", "limit": limit})
                has_data = resp.status_code == 200 and "data" in resp.json()
                status = "PASS" if resp.status_code == 200 and has_data else "FAIL"
                log_test("/edgar/search", f"q=artificial+intelligence&limit={limit}", status,
                        f"Status: {resp.status_code}, Has data: {has_data}")
            except Exception as e:
                log_test("/edgar/search", f"q=artificial+intelligence&limit={limit}", "FAIL", str(e)[:50])

        # Empty query test
        try:
            resp = await client.get(f"{BASE_URL}/edgar/search", params={"q": ""})
            has_error = resp.status_code != 200 or "error" in resp.json().get("data", {})
            status = "PASS" if (resp.status_code != 200 or has_error) else "FAIL"
            log_test("/edgar/search", "q=&forms=", status,
                    f"Status: {resp.status_code}, Properly rejected: {has_error}")
        except Exception:
            log_test("/edgar/search", "q=&forms=", "PASS", "Properly errored")


async def main():
    """Run all tests."""
    print("=" * 120)
    print("EDGAR ENDPOINT COMPREHENSIVE TEST SUITE")
    print("=" * 120)

    await test_edgar_company()
    await test_edgar_financials()
    await test_edgar_concept()
    await test_edgar_frames()
    await test_edgar_search()

    # Summary
    print("\n" + "=" * 120)
    print("TEST SUMMARY")
    print("=" * 120)

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    total = len(results)

    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {passed/total*100:.1f}%")

    # Write detailed results to file
    out = Path(__file__).parent / "reports" / "edgar_test_results.json"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results saved to {out}")

    # Return exit code
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    import asyncio
    sys.exit(asyncio.run(main()))
