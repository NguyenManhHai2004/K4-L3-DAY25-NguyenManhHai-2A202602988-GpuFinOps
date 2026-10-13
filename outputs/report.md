# NimbusAI — GPU Cost Optimization Report

**Period:** monthly  
**Baseline spend:** $27,133  
**Optimized spend:** $14,626  
**Projected savings:** $12,507  (**46%**)

## Savings by lever

| Lever | Savings (USD) |
|---|---|
| Inference (cascade/cache/batch) | $1,212 |
| Purchasing (spot/reserved) | $10,040 |
| Right-size util-lies | $655 |
| Kill idle GPUs | $600 |

## Sustainability

- Energy per query: 0.24 Wh
- Carbon per query: 0.091 gCO2e
- Cheapest+cleanest region: europe-north1

_Figures are June-2026 as-of snapshots; re-baseline before acting._

<!-- analysis:begin -->
## Analysis

### Unit economics ($/1M-token)
Baseline (all large model, no cache, no batch): **$6.488/1M-token**. Optimized (cascade + cache + batch): **$1.126/1M-token**, i.e. **82.6% cheaper** for the same 7,533,027 tokens/day.

### Why GPU-Util is a "lie"
`nvidia-smi` GPU-Util only says a kernel was running during the sample window, not how many SMs or tensor cores were busy.
gpu-h100-4 shows 98% util but ~19% MFU: kernels are resident but mostly stalled on memory or too small, so ~80% of the paid FLOPs are unused.
Cost impact: you pay H100 price for roughly A100-level useful work, so right-sizing saves money without losing throughput.

### Actions, ordered by savings (ROI)
1. Purchasing (spot/reserved): $10,040/month
2. Inference (cascade/cache/batch): $1,212/month
3. Right-size util-lies: $655/month
4. Kill idle GPUs: $600/month

Purchasing is a contract change only (spot for interruptible jobs, reserved for 24/7 inference), so it goes first; right-size after re-testing throughput; idle shutdown is near-zero effort.

### Extensions
- **Reasoning budget** (`bonus/extension_4_reasoning_budget.py`): reasoning is 8.4% of traffic, 16.5% of cost but 94.0% of energy (~80x per query). It is an energy lever, not a dollar lever.
- **Carbon-aware scheduling** (`bonus/extension_5_carbon_scheduling.py`): for interruptible jobs cheapest region = us-east-wa, cleanest = europe-north1, balanced = us-east-wa. Moving us-east-1 -> europe-north1 cuts carbon ~92% and lowers electricity cost too, but adds latency, so only batch/training jobs should move.

### Sustainability tied to cost
Carbon and electricity price do not always move together, so region choice is a business decision. Full write-up: `outputs/SUBMISSION_REPORT.md`.
