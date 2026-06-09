#!/usr/bin/env python3
"""Add per-ticker AI/robotics-client-potential rating + likely-clients list to data.csv.

Score interpretation:
  5 = ALREADY a confirmed client of an AI lab / robotics company at scale
  4 = HIGH probability — product directly fits AI/robotics demand
  3 = MEDIUM — adjacent product or indirect via partners
  2 = LOW — niche / unrelated to AI/robotics direct demand
  1 = N/A or INDIRECT — equipment/material/bond holding, not selling to AI labs directly
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "research" / "TSMC Chip Makers"
DATA = ROOT / "data.csv"

# (ticker → (score, likely_clients_csv))
# Based on product category, existing customer relationships, AI-stack position
MAP: dict[str, tuple[int, str]] = {
    # ── Mega-cap AI compute (already deeply embedded) ──
    "NVDA":    (5, "OpenAI, Anthropic, xAI, Meta, Microsoft, Google, Tesla, AWS — every AI lab + every robotics co"),
    "AMD":     (5, "Microsoft (MI300X), Meta, Oracle, OpenAI (announced MI400 commitment), AWS"),
    "AVGO":    (5, "Google (TPU v6+), Meta (MTIA-2/3), AWS, ByteDance (custom ASICs)"),
    "MRVL":    (5, "AWS (Trainium 2/3 partnership), Anthropic via AWS, hyperscaler custom silicon"),
    "INTC":    (3, "DoD (defense AI), Microsoft (chiplet outsourcing), Anthropic (rumored Falcon Shores tape-out)"),
    "QCOM":    (4, "Tesla (Snapdragon Cockpit in cars), Samsung, Honda, Meta (XR), automotive Cruise"),
    "ARM":     (5, "Every AI chip designer — AWS Graviton/Trainium, Microsoft Cobalt, Nvidia Grace, Apple Silicon, Anthropic/OpenAI via cloud"),
    "IBM":     (3, "DoD/intel (mainframe AI), Anthropic (cloud partnership announced 2024), enterprise AI"),

    # ── AI rack infrastructure (CORE — already shipping into every AI cluster) ──
    "ALAB":    (5, "Microsoft, Google, Meta, AWS, Oracle — every NVL72 GPU rack needs ALAB retimers; xAI Colossus"),
    "CRDO":    (5, "AWS, Meta, Microsoft, Google — 800G/1.6T ethernet AECs in every hyperscale AI cluster"),
    "SITM":    (5, "AWS, Google, Meta, Microsoft — precision MEMS clocks in every AI NIC/retimer/HBM stack"),
    "MXL":     (4, "AWS, Microsoft, Google — optical DSPs in 800G+ transceivers (CPO/co-packaged-optics roadmap)"),
    "NVTS":    (5, "NVIDIA (qualified into 800V power shelf), Microsoft Azure power, hyperscaler PSUs"),
    "AIP":     (5, "AWS (Trainium NoC), Meta (MTIA NoC), Tesla (Dojo), Microsoft, NVIDIA chiplet designs — IP licensed across nearly every chiplet AI design"),
    "LSCC":    (4, "Microsoft, Google, AWS — server-board BMC/sideband/secure-boot FPGAs (every AI server has one)"),

    # ── Memory (HBM thesis) ──
    "MU":      (5, "NVIDIA, AMD, AVGO — HBM3e/HBM4 in every AI accelerator. OpenAI/Anthropic indirect via NVDA"),

    # ── Auto / Humanoid robotics — sensor + actuator + perception ──
    "NXPI":    (5, "Tesla (S32 platform), Ford, GM, Volkswagen — auto MCU leader. Used in Figure, 1X, Apptronik humanoid controllers via tier-1"),
    "ALGM":    (5, "Tesla (motor drivers), Figure 02, 1X Neo, Apptronik Apollo, Boston Dynamics, Optimus — Hall/TMR sensors in every actuator"),
    "ADI":     (4, "Boston Dynamics IMUs, Tesla autopilot sensors, robotics signal chain — also AI-server power telemetry"),
    "AMBA":    (4, "Waymo (Cruise+Zoox alternates), Bosch (auto camera SoCs), surveillance/AI vision OEMs"),
    "INDI":    (4, "Bosch + tier-1 auto suppliers (Tesla competitors), ADAS sensor processors"),
    "STM":     (4, "Tesla, Bosch, Continental (auto IDM); STM32 in many robotics platforms; FD-SOI for AI inference"),
    "IFNNY":   (4, "Tesla power semi, Boston Dynamics, automotive AI tier-1, EV charging"),
    "RNECY":   (4, "Toyota, Honda, GM — auto MCU IDM. Humanoid robotics MCUs"),
    "APTV":    (4, "Tier-1 to Tesla competitors, ADAS controllers, zonal compute"),
    "MCHP":    (3, "Auto MCU + industrial. Some robotics use. PIC32 + dsPIC widely used in actuator control"),
    "MPWR":    (4, "NVIDIA AI accelerator boards (board-level power), hyperscaler PSU electronics, robotics power management"),

    # ── Edge AI / specialty ──
    "AMBQ":    (3, "Apple AirPods, Meta wearables — on-device speech-AI; some robotics tinyML"),
    "SLAB":    (2, "IoT wireless — tangential to AI labs; some smart-home + edge inference"),
    "CRUS":    (2, "Apple audio codecs — Apple Intelligence runs on AP, not Cirrus DSPs"),
    "HIMX":    (2, "Smart-glasses display drivers (Meta Ray-Ban Stories, Magic Leap), but secondary AI play"),
    "GSIT":    (3, "Gemini APU SRAM AI inference — niche; if adopted, used by edge-AI projects"),
    "QUIK":    (3, "eFPGA IP licensed to AI chip designers; EOS voice SoCs for hearables"),
    "MRAM":    (3, "Embedded MRAM at TSMC — could be in AI ASICs (AVGO custom, AWS Trainium possibly)"),

    # ── Niche / lower probability ──
    "GCTS":    (2, "5G RFICs — adjacent to AI-cloud delivery but not AI compute"),
    "MOBX":    (2, "Photonic interconnect — pitching CPO for AI clusters; execution-risk play"),
    "PRSO":    (2, "60 GHz mmWave PHY — niche, AR/VR-adjacent"),
    "THPTF":   (2, "Auto camera + security-cam SoCs — surveillance AI tangential"),

    # ── Apple's silicon — they're not a vendor to other AI labs ──
    "AAPL":    (3, "Apple Intelligence runs on own silicon; they're a buyer (NVDA, AMZN Trainium for backend ML) more than seller"),

    # ── Big tech companies (they're chip BUYERS not sellers — but they're 'clients' of TSMC for their own custom silicon) ──
    "AMZN":    (5, "Trainium 2/3 used by Anthropic, AWS customers; Annapurna designs AI ASICs at TSMC"),
    "MSFT":    (5, "Maia 100 used internally + by OpenAI partnership; Cobalt CPU for Azure"),
    "META":    (5, "MTIA-1/2 used internally for own AI training; partner Anthropic on Llama-era infra"),
    "TSLA":    (5, "Internal Dojo D2 + AI5 FSD chips at TSMC; xAI also uses NVDA + co-design with Tesla's silicon team"),
    "GOOGL":   (5, "TPU v6 (via AVGO at TSMC); Google DeepMind backbone — though GOOGL not in our data.csv"),

    # ── Networking ──
    "CSCO":    (4, "Silicon One in hyperscale AI cluster ethernet — Microsoft, Meta, Google all evaluate"),

    # ── PC / server OEMs ──
    "HPQ":     (3, "PCs containing TSMC chips — Anthropic/OpenAI etc. likely have HPE servers in their colos"),
    "HPE":     (3, "Server platforms for hyperscaler private cloud — some AI lab DC build outs"),
    "DELL":    (3, "Same as HPE — server-based AI infrastructure"),
    "SONY":    (4, "Sony Semiconductor CIS in Waymo LIDAR, Tesla cameras, drone/robotics cameras"),

    # ── MediaTek (TWSE) — broad mobile + cloud-AI inference ──
    "2454.TW": (4, "Cloud-edge AI inference; Anthropic-class on-device LLM (Dimensity 9400). Used in tablets, automotive"),

    # ── Equipment + EDA — sell to FOUNDRIES not AI labs (indirect) ──
    "AMAT":    (1, "Sells to TSMC + Intel + Samsung — AI labs are indirect end-users via fabs"),
    "ASML":    (1, "Same. EUV monopoly. Indirect via every TSMC customer"),
    "LRCX":    (1, "Same. Etch tools to fabs"),
    "KLAC":    (1, "Same. Yield inspection to fabs"),
    "CDNS":    (4, "Every AI chip designer (AWS, Google, Meta, AAPL, Tesla, NVIDIA) — licenses Cadence EDA tools"),
    "SNPS":    (4, "Every AI chip designer — licenses Synopsys EDA + IP cores (PCIe, USB, DDR)"),

    # ── Photomasks / materials ──
    "PLAB":    (1, "Sells photomasks to TSMC; AI labs are indirect end-users"),
    "Q":       (1, "Materials/chemicals to TSMC fab; indirect"),

    # ── OSAT / downstream ──
    "AMKR":    (3, "Packages AVGO custom AI silicon (Google TPU, Meta MTIA), AMD MI300, NVDA peripheral chiplets"),
    "TSEM":    (2, "Specialty analog foundry — minor AI exposure"),
    "GFS":     (3, "US foundry — DoD AI silicon, some edge-AI chips (Apple moved some chips here)"),
    "SMICY":   (1, "Chinese foundry — sanctioned from AI work due to US export controls"),

    # ── Mfg partners (assemble servers/devices) ──
    "HNHPF":   (4, "Foxconn assembles every NVIDIA HGX/DGX system + Apple devices + most hyperscaler servers"),
    "PGTRY":   (3, "Server/PC contract manufacturer — secondary scale"),
    "WSTNF":   (3, "Server ODM — direct AI server assembler for Microsoft/Meta/Amazon"),

    # ── TSMC subsidiary ──
    "VSCFY":   (2, "Mature-node analog/specialty — AI exposure indirect"),

    # ── Bond holdings — NOT chip relationships ──
    "F":       (1, "TSMC holds Ford bonds; Ford uses NXP/Renesas chips. No direct AI-supplier role."),
    "GM":      (1, "Same. Cruise (GM-owned) is AI-adjacent, but GM not selling to AI labs"),
}

rows = list(csv.DictReader(DATA.open()))
for r in rows:
    score, clients = MAP.get(r["ticker"], (None, ""))
    r["ai_client_score"] = str(score) if score is not None else "?"
    r["ai_client_likelihood"] = {
        5: "ALREADY",
        4: "HIGH",
        3: "MEDIUM",
        2: "LOW",
        1: "INDIRECT/NA",
    }.get(score, "?")
    r["likely_ai_clients"] = clients

cols = list(rows[0].keys())
with DATA.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)

from collections import Counter
print(f"Updated {len(rows)} rows in data.csv")
print(f"\nAI-client-likelihood distribution:")
band_counts = Counter(r["ai_client_likelihood"] for r in rows)
for band in ["ALREADY", "HIGH", "MEDIUM", "LOW", "INDIRECT/NA", "?"]:
    print(f"  {band:<14} {band_counts.get(band, 0)}")

# Sample by band
print(f"\nALREADY (score 5):")
for r in rows:
    if r["ai_client_likelihood"] == "ALREADY":
        print(f"  {r['ticker']:<7}  {r['company'][:25]:<26} → {r['likely_ai_clients'][:80]}")

print(f"\nHIGH (score 4):")
for r in rows:
    if r["ai_client_likelihood"] == "HIGH":
        print(f"  {r['ticker']:<7}  {r['company'][:25]:<26} → {r['likely_ai_clients'][:80]}")
