#!/usr/bin/env python3
"""Growth-focused prediction model for our 55 TSMC clients.

Goal: identify **multibagger candidates** — small/mid-cap stocks with strong
fundamentals, momentum, and AI-tailwind exposure that could 2x–10x over 6-12 months.

Composite score weights small caps heavily (asymmetric upside) and AI tier (the
biggest macro tailwind). Mega-caps are penalized because they're already big —
they can grow but won't multibag.

Output:
  research/TSMC Chip Makers/stock_predictions.csv
"""

from __future__ import annotations

import csv
import warnings
from collections import Counter
from pathlib import Path

warnings.filterwarnings("ignore")
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent / "research" / "TSMC Chip Makers"
CUSTOMERS_CSV = ROOT / "data.csv"
SENATE_CSV = ROOT / "senate_trades_in_tsmc_customers.csv"
HOUSE_CSV = ROOT / "house_trades_in_tsmc_customers.csv"
OUT_CSV = ROOT / "stock_predictions.csv"

# ─── Verdict bands (growth-focused) ────────────────────────────────────────
VERDICT_BANDS = [
    (80, "10X CANDIDATE"),      # small-cap + momentum + AI tier — asymmetric multibagger
    (50, "2-3X GROWTH"),        # mid-cap, AI-exposed, accelerating
    (25, "STEADY GROWTH"),      # established but still appreciating
    (5,  "MILD UPSIDE"),
    (-15, "STAGNANT"),
    (-999, "AVOID"),
]

# Recommendation key → score
REC_SCORE = {
    "strong_buy": 15, "buy": 10, "hold": 0, "underperform": -5, "sell": -10, "strong_sell": -20,
    None: 0, "": 0, "none": 0,
}

# AI tier weight is heavier in growth model (biggest macro tailwind)
AI_TIER_SCORE = {
    "CORE": 25, "ENABLER": 20, "EDGE": 15, "AUX": 5, "AUX+EDGE": 10, "NONE": -10, "": 0,
}


def market_cap_band_score(mcap: float | None) -> tuple[int, str]:
    """Inverse-mcap bonus — small caps get the asymmetric-upside boost."""
    if not mcap or mcap <= 0:
        return 0, "unknown"
    b = mcap / 1e9  # in $B
    if b < 0.5:    return 25, "micro (<$500M)"     # 10× still plausible
    if b < 2:      return 20, "small ($0.5-2B)"
    if b < 10:     return 12, "small-mid ($2-10B)"
    if b < 50:     return 5,  "mid ($10-50B)"
    if b < 200:    return -2, "large ($50-200B)"
    if b < 1000:   return -8, "mega ($200B-1T)"    # very hard to multibag
    return -15, "trillion+ (>$1T)"                  # essentially impossible


def momentum_score(pct_1y: float, pct_30d: float, pct_6mo: float | None) -> tuple[float, str]:
    """Reward sustained + recent positive momentum. Penalize huge drops (could be broken)."""
    # 1y direction matters most for trend; 30d for continuation
    s = 0.0
    parts = []
    if pct_1y >= 300:    score_1y = 20; parts.append(f"+1y {pct_1y:.0f}% ramp")
    elif pct_1y >= 100:  score_1y = 15; parts.append(f"+1y {pct_1y:.0f}% strong")
    elif pct_1y >= 50:   score_1y = 10; parts.append(f"+1y {pct_1y:.0f}% solid")
    elif pct_1y >= 20:   score_1y = 5;  parts.append(f"+1y {pct_1y:.0f}% modest")
    elif pct_1y >= 0:    score_1y = 0
    elif pct_1y >= -20:  score_1y = -5;  parts.append(f"1y {pct_1y:.0f}% lagging")
    elif pct_1y >= -50:  score_1y = -10; parts.append(f"1y {pct_1y:.0f}% weak")
    else:                score_1y = -15; parts.append(f"1y {pct_1y:.0f}% broken")
    s += score_1y

    # 30d continuation
    if pct_30d >= 20:    s += 8;  parts.append(f"30d +{pct_30d:.0f}% accelerating")
    elif pct_30d >= 5:   s += 5
    elif pct_30d > -5:   s += 0
    elif pct_30d > -15:  s += -3
    else:                s += -6; parts.append(f"30d {pct_30d:.0f}% rolling over")

    # 6mo (if available)
    if pct_6mo is not None:
        if pct_6mo > 50 and pct_30d > 0:
            s += 5; parts.append(f"6mo +{pct_6mo:.0f}% (compounding)")

    return s, "; ".join(parts) if parts else "flat"


