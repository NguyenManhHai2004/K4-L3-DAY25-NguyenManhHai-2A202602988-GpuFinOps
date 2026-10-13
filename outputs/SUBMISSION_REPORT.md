# NimbusAI GPU FinOps Optimization — Lab 25 Submission Report

**Student:** Nguyen Manh Hai  
**Date:** October 2026  
**Lab:** Day 25 — GPU FinOps & Cost Optimization  
**Institution:** VinUni

---

## Executive Summary

This report documents a comprehensive GPU cost optimization analysis for NimbusAI, a startup LLM inference platform. Through systematic analysis of GPU telemetry, token usage patterns, and purchasing strategies, we identified and quantified **$12,507 in monthly savings (46% reduction)** measured in $/1M-token efficiency, without requiring infrastructure changes.

### Key Results at a Glance
- **Baseline monthly spend:** $27,133
- **Optimized monthly spend:** $14,626
- **Total projected savings:** $12,507/month (46%)
- **Primary savings driver:** GPU purchasing strategy (80% of savings)
- **Carbon reduction potential:** 92% via regional scheduling

---

## Part 1: Understanding the Problem

### Why $/1M-token Instead of $/GPU-hour?

Traditional GPU cost metrics focus on infrastructure spend ($/GPU-hour), but fail to measure **efficiency of utilization**. Two teams could spend identical amounts on GPU time while one delivers 10× more value due to superior software optimization. By measuring **$/1M-token (cost per million tokens processed)**, we force ourselves to optimize both *how much we pay* AND *how much value we deliver*.

**Finding:** NimbusAI's baseline efficiency was $6.488/1M-token, indicating significant room for optimization.

### Four Cost Optimization Levers Identified

Our analysis revealed four independent optimization opportunities:

1. **Inference Software Optimization** — Cascade routing, prompt caching, batch API
2. **GPU Purchasing Strategy** — Spot vs Reserved vs On-demand tier selection
3. **Right-sizing Over-provisioned GPUs** — Addressing GPU utilization lies
4. **Eliminating Idle GPU Hours** — Shutting down consistently underutilized hardware

---

## Part 2: Detailed Findings by Mission

### M1: GPU Efficiency Audit — "The GPU Util Lie"

**Discovery:** 2 GPUs (gpu-h100-4, gpu-a10g-1) report 96-98% utilization but achieve only 19-27% MFU (Model FLOPs Utilization).

This is the "GPU-Util lie" — the GPU's clock is active, but the actual compute work is minimal, likely due to memory bandwidth limitations or inefficient workload distribution.

**Quantified Impact:**
- GPU-h100-4: 98.2% util, 19.4% MFU → Candidate for A100 (50% cost reduction)
- GPU-a10g-1: 96.9% util, 26.8% MFU → Candidate for L4 (60% cost reduction)
- Additional: gpu-h100-5 idles 8 h in the telemetry day = $20/day, extrapolated to ~$600/month (assumes the pattern repeats daily)

**Savings:** $655 (right-sizing) + $600 (idle kill) = **$1,255/month**

---

### M2: Inference Cost Levers — Cascade, Cache, Batch

**Baseline scenario:** All 2,400 daily requests routed to the large language model, no caching, no batching.
- **Baseline cost:** $6.488/1M-token ($48.87/day)

**Optimized scenario:** Apply three software techniques simultaneously:
1. **Cascade routing** — Route requests to the small model where `route_tier=small` ($0.20/$0.40 vs $3.00/$15.00 per 1M tokens)
2. **Prompt caching** — 10% discount on cached input tokens (matching Anthropic, Claude, and Gemini policies)
3. **Batch API** — 50% discount on batch-processable requests

**Optimized cost:** $1.126/1M-token ($8.48/day)

**Savings:** 82.6% reduction from inference optimization alone = **$1,212/month**

**Key insight:** Discounts multiply. With both caching (10% cost on cached input) and batching (50% total bill), the combined effective rate is 0.10 × 0.50 = 0.05 (95% off baseline).

---

### M3: GPU Purchasing Strategy — Spot vs Reserved vs On-demand

**Analysis:** Break-even utilization for reserved instances at 45% discount is 55% (≈13.2 hours/day).

**Policy:**
- **Interruptible jobs + duty < 55%** → Spot instances (account for checkpoint overhead)
- **Steady jobs + duty ≥ 55%** → 3-year reserved instances
- **Spiky jobs** → On-demand

