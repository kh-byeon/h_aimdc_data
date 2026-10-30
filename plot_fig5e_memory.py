"""Fig. 5e — on-chip and device-DRAM memory on one log axis.

Bar length = total footprint (log axis). Each bar is divided in proportion to each component's share of
the total, so the segments read as fractions and the bar end reads as the total.
Byte counts are decimal. Sources: offline_data_* builds, online_accelerator_device.py, llm_generator.py
(h_rag); the measured footprints are listed in simulation_results/fig5e_memory_footprint_reference.md.
The array segment counts one byte per stored analog value, a storage-equivalent convention, not a
physical area.

    python plot_fig5e_memory.py   # figures/fig5e_memory.{pdf,svg,png}, simulation_results/fig5e/fig5e_numbers.json
"""
import json
import math
import os

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import FixedLocator, FuncFormatter, LogLocator, NullFormatter

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "figures")
NUM = os.path.join(ROOT, "simulation_results", "fig5e")
os.makedirs(OUT, exist_ok=True)
os.makedirs(NUM, exist_ok=True)

D, NLIST, M, CODEWORDS, K = 768, 128, 8, 256, 5
ARRAYS = (NLIST + K) * D * 1                     # 102,144 stored analog values, drawn at 1 B per value
PQLUT = M * CODEWORDS * (D // M) * 4
OPQ = D * D * 4
CAND = 875 * D * 4                               # decoded candidates, largest CUAD contract (875 chunks)
ENC = 109_486_464 * 4                            # multi-qa-mpnet-base-dot-v1, fp32 as run
VOCAB, HID, LAYERS = 128_256, 4096, 32
LIN = LAYERS * (2 * HID * HID + 2 * HID * 1024 + 3 * HID * 14_336)
REST = 2 * VOCAB * HID + (2 * LAYERS + 1) * HID
GEN = {"int4": LIN * (0.5 + 4 / 64) + REST * 2,
       "int8": LIN + LAYERS * (2 * HID + 2 * 1024 + 2 * 14_336 + HID) * 4 + REST * 2,
       "fp16": (LIN + REST) * 2}
KV = 2 * LAYERS * 8 * 128 * 2 * (2805 + 512)
NPU_SRAM, PHONE_DRAM = (0.384e6, 8e6), (11e9, 19e9)

C_ONCHIP = {"U-AIMDC arrays": "#d9822b", "PQ LUT": "#7d99c9", "OPQ rotation": "#2f4b7c", "Candidate buffer": "#1b7f79"}
C_DRAM = {"Generator weights": "#333333", "KV cache": "#8c8c8c", "Query encoder": "#c4c4c4"}
bars = [  # (row label, [(component, bytes)])
    ("On-chip", [("U-AIMDC arrays", ARRAYS), ("PQ LUT", PQLUT), ("OPQ rotation", OPQ), ("Candidate buffer", CAND)]),
    ("DRAM, int4", [("Generator weights", GEN["int4"]), ("KV cache", KV), ("Query encoder", ENC)]),
    ("DRAM, int8", [("Generator weights", GEN["int8"]), ("KV cache", KV), ("Query encoder", ENC)]),
    ("DRAM, fp16", [("Generator weights", GEN["fp16"]), ("KV cache", KV), ("Query encoder", ENC)]),
]
json.dump({lab: {c: b for c, b in segs} | {"total": sum(b for _, b in segs)} for lab, segs in bars},
          open(f"{NUM}/fig5e_numbers.json", "w"), indent=1)


def fmt(b):
    if b >= 1e9:
        return f"{b / 1e9:.1f} GB"
    if b >= 1e8:
        return f"{b / 1e9:.2f} GB"
    return f"{b / 1e6:.1f} MB" if b >= 1e6 else f"{b / 1e6:.2f} MB"


matplotlib.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"],
    "font.size": 7, "axes.labelsize": 7, "xtick.labelsize": 6.5, "ytick.labelsize": 6.5,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "xtick.minor.width": 0.4, "xtick.major.size": 2.5,
    "xtick.minor.size": 1.5, "pdf.fonttype": 42, "svg.fonttype": "none",
})
INK, MUTED, BAND = "#222222", "#5a5a5a", "#ebebeb"
fig = plt.figure(figsize=(88 / 25.4, 64 / 25.4))
ax = fig.add_axes([0.175, 0.35, 0.75, 0.47])
X0, X1 = 1e5, 1e11
ax.set_xscale("log"); ax.set_xlim(X0, X1)
ys = [0, 1.45, 2.45, 3.45]
ax.set_ylim(ys[-1] + 0.5, -0.75)

