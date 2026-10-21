#!/usr/bin/env python3
"""Fig. 5d -- memory traffic per query against the selected-set size k.

Analytic count of values moved in the diversity comparison alone (Methods,
"Memory-traffic accounting"):
    software MMR : N * k * d        (every candidate re-reads all k rows of S)
    H-AIMDC      : N * (d + 1)      (candidate broadcast in, one scalar out)
N is the mean number of candidates streamed per query on the 1,000-question
HotpotQA run at the operating point (write_stats, distractor scope, k = 5):
    H_RAG_cuad_v3.0_MMR_deviceModeling/sweep_exports/write_stats/distractor/
        20260911_103459_mmr-capacitor_centroid-nvm/write_stats_summary.json
One N is used for both lines, so the gap is exactly k*d/(d+1) ~ k.

    python plot_fig5d_traffic.py            # writes figures/fig5d_traffic.{png,svg,pdf}
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

# software MMR: step-wise, one level per k
for i, (k, v) in enumerate(zip(KS, sw)):
    k_next = KS[i + 1] if i + 1 < len(KS) else 24
    ax.plot([k, k_next], [v, v], color=C_SW, lw=2.2, solid_capstyle="butt", zorder=3)
ax.plot(KS, sw, "o", color=C_SW, ms=6, mec="white", mew=0.8, zorder=4)
# H-AIMDC: flat
ax.plot([2.5, 24], [hw, hw], color=C_HW, lw=2.2, zorder=3)
ax.plot(KS, [hw] * 3, "o", color=C_HW, ms=6, mec="white", mew=0.8, zorder=4)

# gap arrows with the ratio
for k, v in zip(KS, sw):
    ax.annotate("", xy=(k, v / 1.25), xytext=(k, hw * 1.25),
                arrowprops=dict(arrowstyle="<->", color=C_ARR, lw=0.9, ls=(0, (3, 2)),
                                mutation_scale=9), zorder=5)
    ax.text(k + 0.45, (v * hw) ** 0.5, f"{v / hw:.0f}×", color=C_ARR, fontsize=9.5,
            fontweight="bold", va="center", ha="left")

ax.text(23.5, sw[-1] * 2.6, "Software MMR", color=C_SW, fontsize=9.5, fontweight="bold",
        ha="right", va="bottom")
ax.text(23.5, sw[-1] * 1.55, "re-reads all k rows for every candidate", color=C_SW,
        fontsize=7.6, ha="right", va="bottom")
ax.text(23.5, hw / 1.6, "H-AIMDC", color=C_HW, fontsize=9.5, fontweight="bold",
        ha="right", va="top")
ax.text(23.5, hw / 2.6, "flat in k: rows stay in the array", color=C_HW, fontsize=7.6,
        ha="right", va="top")

ax.set_xlabel("Selected set size  k", fontsize=10, fontweight="bold")
ax.set_ylabel("Memory traffic per query (values)", fontsize=10, fontweight="bold")
for lab in ax.get_yticklabels():
    lab.set_fontweight("bold")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)

out = Path(__file__).resolve().parent / "figures"
out.mkdir(exist_ok=True)
for ext in ("png", "svg", "pdf"):
    fig.savefig(out / f"fig5d_traffic.{ext}", dpi=300, bbox_inches="tight", pad_inches=0.05)
print("N =", N, "| software:", [round(v) for v in sw], "| H-AIMDC:", round(hw),
      "| ratios:", [round(v / hw, 2) for v in sw])