**Recommendations:**
| Job | GPU | Tier | Savings |
|-----|-----|------|---------|
| job-train-llm | H100×8 | Spot | $4,404 |
| job-infer-chat | A10G×6 | Reserved | $1,728 |
| job-infer-rag | A100×3 | Reserved | $1,706 |
| (others) | (mixed) | (mixed) | $2,202 |

**Total purchasing savings:** **$10,040/month (39.1%)**

**Why this dominates:** Purchasing strategy accounts for 80% of total savings because GPU hourly rates are the largest fixed cost in the bill.

---

### M4: Cost Allocation & Chargeback Readiness

**Cost distribution by team (daily):**
- Team "assistant": $2.59 (highest consumer)
- Team "search": $2.49
- Team "eval": $1.79
- Team "rag": $1.60

**Tag coverage:** 92% (exceeds 80% gate) → Chargeback ready ✓

This enables cost transparency and team-level accountability without guesswork.

---

### M5: Integrated Optimization & Sustainability

**Monthly Financial Summary:**

| Category | Amount |
|----------|--------|
| Baseline spend | $27,133 |
| Inference optimization | -$1,212 |
| Purchasing optimization | -$10,040 |
| Right-sizing | -$655 |
| Idle elimination | -$600 |
| **Optimized spend** | **$14,626** |
| **Total savings** | **$12,507 (46%)** |

**Sustainability Metrics:**
- Energy per query: 0.24 Wh
- Carbon per query: 0.091 gCO2e (us-east-1 baseline)
- Region comparison: europe-north1 (hydropower, 30 gCO2e/kWh) is 22× cleaner than europe-central2 (coal, 660 gCO2e/kWh)

---

## Part 3: Extensions (code in `bonus/`, no change to `finops/`, `missions/`, `tests/`)

### Extension 4: Reasoning budget — `bonus/extension_4_reasoning_budget.py`

| Metric (per day, optimized pricing) | Reasoning | Normal |
|---|---|---|
| Requests | 201 (**8.4% of traffic**) | 2,199 |
| Cost | $1.40 (**16.5% of cost**) | $7.08 |
| Energy (Wh) | 29,788 (**94.0% of energy**) | 1,887 |

**Insight:** reasoning is 8.4% of traffic but 94% of energy, because the model uses ~80x the energy of a normal query on the same tokens. In dollars it is cheap (the API bills per token; $/1M-token is the same, 1.125 vs 1.127), so the real cost of reasoning is energy/latency, not the bill.

**Cap scenarios** (reasoning is already below 10%, so a 10% cap changes nothing; tighter caps tested):

| Reasoning cap | Saved $/month | Saved energy |
|---|---|---|
| 5% of traffic | ~$0 | 24.0% |
| 2% of traffic | ~$2 | 61.1% |
| 0% | ~$3 | 92.9% |

**Routing rule proposed:** use reasoning only for tasks flagged complex (e.g. multi-step eval or code), default everything else to normal mode. This is an energy/carbon lever, not a dollar lever. (Dataset has no confidence column, so no confidence gate is simulated.)

### Extension 5: Carbon-aware scheduling — `bonus/extension_5_carbon_scheduling.py`

Energy for the 5 interruptible jobs = GPU watts x GPU-hours = **1,789 kWh/period**.

| Region | $/kWh | gCO2/kWh | Electricity $ | CO2 (kg) |
|---|---|---|---|---|
| europe-north1 | 0.090 | 30 | 161 | 54 |
| us-east-wa | 0.055 | 90 | 98 | 161 |
| us-west-2 | 0.070 | 120 | 125 | 215 |
| us-east-1 (current) | 0.120 | 380 | 215 | 680 |
| europe-central2 | 0.180 | 660 | 322 | 1,181 |

- Cheapest: **us-east-wa**. Cleanest: **europe-north1**. Best balance of both: **us-east-wa** (second cleanest, cheapest power).
- Moving from us-east-1 to europe-north1 cuts **626 kg CO2 (92.1%)** and also saves ~$54 of electricity; moving to us-east-wa saves 519 kg (76%) and ~$117.
- Latency trade-off: europe-north1 is far from US users. That is fine for interruptible training/batch jobs and not for real-time inference, so only interruptible jobs should move.
- Which region is "optimal" depends on company priority: pure cost -> us-east-wa; pure carbon -> europe-north1.

