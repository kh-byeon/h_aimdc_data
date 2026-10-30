#!/usr/bin/env python3
"""Fig. 5d -- idealized selected-set operand movement per query against the selected-set size k.

Analytic count of values moved in the diversity comparison alone (Supplementary Note 2.3):
    re-read baseline : N * k * d    (every candidate re-reads all k rows of S from memory)
    U-AIMDC          : N * (d + 1)  (candidate broadcast in, one scalar out of the array)
The panel shows how each count scales with k. It is not a traffic or energy comparison:
the k rows (15-60 KiB in FP32 for k = 5-20) can stay in a cache or SRAM, and writes,
conversion and reduction are not counted. No ratio is drawn for that reason.
N is the mean number of candidates streamed per query on the 1,000-question
HotpotQA run at the operating point (write_stats, distractor scope, k = 5):
    simulation_results/write_stats/write_stats_k/distractor/k5/
        20260912_213905_mmr-capacitor_centroid-nvm/write_stats_summary.json  (n_streamed, mean)
One N is used for both lines, so the gap is exactly k*d/(d+1) ~ k.

    python plot_fig5d_operands.py           # writes figures/fig5d_operands.{png,svg,pdf}

Replaces plot_fig5d_traffic.py of v1.0.0, which drew the original panel with 5x/10x/20x ratio
arrows and the labels "software" and "H-AIMDC".
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

N = 6.936          # candidates streamed per query (mean, n = 1000)
D = 768            # embedding dimension
KS = [5, 10, 20]

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"], "font.size": 10,
    "axes.linewidth": 0.8, "pdf.fonttype": 42, "ps.fonttype": 42,
})
C_SW, C_HW, C_ARR = "#8C8C8C", "#C8641E", "#1F7A5C"

sw = [N * k * D for k in KS]
hw = N * (D + 1)

fig, ax = plt.subplots(figsize=(3.6, 3.3))
fig.subplots_adjust(left=0.2, right=0.97, top=0.95, bottom=0.17)
ax.set_yscale("log")
ax.set_xlim(2.5, 24); ax.set_ylim(1e3, 1e6)
ax.set_xticks(KS); ax.set_xticklabels([str(k) for k in KS], fontweight="bold")
ax.grid(True, which="major", axis="y", color="0.85", lw=0.6)
ax.grid(True, which="major", axis="x", color="0.85", lw=0.6)
ax.set_axisbelow(True)

# re-read baseline: step-wise, one level per k
for i, (k, v) in enumerate(zip(KS, sw)):
    k_next = KS[i + 1] if i + 1 < len(KS) else 24
    ax.plot([k, k_next], [v, v], color=C_SW, lw=2.2, solid_capstyle="butt", zorder=3)
ax.plot(KS, sw, "o", color=C_SW, ms=6, mec="white", mew=0.8, zorder=4)
# U-AIMDC: flat
ax.plot([2.5, 24], [hw, hw], color=C_HW, lw=2.2, zorder=3)
ax.plot(KS, [hw] * 3, "o", color=C_HW, ms=6, mec="white", mew=0.8, zorder=4)

# size of the k selected rows in FP32, so the reader sees they are small
for i, (k, v) in enumerate(zip(KS, sw)):
    lab = f"{k * D * 4 / 1024:.0f} KiB" + (" (FP32)" if i == 0 else "")
    ax.text(k + 0.3, v / 1.3, lab, color=C_SW, fontsize=7.2, ha="left", va="top")

ax.text(23.5, sw[-1] * 2.6, "Re-read baseline", color=C_SW, fontsize=9.5, fontweight="bold",
        ha="right", va="bottom")
ax.text(23.5, sw[-1] * 1.55, "k rows read for every candidate", color=C_SW,
        fontsize=7.6, ha="right", va="bottom")
ax.text(23.5, hw / 1.6, "U-AIMDC", color=C_HW, fontsize=9.5, fontweight="bold",
        ha="right", va="top")
ax.text(23.5, hw / 2.6, "flat in k: rows stay in the array", color=C_HW, fontsize=7.6,
        ha="right", va="top")

ax.set_xlabel("Selected set size  k", fontsize=10, fontweight="bold")
ax.set_ylabel("Selected-set operands moved\nper query (values)", fontsize=10, fontweight="bold")
for lab in ax.get_yticklabels():
    lab.set_fontweight("bold")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)

out = Path(__file__).resolve().parent / "figures"
out.mkdir(exist_ok=True)
for ext in ("png", "svg", "pdf"):
    fig.savefig(out / f"fig5d_operands.{ext}", dpi=300, bbox_inches="tight", pad_inches=0.05)
print("N =", N, "| re-read baseline:", [round(v) for v in sw], "| U-AIMDC:", round(hw),
      "| ratios:", [round(v / hw, 2) for v in sw])
