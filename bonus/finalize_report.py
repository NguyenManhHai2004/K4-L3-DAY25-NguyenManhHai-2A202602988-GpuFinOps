"""Post-process outputs/report.md after M5 (does NOT touch missions/ or finops/).

M5 rewrites report.md every run (verify.py, run_all.py), so run this LAST:
    python verify.py && python bonus/finalize_report.py

It (1) fixes the mis-encoded em dash in the title (original code writes cp1252),
(2) appends the analysis sections the rubric asks for, using numbers from the extensions.
Idempotent: re-running replaces the appended block instead of duplicating it.
"""
from __future__ import annotations
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bonus"))
import extension_4_reasoning_budget as ext4
import extension_5_carbon_scheduling as ext5
from missions import m2_inference_levers

REPORT = os.path.join(ROOT, "outputs", "report.md")
MARK = "<!-- analysis:begin -->"


def levers_from(md: str) -> list[tuple[str, int]]:
    out = []
    for m in re.finditer(r"^\| (.+?) \| \$([\d,]+) \|\s*$", md, re.M):
        out.append((m.group(1), int(m.group(2).replace(",", ""))))
    return out


def main() -> None:
    raw = open(REPORT, "rb").read()
    try:
        md = raw.decode("utf-8")
    except UnicodeDecodeError:
        md = raw.decode("cp1252", errors="replace")
    md = md.replace("\r\n", "\n").split(MARK)[0].rstrip() + "\n"
    md = md.replace("NimbusAI � GPU", "NimbusAI — GPU")

    r2 = m2_inference_levers.run(verbose=False)
    r4 = ext4.run(verbose=False)
    r5 = ext5.run(verbose=False)
    sh = r4["shares"]
    ranked = sorted(levers_from(md), key=lambda x: -x[1])
    prio = "\n".join(f"{i}. {n}: ${v:,}/month" for i, (n, v) in enumerate(ranked, 1))

    block = f"""
{MARK}
## Analysis

### Unit economics ($/1M-token)
Baseline (all large model, no cache, no batch): **${r2['baseline_per_m']:.3f}/1M-token**. Optimized (cascade + cache + batch): **${r2['optimized_per_m']:.3f}/1M-token**, i.e. **{r2['savings_pct']}% cheaper** for the same {r2['total_tokens']:,} tokens/day.

### Why GPU-Util is a "lie"
`nvidia-smi` GPU-Util only says a kernel was running during the sample window, not how many SMs or tensor cores were busy.
gpu-h100-4 shows 98% util but ~19% MFU: kernels are resident but mostly stalled on memory or too small, so ~80% of the paid FLOPs are unused.
Cost impact: you pay H100 price for roughly A100-level useful work, so right-sizing saves money without losing throughput.

### Actions, ordered by savings (ROI)
{prio}

Purchasing is a contract change only (spot for interruptible jobs, reserved for 24/7 inference), so it goes first; right-size after re-testing throughput; idle shutdown is near-zero effort.

### Extensions
- **Reasoning budget** (`bonus/extension_4_reasoning_budget.py`): reasoning is {sh['traffic']:.1%} of traffic, {sh['cost']:.1%} of cost but {sh['energy']:.1%} of energy (~80x per query). It is an energy lever, not a dollar lever.
- **Carbon-aware scheduling** (`bonus/extension_5_carbon_scheduling.py`): for interruptible jobs cheapest region = {r5['cheapest']}, cleanest = {r5['cleanest']}, balanced = {r5['balanced']}. Moving us-east-1 -> {r5['cleanest']} cuts carbon ~92% and lowers electricity cost too, but adds latency, so only batch/training jobs should move.

### Sustainability tied to cost
Carbon and electricity price do not always move together, so region choice is a business decision. Full write-up: `outputs/SUBMISSION_REPORT.md`.
"""
    with open(REPORT, "w", encoding="utf-8", newline="\n") as f:
        f.write(md + block)
    print("report.md finalized")


if __name__ == "__main__":
    main()
