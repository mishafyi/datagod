#!/usr/bin/env python3
"""Download all 1,426 House PTR PDFs (2023-2025), extract transactions with pdfplumber,
cross-reference against the 55 TSMC clients in research/TSMC Chip Makers/data.csv."""

from __future__ import annotations

import csv
import io
import re
import time
import urllib.request
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parent.parent / "research" / "TSMC Chip Makers"
PTR_INDEX = ROOT / "house_ptr_filings_2023_2025.csv"
PDF_CACHE = ROOT / "house_ptr_pdfs"
OUT_ALL = ROOT / "house_ptrs_all_transactions.csv"
OUT_MATCH = ROOT / "house_trades_in_tsmc_customers.csv"

HEADERS = {"User-Agent": "Mozilla/5.0 (datagod research)"}

# Matches: "<OWNER> <Asset Name> (<TICKER>) [<TYPE>] <P/S/E> <date> <date> <amount>"
# Owner codes: SP / DC / JT / (blank for filer)
# Type codes in brackets: ST OP GS MF EF OL ...
# Tx type: P (Purchase), S (Sale), E (Exchange), can have (partial)
TXN_RE = re.compile(
    r"^(?P<owner>(?:SP|DC|JT|JT\s+SP|SP\s+DC|DC\s+SP|\s*)?)\s*"
    r"(?P<asset>.+?)\s*"
    r"\((?P<ticker>[A-Z]{1,6})\)\s*"
    r"(?:\[(?P<typecode>[A-Z]{2,3})\]\s*)?"
    r"(?P<txtype>[PSE](?:\s*\(partial\))?)\s+"
    r"(?P<tx_date>\d{1,2}/\d{1,2}/\d{4})\s+"
    r"(?P<notify_date>\d{1,2}/\d{1,2}/\d{4})\s+"
    r"\$(?P<amount_min>[\d,]+)\s*-\s*\$?(?P<amount_max>[\d,]+)",
    re.MULTILINE,
)
NAME_RE = re.compile(r"Name:\s+(.+?)(?=\n|$)")
DISTRICT_RE = re.compile(r"State/District:\s+(\S+)")


def parse_ptr(pdf_bytes: bytes) -> tuple[str, str, list[dict]]:
    """Return (filer, state_district, transactions[])."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join((page.extract_text() or "") for page in pdf.pages)
    filer_m = NAME_RE.search(text)
    state_m = DISTRICT_RE.search(text)
    filer = filer_m.group(1).strip() if filer_m else "?"
    state = state_m.group(1).strip() if state_m else ""
    txs: list[dict] = []
    for m in TXN_RE.finditer(text):
        txs.append({
            "filer": filer,
            "state_district": state,
            "owner": (m.group("owner") or "").strip(),
            "asset": m.group("asset").strip()[:120],
            "ticker": m.group("ticker"),
            "type_code": m.group("typecode") or "",
            "tx_type": m.group("txtype").strip(),
            "tx_date": m.group("tx_date"),
            "notify_date": m.group("notify_date"),
            "amount_min": m.group("amount_min").replace(",", ""),
            "amount_max": m.group("amount_max").replace(",", ""),
        })
    return filer, state, txs


def main() -> int:
    PDF_CACHE.mkdir(parents=True, exist_ok=True)

    # Load TSMC-customer tickers
    data_csv = ROOT / "data.csv"
    customers = list(csv.DictReader(data_csv.open()))
    customer_tickers = {r["ticker"].split(".")[0]: r["company"] for r in customers}
    print(f"Customer roster: {len(customer_tickers)} tickers")

    # Load PTR index
    ptrs = list(csv.DictReader(PTR_INDEX.open()))
    print(f"PTR index: {len(ptrs)} filings\n")

    all_txns: list[dict] = []
    matched_txns: list[dict] = []
    download_count = parsed_count = errors = 0
    start = time.time()

    for i, ptr in enumerate(ptrs, 1):
        if i % 50 == 0:
            elapsed = time.time() - start
            eta = elapsed / i * (len(ptrs) - i)
            print(f"  [{i}/{len(ptrs)}] | dl={download_count} | parsed={parsed_count} | txns={len(all_txns):,} | matched={len(matched_txns)} | eta {eta:.0f}s",
                  flush=True)
        doc_id = ptr["doc_id"]
        year = ptr["year"]
        if not doc_id:
            continue
        cache_path = PDF_CACHE / f"{year}_{doc_id}.pdf"
        if not cache_path.exists():
            try:
                req = urllib.request.Request(ptr["pdf_url"], headers=HEADERS)
                pdf_bytes = urllib.request.urlopen(req, timeout=30).read()
                cache_path.write_bytes(pdf_bytes)
                download_count += 1
                time.sleep(0.05)  # be polite
            except Exception as e:
                errors += 1
                continue
        try:
            pdf_bytes = cache_path.read_bytes()
            filer, state, txns = parse_ptr(pdf_bytes)
        except Exception as e:
            errors += 1
            continue
        parsed_count += 1
        for tx in txns:
            tx["doc_id"] = doc_id
            tx["year"] = year
            tx["pdf_url"] = ptr["pdf_url"]
            all_txns.append(tx)
            if tx["ticker"] in customer_tickers:
                tx2 = dict(tx)
                tx2["customer_company"] = customer_tickers[tx["ticker"]]
                matched_txns.append(tx2)

    # Save outputs
    fieldnames_all = ["doc_id","year","filer","state_district","owner","asset","ticker",
                      "type_code","tx_type","tx_date","notify_date","amount_min","amount_max","pdf_url"]
    with OUT_ALL.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames_all)
        w.writeheader()
        w.writerows(all_txns)

    fieldnames_match = ["ticker","customer_company"] + fieldnames_all
    with OUT_MATCH.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames_match)
        w.writeheader()
        w.writerows(matched_txns)

    elapsed = time.time() - start
    print(f"\nDone in {elapsed:.0f}s. parsed={parsed_count}, errors={errors}, "
          f"total txns={len(all_txns):,}, matched={len(matched_txns)}")
    print(f"Saved: {OUT_ALL.name} ({len(all_txns)} rows)")
    print(f"Saved: {OUT_MATCH.name} ({len(matched_txns)} rows)")

    # Top filers/tickers in our customer set
    from collections import Counter
    by_filer = Counter(t["filer"] for t in matched_txns)
    by_ticker = Counter(t["ticker"] for t in matched_txns)
    print(f"\nTop House traders by # of trades in our 55 customers:")
    for filer, n in by_filer.most_common(20):
        print(f"  {n:>4}  {filer}")
    print(f"\nMost-traded tickers (in our customer set):")
    for ticker, n in by_ticker.most_common(20):
        print(f"  {n:>4}  {ticker}  ({customer_tickers.get(ticker,'')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