---

## Part 3b: Analysis behind the numbers

**Why GPU-Util is a "lie".** `nvidia-smi` GPU-Util only says a kernel was running during the sample window, not how many SMs or tensor cores were busy. gpu-h100-4 shows 98.2% util but 19.4% MFU: kernels are resident but mostly stalled on memory or small, so ~80% of the paid FLOPs are unused. For cost this means you pay H100 price for ~A100-level useful work, hence right-sizing saves money without losing throughput.

**Priority order (by ROI and effort):**
1. Purchasing (spot for interruptible, reserved for 24/7): $10,040/month, biggest lever and a contract change only.
2. Right-size the 2 util-lie GPUs: $655/month, low risk after re-testing throughput.
3. Kill idle GPU hours: $600/month, near-zero effort.
4. Inference levers: $1,212/month in this dataset (82.6% off the inference bill, which is small next to GPU rent).
5. Sustainability: shift interruptible jobs to a cleaner region and cap reasoning; large carbon/energy gain, small dollar gain.

**Sustainability tied to cost.** Carbon and electricity price do not always move together (europe-north1 is cleaner but pricier than us-east-wa), so the region choice is a business decision; for interruptible jobs europe-north1 is both cleaner and cheaper than the current us-east-1.

## Part 4: Implementation Recommendations

### Immediate Actions (0-1 week)
1. **Apply purchasing strategy (M3)** — Contract spot instances for training jobs, 3-year reserved for 24/7 inference
2. **Enable cascade routing (M2)** — Deploy router logic to direct 80% of requests to smaller model
3. **Kill idle GPU (M1)** — Shut down gpu-h100-5 or reallocate

### Short-term (1-4 weeks)
1. **Right-size over-provisioned GPUs** — Replace gpu-h100-4 with A100, gpu-a10g-1 with L4
2. **Implement prompt caching** — Modify request logic to extract and cache common prefixes
3. **Enable batch API** — Queue batch-compatible requests for off-peak processing

### Medium-term (4-12 weeks)
1. **Reasoning confidence gating** — Add confidence scores to model output, gate expensive reasoning
2. **Regional scheduling for interruptible jobs** — Implement multi-region job queue, preferring europe-north1

### Measurement
- Run `python missions/run_all.py` monthly to re-baseline
- Track $/1M-token as primary KPI
- Report cost by team for chargeback

---

## Conclusion

Through systematic analysis of GPU telemetry, token usage, and purchasing options—**without modifying infrastructure or deploying new hardware**—we identified a path to **46% cost reduction ($12,507/month)** at NimbusAI.

The largest opportunity (80% of savings) lies in **GPU purchasing strategy**: matching Reserved instances to steady workloads, Spot to interruptible jobs, and On-demand to variable usage. The second-order opportunity (18% of savings) comes from **inference software optimization** via cascade routing and prompt caching.

Both extensions demonstrate that cost optimization extends beyond compute purchasing: **reasoning budgets** can be optimized for confidence-weighted use, and **carbon footprint** can be reduced 90% via regional scheduling—turning cost optimization into sustainability optimization simultaneously.

---

## Appendices

### A. Data Files Generated
- `data/price_catalog.csv` — GPU pricing by tier (on-demand, spot, 1yr/3yr reserved)
- `data/gpu_telemetry.csv` — GPU utilization, MFU, MBU metrics
- `data/token_usage.csv` — 2,400 daily request logs with caching, batching, reasoning flags
- `data/workloads.csv` — 8 jobs with duty cycle and interruptibility metadata

### B. Output Files
- `outputs/report.md` — Summary baseline vs optimized
- `outputs/savings.png` — Waterfall chart by lever
- `outputs/focus_export.csv` — FOCUS-format cost allocation
- `outputs/extension_4_reasoning_analysis.csv` — Reasoning cost breakdown
- `outputs/extension_5_carbon_scheduling.csv` — Regional carbon impact
- `bonus/extension_4_reasoning_budget.py`, `bonus/extension_5_carbon_scheduling.py` — code that produces the two extension CSVs

### C. Verification
```bash
python verify.py        # 11/11 checks passed
pytest -q              # 15/15 tests passed
cat outputs/report.md  # Final report
```

---

**Author:** Nguyen Manh Hai  
**Verification:** 11/11 checks and 15/15 tests passing; no files in `tests/` or `finops/` were modified.
