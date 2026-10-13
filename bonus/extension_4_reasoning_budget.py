"""Extension 4 — Reasoning budget: $ and Wh of is_reasoning=1 vs 0, and a cap scenario.

Run: python bonus/extension_4_reasoning_budget.py
Reads data only; does not modify finops/ or missions/. Writes outputs/extension_4_reasoning_analysis.csv
"""
from __future__ import annotations
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from missions._common import load_csv, num
from missions.m2_inference_levers import MODEL_PRICES
from finops import pricing, sustainability

DAYS = 30


def run(verbose: bool = True) -> dict:
    rows = load_csv("token_usage.csv")
    recs = []
    for r in rows:
        inp, out = int(num(r["input_tokens"])), int(num(r["output_tokens"]))
        pin, pout = MODEL_PRICES[r["route_tier"]]
        cost = pricing.request_cost(inp, out, pin, pout,
                                    cached_in=int(num(r["cached_input_tokens"])),
                                    batch=bool(int(num(r["is_batch"]))))
        reasoning = bool(int(num(r["is_reasoning"])))
        wh = sustainability.wh_per_query(inp + out, is_reasoning=reasoning)
        recs.append({"tier": r["route_tier"], "reasoning": reasoning, "tokens": inp + out,
                     "cost": cost, "wh": wh})

    def agg(flag):
        sub = [x for x in recs if x["reasoning"] == flag]
        return {"n": len(sub), "tokens": sum(x["tokens"] for x in sub),
                "cost": sum(x["cost"] for x in sub), "wh": sum(x["wh"] for x in sub)}

    rs, nm = agg(True), agg(False)
    tot_n, tot_cost, tot_wh = rs["n"] + nm["n"], rs["cost"] + nm["cost"], rs["wh"] + nm["wh"]
    shares = {"traffic": rs["n"] / tot_n, "cost": rs["cost"] / tot_cost, "energy": rs["wh"] / tot_wh}

    # Cap scenario: keep only `cap` of traffic as reasoning; the rest run as normal queries.
    # Saved $ = excess cost vs the mean non-reasoning request of the same tier;
    # saved Wh = reasoning energy minus the normal-mode energy for the same tokens.
    tier_mean = {}
    for t in {x["tier"] for x in recs}:
        sub = [x for x in recs if x["tier"] == t and not x["reasoning"]]
        tier_mean[t] = sum(x["cost"] / x["tokens"] for x in sub) / len(sub) if sub else 0.0
    reasoning_recs = sorted((x for x in recs if x["reasoning"]), key=lambda x: -x["wh"])
    scenarios = []
    for cap in (0.05, 0.02, 0.0):
        keep = int(round(cap * tot_n))
        dropped = reasoning_recs[keep:]
        saved_usd = sum(max(0.0, x["cost"] - tier_mean[x["tier"]] * x["tokens"]) for x in dropped)
        saved_wh = sum(x["wh"] - sustainability.wh_per_query(x["tokens"]) for x in dropped)
        scenarios.append({"cap": cap, "saved_usd_day": saved_usd, "saved_wh_day": saved_wh,
                          "saved_wh_pct": saved_wh / tot_wh * 100})

    if verbose:
        print("== Extension 4: Reasoning budget ==")
        print(f"traffic share of reasoning : {shares['traffic']:.1%}  ({rs['n']}/{tot_n} requests)")
        print(f"cost share of reasoning    : {shares['cost']:.1%}  (${rs['cost']:.2f} of ${tot_cost:.2f}/day)")
        print(f"energy share of reasoning  : {shares['energy']:.1%}  ({rs['wh']:.0f} of {tot_wh:.0f} Wh/day)")
        print(f"$/1M-token reasoning vs normal: {pricing.dollars_per_million(rs['cost'], rs['tokens']):.3f} "
              f"vs {pricing.dollars_per_million(nm['cost'], nm['tokens']):.3f}")
        print("note: current reasoning share is below 10%, so a 10% cap changes nothing; testing tighter caps")
        for s in scenarios:
            print(f"cap {s['cap']:.0%}: saves ${s['saved_usd_day']:.2f}/day (${s['saved_usd_day']*DAYS:.0f}/mo), "
                  f"{s['saved_wh_day']:.0f} Wh/day ({s['saved_wh_pct']:.1f}% of energy)")

    out_path = os.path.join(ROOT, "outputs", "extension_4_reasoning_analysis.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "reasoning", "normal", "note"])
        w.writerow(["requests", rs["n"], nm["n"], f"traffic share {shares['traffic']:.1%}"])
        w.writerow(["tokens", rs["tokens"], nm["tokens"], ""])
        w.writerow(["cost_usd_day", round(rs["cost"], 2), round(nm["cost"], 2), f"cost share {shares['cost']:.1%}"])
        w.writerow(["energy_wh_day", round(rs["wh"]), round(nm["wh"]), f"energy share {shares['energy']:.1%}"])
        w.writerow([])
        w.writerow(["cap_reasoning_traffic", "saved_usd_day", "saved_usd_month", "saved_wh_day", "saved_wh_pct"])
        for s in scenarios:
            w.writerow([f"{s['cap']:.0%}", round(s["saved_usd_day"], 2), round(s["saved_usd_day"] * DAYS),
                        round(s["saved_wh_day"]), round(s["saved_wh_pct"], 1)])
    return {"shares": shares, "scenarios": scenarios}


if __name__ == "__main__":
    run()
