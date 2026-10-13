"""Extension 5 — Carbon-aware scheduling for interruptible jobs across all 5 regions.

Run: python bonus/extension_5_carbon_scheduling.py
Energy per job = GPU board watts (price_catalog.csv) x GPU-hours (workloads.csv).
Reads data only; writes outputs/extension_5_carbon_scheduling.csv
"""
from __future__ import annotations
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from missions._common import load_csv, num, catalog_by_type
from finops.sustainability import REGION_CARBON, REGION_PRICE_KWH, carbon_g, energy_cost_usd

BASE = "us-east-1"


def run(verbose: bool = True) -> dict:
    cat = catalog_by_type()
    jobs = [j for j in load_csv("workloads.csv") if int(num(j["interruptible"])) == 1]
    jobs_kwh = []
    for j in jobs:
        gpu_h = num(j["hours_per_day"]) * num(j["days"]) * int(num(j["num_gpus"]))
        jobs_kwh.append((j["job_id"], num(cat[j["gpu_type"]]["watts"]) / 1000.0 * gpu_h))
    total_kwh = sum(k for _, k in jobs_kwh)
    wh = total_kwh * 1000.0

    table = []
    for region in REGION_CARBON:
        table.append({"region": region, "usd_kwh": REGION_PRICE_KWH[region], "g_kwh": REGION_CARBON[region],
                      "energy_usd": energy_cost_usd(wh, region), "carbon_kg": carbon_g(wh, region) / 1000.0})
    # balanced = lowest sum of the two min-max normalised criteria
    lo_c, hi_c = min(t["energy_usd"] for t in table), max(t["energy_usd"] for t in table)
    lo_g, hi_g = min(t["carbon_kg"] for t in table), max(t["carbon_kg"] for t in table)
    for t in table:
        t["balanced"] = (t["energy_usd"] - lo_c) / (hi_c - lo_c) + (t["carbon_kg"] - lo_g) / (hi_g - lo_g)
    cheapest = min(table, key=lambda t: t["energy_usd"])["region"]
    cleanest = min(table, key=lambda t: t["carbon_kg"])["region"]
    balanced = min(table, key=lambda t: t["balanced"])["region"]
    base = next(t for t in table if t["region"] == BASE)
    best = next(t for t in table if t["region"] == cleanest)

    if verbose:
        print("== Extension 5: Carbon-aware scheduling ==")
        print(f"interruptible jobs: {[j for j, _ in jobs_kwh]}")
        print(f"energy (GPU watts x GPU-hours): {total_kwh:,.0f} kWh/period")
        print(f"{'region':17}{'$/kWh':>7}{'gCO2/kWh':>10}{'energy $':>10}{'CO2 kg':>9}")
        for t in sorted(table, key=lambda t: t["carbon_kg"]):
            print(f"{t['region']:17}{t['usd_kwh']:>7.3f}{t['g_kwh']:>10}{t['energy_usd']:>10,.0f}{t['carbon_kg']:>9,.0f}")
        print(f"cheapest: {cheapest} | cleanest: {cleanest} | balanced: {balanced}")
        print(f"{BASE} -> {cleanest}: saves {base['carbon_kg']-best['carbon_kg']:,.0f} kg CO2 "
              f"({1-best['carbon_kg']/base['carbon_kg']:.1%}), electricity {base['energy_usd']-best['energy_usd']:+,.0f} USD")
        print("latency trade-off: europe-north1 is far from US users; fine for batch/training (interruptible), "
              "not for real-time inference.")

    out_path = os.path.join(ROOT, "outputs", "extension_5_carbon_scheduling.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["region", "usd_per_kwh", "gco2_per_kwh", "energy_cost_usd", "carbon_kg", "pick"])
        for t in table:
            picks = [n for n, r in (("cheapest", cheapest), ("cleanest", cleanest), ("balanced", balanced)) if r == t["region"]]
            w.writerow([t["region"], t["usd_kwh"], t["g_kwh"], round(t["energy_usd"], 2),
                        round(t["carbon_kg"], 1), "+".join(picks)])
    return {"cheapest": cheapest, "cleanest": cleanest, "balanced": balanced, "total_kwh": total_kwh}


if __name__ == "__main__":
    run()