def valuation_score(pe: float | None, peg: float | None, fwd_pe: float | None,
                    rev_growth: float | None) -> tuple[float, str]:
    """PEG-weighted valuation; cheap-for-growth = bonus, nosebleed = penalty."""
    parts = []
    s = 0.0
    # PEG (forward P/E to growth)
    if peg is not None and peg > 0:
        if peg < 0.5:    s += 12; parts.append(f"PEG {peg:.2f} (cheap-growth)")
        elif peg < 1.0:  s += 8;  parts.append(f"PEG {peg:.2f} (fair)")
        elif peg < 2.0:  s += 0
        elif peg < 5.0:  s += -5; parts.append(f"PEG {peg:.2f} (rich)")
        else:            s += -10
    # Forward P/E (extreme penalty for nosebleed)
    if fwd_pe is not None and fwd_pe > 0:
        if fwd_pe > 80:   s += -10; parts.append(f"fwd P/E {fwd_pe:.0f} (extreme)")
        elif fwd_pe > 50: s += -3
        elif fwd_pe < 15: s += 3; parts.append(f"fwd P/E {fwd_pe:.1f} (cheap)")
    # Revenue growth is the growth-investor's primary metric
    if rev_growth is not None:
        if rev_growth > 1.0:    s += 15; parts.append(f"rev +{rev_growth*100:.0f}% YoY (hypergrowth)")
        elif rev_growth > 0.5:  s += 10; parts.append(f"rev +{rev_growth*100:.0f}% YoY")
        elif rev_growth > 0.2:  s += 5
        elif rev_growth < -0.1: s += -5; parts.append(f"rev {rev_growth*100:.0f}% (shrinking)")
    return s, "; ".join(parts) if parts else "n/a"


def fetch_fundamentals(ticker: str) -> dict:
    t = yf.Ticker(ticker)
    try:
        info = t.info or {}
    except Exception:
        info = {}
    # 6-month price change
    pct_6mo = None
    try:
        h = t.history(period="6mo")
        if len(h) > 1:
            pct_6mo = round((h["Close"].iloc[-1] / h["Close"].iloc[0] - 1) * 100, 1)
    except Exception:
        pass

    return {
        "market_cap": info.get("marketCap"),
        "current_price": info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose"),
        "target_mean": info.get("targetMeanPrice"),
        "target_high": info.get("targetHighPrice"),
        "target_low": info.get("targetLowPrice"),
        "num_analysts": info.get("numberOfAnalystOpinions"),
        "recommendation": info.get("recommendationKey"),
        "pe": info.get("trailingPE"),
        "fwd_pe": info.get("forwardPE"),
        "peg": info.get("pegRatio"),
        "beta": info.get("beta"),
        "profit_margin": info.get("profitMargins"),
        "roe": info.get("returnOnEquity"),
        "rev_growth": info.get("revenueGrowth"),
        "earnings_growth": info.get("earningsGrowth"),
        "pct_6mo": pct_6mo,
    }


def verdict_for(score: float) -> str:
    for threshold, label in VERDICT_BANDS:
        if score >= threshold:
            return label
    return "AVOID"


def load_political_counts() -> tuple[Counter, Counter]:
    senate = Counter()
    if SENATE_CSV.exists():
        for r in csv.DictReader(SENATE_CSV.open()):
            senate[r.get("ticker", "")] += 1
    house = Counter()
    if HOUSE_CSV.exists():
        for r in csv.DictReader(HOUSE_CSV.open()):
            house[r.get("ticker", "")] += 1
    return senate, house


def projected_multiplier(score: float, mcap_band_name: str) -> str:
    """Rough multibagger projection — heuristic only, not a forecast."""
    if score >= 80 and "micro" in mcap_band_name:
        return "5-10×"
    if score >= 80 and "small" in mcap_band_name:
        return "3-5×"
    if score >= 60:
        return "2-3×"
    if score >= 40:
        return "1.5-2×"
    if score >= 20:
        return "1.2-1.5×"
    if score >= 0:
        return "~1× (sideways)"
    return "downside risk"


def narrative(row: dict, fund: dict, mcap_band: str, score: float, verdict: str,
              multiplier: str) -> str:
    cp = fund.get("current_price")
    tg = fund.get("target_mean")
    upside = ""
    if cp and tg and cp > 0:
        upside = f", consensus target ${tg:.2f} ({(tg/cp-1)*100:+.0f}%)"
    rev_g = fund.get("rev_growth")
    rev_s = f", rev {rev_g*100:+.0f}% YoY" if rev_g is not None else ""
    return (f"{row['company']} ({row['ticker']}) — **{verdict}** | projection: {multiplier} "
            f"| {mcap_band} | tier: {row.get('ai_tier','?')} "
            f"| 1y {row.get('change_1y_pct','?')}%, 6mo {fund.get('pct_6mo','?')}%, 30d {row.get('change_30d_pct','?')}% "
            f"{rev_s}{upside}")


