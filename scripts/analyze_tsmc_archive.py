#!/usr/bin/env python3
"""Analyze locally-mirrored TSMC SEC archive for customer/partner mentions.

Once the data/ folder has all TSMC filings downloaded, this script:
1. Walks every file in data/0001046179/*/
2. Strips HTML to plaintext (cached per-file)
3. Searches for ~80 known chip-vendor / hyperscaler names (broader than the
   previous run's 50-pattern list)
4. Reports per-company hit count, date range, and a representative snippet
"""
from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "research" / "TSMC Chip Makers"
ARCHIVE = ROOT / "data" / "0001046179"
OUT_SUMMARY = ROOT / "tsmc_archive_partner_summary.csv"
OUT_DETAIL = ROOT / "tsmc_archive_partner_details.csv"

# Broader name list — includes acronyms (caught what the 6-K regex missed)
CANDIDATES: dict[str, list[str]] = {
    # Big chip designers
    "AAPL/Apple": [r"\bApple Inc\b", r"\bApple Computer\b"],
    "NVDA/NVIDIA": [r"\bNVIDIA\b", r"\bNvidia\b"],
    "AMD": [r"\bAdvanced Micro Devices\b", r"\bAMD,? Inc\b", r"\b(?<![A-Z])AMD(?![A-Z])\b"],
    "INTC/Intel": [r"\bIntel Corp", r"\bIntel,? Inc\b"],
    "QCOM/Qualcomm": [r"\bQualcomm\b", r"\bQUALCOMM\b"],
    "AVGO/Broadcom": [r"\bBroadcom\b"],
    "MRVL/Marvell": [r"\bMarvell\b"],
    "MediaTek": [r"\bMediaTek\b"],
    "TXN/Texas Instruments": [r"\bTexas Instruments\b"],
    "NXPI/NXP": [r"\bNXP\s+Semiconductors\b", r"\bNXP\s+B\.?V\.?\b"],
    "ADI/Analog Devices": [r"\bAnalog Devices\b"],
    "MCHP/Microchip": [r"\bMicrochip Technology\b"],
    "ON/onsemi": [r"\bON Semiconductor\b", r"\bonsemi\b"],
    "MU/Micron": [r"\bMicron Technology\b"],
    "STM/STMicro": [r"\bSTMicroelectronics\b"],
    "Infineon": [r"\bInfineon\b"],
    "Renesas": [r"\bRenesas\b"],
    "SKHynix": [r"\bSK Hynix\b"],
    "Samsung": [r"\bSamsung Electronics\b"],
    # Big tech / hyperscalers
    "AMZN/Amazon": [r"\bAmazon\.com\b", r"\bAmazon Web Services\b", r"\bAnnapurna\b"],
    "GOOGL/Alphabet": [r"\bAlphabet Inc\b", r"\bGoogle LLC\b"],
    "MSFT/Microsoft": [r"\bMicrosoft Corp"],
    "META/Meta": [r"\bMeta Platforms\b"],
    "TSLA/Tesla": [r"\bTesla,? Inc\b"],
    # Equipment / suppliers
    "ASML": [r"\bASML\b"],
    "AMAT/Applied Materials": [r"\bApplied Materials\b"],
    "LRCX/Lam Research": [r"\bLam Research\b"],
    "KLAC/KLA": [r"\bKLA Corp", r"\bKLA-Tencor\b"],
    "TEL/Tokyo Electron": [r"\bTokyo Electron\b"],
    "Photronics": [r"\bPhotronics\b"],
    # Networking / Comms
    "CSCO/Cisco": [r"\bCisco Systems\b", r"\bCisco,? Inc\b"],
    "ANET/Arista": [r"\bArista Networks\b"],
    # PCs / hardware
    "DELL/Dell": [r"\bDell Technologies\b", r"\bDell Inc\b"],
    "HPE": [r"\bHewlett Packard Enterprise\b"],
    "HPQ/HP": [r"\bHP Inc\b", r"\bHewlett-Packard\b"],
    "LNVGY/Lenovo": [r"\bLenovo\b"],
    # OSAT / packaging / foundries
    "AMKR/Amkor": [r"\bAmkor\b"],
    "ASE": [r"\bASE Technology\b", r"\bAdvanced Semiconductor Engineering\b"],
    "GlobalFoundries": [r"\bGlobalFoundries\b", r"\bGlobal Foundries\b"],
    "UMC": [r"\bUnited Microelectronics\b"],
    "SMIC": [r"\bSemiconductor Manufacturing International\b"],
    "Vanguard Intl Semi": [r"\bVanguard International Semiconductor\b"],
    # EDA / IP
    "SNPS/Synopsys": [r"\bSynopsys\b"],
    "CDNS/Cadence": [r"\bCadence Design\b"],
    "ARM": [r"\bArm Holdings\b", r"\bARM Holdings\b", r"\bArm Limited\b"],
    "Arteris": [r"\bArteris\b"],
    # Mfg / EMS partners
    "Foxconn/Hon Hai": [r"\bHon Hai\b", r"\bFoxconn\b"],
    "Pegatron": [r"\bPegatron\b"],
    "Quanta": [r"\bQuanta Computer\b"],
    "Wistron": [r"\bWistron\b"],
    # Other notable chip designers in our 33-row list
    "ALAB/Astera Labs": [r"\bAstera Labs\b"],
    "CRDO/Credo": [r"\bCredo Technology\b"],
    "SITM/SiTime": [r"\bSiTime\b"],
    "NVTS/Navitas": [r"\bNavitas Semiconductor\b"],
    "SLAB/Silicon Labs": [r"\bSilicon Labs\b", r"\bSilicon Laboratories\b"],
    "ALGM/Allegro": [r"\bAllegro MicroSystems\b"],
    "LSCC/Lattice": [r"\bLattice Semiconductor\b"],
    "MXL/MaxLinear": [r"\bMaxLinear\b"],
    "CRUS/Cirrus Logic": [r"\bCirrus Logic\b"],
    "AMBA/Ambarella": [r"\bAmbarella\b"],
    "AMBQ/Ambiq": [r"\bAmbiq Micro\b"],
    "MRAM/Everspin": [r"\bEverspin\b"],
    "GSIT/GSI Tech": [r"\bGSI Technology\b"],
    "INDI/indie Semi": [r"\bindie Semiconductor\b"],
    "Q/Qnity": [r"\bQnity Electronics\b"],
    # Auto / industrial
    "F/Ford": [r"\bFord Motor\b"],
    "GM": [r"\bGeneral Motors\b"],
    "Sony": [r"\bSony Semiconductor\b", r"\bSony Group\b"],
}