REFS = [  # (bytes, label, horizontal alignment)
    (4e6, "Ethos-N78 max\n4 MB", "right"), (8e6, "Edge TPU\n8 MB", "left"),
    (11e9, "16 GB phone\n11 GB per app", "right"),
]
for x, lab, ha in REFS:
    y_end = ys[0] + 0.55 if x < 1e9 else ys[-1] + 0.45          # SRAM lines span the on-chip row only
    ax.plot([x, x], [y_end, -0.55], color=MUTED, lw=0.6, ls=(0, (2.5, 1.5)), zorder=1, clip_on=False)
    ax.text(x * (0.93 if ha == "right" else 1.07), -0.6, lab, ha=ha, va="bottom", fontsize=5.5, color=MUTED,
            linespacing=1.05, clip_on=False)
ax.text(math.sqrt(4e6 * 8e6), -1.25, "NPU on-chip SRAM", ha="center", va="bottom", fontsize=6, color=INK, clip_on=False)
ax.text(11e9 * 0.93, -1.25, "Smartphone DRAM", ha="right", va="bottom", fontsize=6, color=INK, clip_on=False)

H = 0.62
for (lab, segs), y in zip(bars, ys):
    total = sum(b for _, b in segs)
    span = math.log10(total) - math.log10(X0)
    pos = math.log10(X0)
    for comp, b in segs:
        a_, b_ = 10 ** pos, 10 ** (pos + span * b / total)
        color = C_ONCHIP.get(comp) or C_DRAM[comp]
        ax.barh(y, b_ - a_, left=a_, height=H, color=color, lw=0, zorder=2)
        pos += span * b / total
        if pos < math.log10(total) - 1e-9:                      # surface gap between segments
            ax.plot([10 ** pos] * 2, [y - H / 2, y + H / 2], color="white", lw=0.7, zorder=2.5,
                    solid_capstyle="butt")
    ax.text(total * 1.3, y, fmt(total), ha="left", va="center", fontsize=6, color=INK, zorder=3,
            bbox=dict(boxstyle="square,pad=0.15", facecolor="white", edgecolor="none"))

ax.set_yticks(ys); ax.set_yticklabels([b[0] for b in bars])
ax.tick_params(axis="y", length=0)
ax.set_xlabel("Memory footprint", labelpad=2)
ax.xaxis.set_major_locator(FixedLocator([1e5, 1e6, 1e7, 1e8, 1e9, 1e10, 1e11]))
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, p: {1e5: "100 kB", 1e6: "1 MB", 1e7: "10 MB", 1e8: "100 MB",
                                                        1e9: "1 GB", 1e10: "10 GB", 1e11: "100 GB"}.get(v, "")))
ax.xaxis.set_minor_locator(LogLocator(base=10, subs=(2, 3, 4, 5, 6, 7, 8, 9), numticks=20))
ax.xaxis.set_minor_formatter(NullFormatter())
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)

# legends with component sizes
on = [Patch(color=C_ONCHIP[c], label=f"{c} {fmt(b)}") for c, b in bars[0][1]]
dr = [Patch(color=C_DRAM["Generator weights"], label="Generator weights"),
      Patch(color=C_DRAM["KV cache"], label=f"KV cache {fmt(KV)}"),
      Patch(color=C_DRAM["Query encoder"], label=f"Query encoder {fmt(ENC)}")]
kw = dict(frameon=False, fontsize=5.8, handlelength=1.0, handleheight=0.8, columnspacing=1.1, handletextpad=0.4,
          borderaxespad=0, loc="upper left")
fig.text(0.02, 0.185, "On-chip", fontsize=6, fontweight="bold", va="top")
fig.legend(handles=on, ncol=2, bbox_to_anchor=(0.175, 0.192), **kw)
fig.text(0.02, 0.055, "DRAM", fontsize=6, fontweight="bold", va="top")
fig.legend(handles=dr, ncol=3, bbox_to_anchor=(0.175, 0.062), **kw)

for ext in ("pdf", "svg", "png"):
    fig.savefig(f"{OUT}/fig5e_memory.{ext}", dpi=600)
svg = open(f"{OUT}/fig5e_memory.svg", encoding="utf8").read()
open(f"{OUT}/fig5e_memory.svg", "w", encoding="utf8").write(
    svg.replace("'Liberation Sans'", "Arial, 'Liberation Sans', sans-serif"))
print("saved")