def main() -> int:
    customers = list(csv.DictReader(CUSTOMERS_CSV.open()))
    # Focus on customers (skip suppliers, peers, etc. for prediction)
    growth_universe = [r for r in customers
                       if r.get("relationship") in ("customer", "indirect_customer")]
    print(f"Universe: {len(growth_universe)} growth-eligible names")

    senate, house = load_political_counts()
    results = []
    for i, row in enumerate(growth_universe, 1):
        ticker = row["ticker"]
        print(f"  [{i}/{len(growth_universe)}] {ticker} …", flush=True)
        fund = fetch_fundamentals(ticker)
        mcap = fund.get("market_cap")
        mcap_pts, mcap_band = market_cap_band_score(mcap)
        try:
            pct_1y = float(row.get("change_1y_pct") or 0)
            pct_30d = float(row.get("change_30d_pct") or 0)
        except ValueError:
            pct_1y = pct_30d = 0
        mom_pts, mom_log = momentum_score(pct_1y, pct_30d, fund.get("pct_6mo"))
        val_pts, val_log = valuation_score(
            fund.get("pe"), fund.get("peg"), fund.get("fwd_pe"), fund.get("rev_growth")
        )
        rec_pts = REC_SCORE.get((fund.get("recommendation") or "").lower(), 0)
        # Analyst upside cap
        upside_pts = 0
        cp, tg = fund.get("current_price"), fund.get("target_mean")
        if cp and tg and cp > 0:
            upside_pts = max(-15, min(25, (tg - cp) / cp * 50))
        tier_pts = AI_TIER_SCORE.get((row.get("ai_tier") or "").strip(), 0)
        sen_n = senate.get(ticker.split(".")[0], 0)
        house_n = house.get(ticker.split(".")[0], 0)
        pol_pts = min(5, sen_n * 0.05 + house_n * 0.3)

        score = mcap_pts + mom_pts + val_pts + rec_pts + upside_pts + tier_pts + pol_pts
        score = round(score, 1)
        verdict = verdict_for(score)
        multiplier = projected_multiplier(score, mcap_band)

        signals = (f"cap={mcap_pts:+}({mcap_band}); momentum={mom_pts:+.0f}[{mom_log}]; "
                   f"valuation={val_pts:+.0f}[{val_log}]; rec={rec_pts:+}; "
                   f"analyst_upside={upside_pts:+.0f}; AI_tier={tier_pts:+}({row.get('ai_tier','')}); "
                   f"political={pol_pts:+.1f}")

        results.append({
            "rank": "",
            "ticker": ticker,
            "company": row["company"],
            "mcap_band": mcap_band,
            "market_cap": mcap,
            "current_price": cp,
            "ai_tier": row.get("ai_tier", ""),
            "relationship": row.get("relationship", ""),
            "tsmc_use": row.get("tsmc_use", "")[:60],
            "change_30d_pct": row.get("change_30d_pct"),
            "change_6mo_pct": fund.get("pct_6mo"),
            "change_1y_pct": row.get("change_1y_pct"),
            "pe": fund.get("pe"),
            "fwd_pe": fund.get("fwd_pe"),
            "peg": fund.get("peg"),
            "rev_growth_yoy": fund.get("rev_growth"),
            "profit_margin": fund.get("profit_margin"),
            "roe": fund.get("roe"),
            "analyst_target": fund.get("target_mean"),
            "analyst_high": fund.get("target_high"),
            "analyst_low": fund.get("target_low"),
            "analyst_upside_pct": round((tg / cp - 1) * 100, 1) if cp and tg and cp > 0 else None,
            "num_analysts": fund.get("num_analysts"),
            "recommendation": fund.get("recommendation"),
            "senate_trades": sen_n,
            "house_trades": house_n,
            "score": score,
            "verdict": verdict,
            "projected_multiplier": multiplier,
            "signals": signals,
            "narrative": narrative(row, fund, mcap_band, score, verdict, multiplier),
        })

    # Sort by score desc
    results.sort(key=lambda r: -float(r["score"]))
    for i, r in enumerate(results, 1):
        r["rank"] = i

    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)
    print(f"\nSaved: {OUT_CSV}")

    # Summary
    from collections import Counter as C
    vcounts = C(r["verdict"] for r in results)
    print(f"\nVerdict counts:")
    for v in ["10X CANDIDATE", "2-3X GROWTH", "STEADY GROWTH", "MILD UPSIDE", "STAGNANT", "AVOID"]:
        print(f"  {v:<18}  {vcounts.get(v, 0)}")

    print(f"\n=== Top 20 by growth score (multiplication candidates) ===")
    print(f"  {'#':>2} {'Ticker':<8} {'Score':>6} {'Mult':<8} {'Verdict':<16} {'Mcap band':<22} {'Tier':<6}  {'Company'}")
    print("-" * 110)
    for r in results[:20]:
        mb = (r["market_cap"] or 0) / 1e9
        print(f"  {r['rank']:>2} {r['ticker']:<8} {r['score']:>6} {r['projected_multiplier']:<8} {r['verdict']:<16} {r['mcap_band']:<22} {r['ai_tier']:<6}  {r['company']}")

    # Specifically show small-caps separately
    print(f"\n=== Sub-$5B growth candidates ===")
    small = [r for r in results if (r["market_cap"] or 0) < 5e9]
    small.sort(key=lambda r: -float(r["score"]))
    print(f"  {'Ticker':<8} {'Mcap':>10} {'Score':>6} {'Mult':<8}  Company / driver")
    print("-" * 95)
    for r in small[:15]:
        mb = (r["market_cap"] or 0) / 1e9
        print(f"  {r['ticker']:<8} ${mb:>8.1f}B {r['score']:>6} {r['projected_multiplier']:<8}  {r['company']} — {r['tsmc_use'][:50]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