def html_to_text(html: str) -> str:
    text = re.sub(r"<script.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-z]+;", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return text


def main() -> int:
    if not ARCHIVE.exists():
        print(f"Archive not found: {ARCHIVE}")
        return 1

    # Compile patterns once
    compiled = {k: [re.compile(p) for p in pats] for k, pats in CANDIDATES.items()}

    files = list(ARCHIVE.rglob("*.txt")) + list(ARCHIVE.rglob("*.htm")) + list(ARCHIVE.rglob("*.html"))
    print(f"Files in archive: {len(files):,}")

    mentions: dict[str, list[tuple[str, str, str]]] = defaultdict(list)  # name -> [(filename, form, snippet)]
    seen_paths = 0
    for p in files:
        seen_paths += 1
        if seen_paths % 100 == 0:
            print(f"  [{seen_paths}/{len(files)}] processed", flush=True)
        # Form type inferred from parent directory name (e.g., 20-F, 6-K)
        form = p.parent.name if p.parent.name != "0001046179" else "?"
        try:
            raw = p.read_text(encoding="utf-8", errors="ignore")
            text = html_to_text(raw)
        except Exception:
            continue
        for name, patterns in compiled.items():
            for pat in patterns:
                m = pat.search(text)
                if m:
                    start = max(0, m.start() - 80)
                    end = min(len(text), m.end() + 100)
                    mentions[name].append((p.name, form, text[start:end].strip()))
                    break

    # Save summary
    print(f"\n=== Companies named in TSMC's local archive ({seen_paths} files) ===")
    print(f"{'Company':<28} {'Files':>6}  Forms")
    print("-" * 80)
    with open(OUT_SUMMARY, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["company", "files_mentioned", "forms"])
        for name, hits in sorted(mentions.items(), key=lambda x: -len(x[1])):
            forms = set(h[1] for h in hits)
            print(f"{name:<28} {len(hits):>6}  {','.join(sorted(forms))}")
            w.writerow([name, len(hits), "|".join(sorted(forms))])

    # Save details (capped per-company to avoid bloat)
    with open(OUT_DETAIL, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["company", "filename", "form", "snippet"])
        for name, hits in sorted(mentions.items(), key=lambda x: -len(x[1])):
            for filename, form, snippet in hits[:20]:
                w.writerow([name, filename, form, snippet[:300]])

    print(f"\nSaved summary: {OUT_SUMMARY}")
    print(f"Saved details: {OUT_DETAIL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
