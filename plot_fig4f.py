#!/usr/bin/env python3
"""Fig. 4f: retention-endurance comparison, drawn from simulation_results/fig4f/fig4f_points.csv
(= the literature rows of Supplementary Table 2) plus the values of this work stated in THIS_WORK below.

    python plot_fig4f.py            # writes figures/fig4f.png and figures/fig4f.pdf

Changes against the earlier draft (Fig5d_draft.py, v1.0.0):
  * every literature point comes from the CSV, which mirrors Supplementary Table 2
  * no upward arrows: the charge-storage cells that report no endurance are placed at the top
    edge of the plot (FLOOR below); that position is not a measured endurance (stated in the caption)
  * this work is drawn as open squares: FeCAP at the extrapolated retention and the last endurance
    checkpoint with >= 90 % of the pristine window; DeCAP at the 4T2C retention (6.2 h) and the
    2T1C write test (1e10 cycles), two different test structures
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "simulation_results" / "fig4f" / "fig4f_points.csv"
OUT = ROOT / "figures"

# ----------------------------------------------------------------------------- this work
# retention: DeCAP = time at which the notch drift of the 10 h 4T2C trace reaches the
# smallest spacing of the 25 programmed states (62 mV; Supplementary Fig. 3), 6.2 h.
#            FeCAP = measured window of the single-state transfer test (10^4 s) and its
#            log-linear extrapolation to ten years (3.2e8 s).
# endurance: FeCAP = last checkpoint at which the +/-5.5 V transfer-curve window stays >= 90 % of
#            pristine: 1e5 for both devices (554 3-13#1: 90.7 %; 556 2-17: 92.4 %); tested to 1e8 / 1e7
#            DeCAP = 2T1C storage-node write test to 1e10 cycles
THIS_WORK = dict(
    fecap_ret=3.2e8, fecap_end=1e5,     # retention extrapolated to ten years from the 10^4 s fit, as in Table 2;
                                        # endurance = last checkpoint with >= 90 % of the pristine window (both devices)
    decap_ret=2.2e4, decap_end=1e10,    # 6.2 h drift to the 62 mV minimum state spacing; 2T1C write test
)
FLOOR = 1.5e10                          # top-edge position of cells without a reported endurance

# ----------------------------------------------------------------------------- style
plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"], "font.size": 10,
    "axes.linewidth": 0.7, "xtick.major.width": 0.7, "ytick.major.width": 0.7,
    "xtick.major.size": 3.5, "ytick.major.size": 3.5,
    "xtick.labelsize": 9, "ytick.labelsize": 9,
    "pdf.fonttype": 42, "ps.fonttype": 42,
})
C_FE, C_RR, C_PC, C_FL = "#2E5EAA", "#3F7A56", "#8A4FA8", "#1F7A8C"
C_CH, C_TW = "#D2691E", "#B3282B"
C_BIN, C_BINT = "#A8A8A8", "#8C8C8C"
C_STAT, C_DYN = "#8FB8DE", "#F0B27A"
YR, DAY = 3.156e7, 8.64e4
RET_ST_LO, END_ST = 10 * DAY, 1e1
RET_DY_LO, RET_DY, END_DY_LO, END_DY_HI = 3.7e-5, 3.7e-2, 1e6, 1e8
X_MIN, X_MAX, Y_MIN, Y_MAX = 1e-5, 1e10, 1e2, 1e11

COLOR = {"hkmg_fefet": C_FE, "srcoox": C_RR, "hfo2_ispva": C_RR, "mlc_pcm": C_PC,
         "ct_memristor": C_FL, "sns2_fefet": C_FE, "sr_rram": C_RR, "mos2_flash": C_FL,
         "si_gain_cell": C_BIN, "mos2_2t1c": C_CH, "igzo_2t1c": C_CH}
# label offsets in points and alignment, per key -- tune here
OFFSET = {
    "hkmg_fefet": ((40, -13), "center"), "srcoox": ((-8, -9), "right"),
    "hfo2_ispva": ((-8, 0), "right"), "mlc_pcm": ((-8, 8), "right"),
    "ct_memristor": ((-8, 0), "right"), "ito_fefet": ((-8, 0), "right"),
    "mos2_fefet": ((-8, -8), "right"), "sns2_fefet": ((-8, 9), "right"),
    "igzo_hzo_fefet": ((8, -8), "left"), "sr_rram": ((-8, 0), "right"),
    "mos2_flash": ((8, 3), "left"),
    "si_gain_cell": ((-8, 0), "right"), "mos2_2t1c": ((0, -13), "center"),
    "igzo_2t1c": ((0, -26), "center"),
}
# two sources sit on the same (1e5, 1e4) point; they are nudged apart by this visual factor
# (labels and the CSV keep the true values)
JITTER = {"hkmg_fefet": 0.85, "mos2_flash": 1.15}


def load_points():
    rows = []
    with open(DATA, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            r["retention_s"] = float(r["retention_s"])
            r["endurance_cycles"] = float(r["endurance_cycles"]) if r["endurance_cycles"] else None
            rows.append(r)
    return rows


def marker_kind(r):
    """2 = both axes analog, 1 = retention analog / endurance binary, 0 = both binary."""
    if r["retention_mode"] == "analog" and r["endurance_mode"] == "analog":
        return 2
    if r["retention_mode"] == "analog":
        return 1
    return 0


def draw_point(ax, x, y, kind, col):
    if kind == 2:
        ax.plot([x], [y], "o", color=col, mec="white", mew=0.7, ms=6.6, zorder=7)
    elif kind == 1:
        ax.plot([x], [y], "o", mfc=col, fillstyle="left", ms=6.2, mec=col, mew=1.3,
                ls="none", zorder=7)
    else:
        ax.plot([x], [y], "o", mfc="white", mec=C_BIN, mew=1.2, ms=5.0, ls="none", zorder=5)


def main():
    pts = load_points()
    fig, ax = plt.subplots(figsize=(5.55, 4.60))
    fig.subplots_adjust(left=0.155, right=0.965, top=0.90, bottom=0.145)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(X_MIN, X_MAX); ax.set_ylim(Y_MIN, Y_MAX)

    # ---- tier requirements (unchanged from the draft)
    ax.add_patch(Rectangle((RET_ST_LO, END_ST), 1e11, 1e14, fc=C_STAT, alpha=0.26, ec="none", zorder=0))
    ax.add_patch(Rectangle((RET_DY, END_DY_LO), 1e11, 1e14, fc=C_DYN, alpha=0.30, ec="none", zorder=0))
    ax.plot([RET_DY, 1e11], [END_DY_HI, END_DY_HI], color="#8A4B10", lw=0.7, ls=(0, (4, 2.5)), zorder=2, alpha=0.85)
    plt.rcParams["hatch.linewidth"] = 0.5
    ax.add_patch(Rectangle((RET_ST_LO, END_DY_LO), 1e11, 1e14, fc="none", ec="#A8A8A8", lw=0.6,
                           hatch="////", alpha=0.55, zorder=1))
    ax.add_patch(Rectangle((RET_ST_LO, END_DY_LO), 1e11, 1e14, fc="none", ec="#6A6A6A", lw=0.8,
                           alpha=0.8, zorder=2))
    ax.axvspan(RET_DY_LO, RET_DY, color=C_DYN, alpha=0.13, lw=0, zorder=0)
    for xv in (RET_DY_LO, RET_DY):
        ax.plot([xv, xv], [1e1, Y_MAX], color="#8A4B10", lw=0.7, ls=(0, (2, 2)), zorder=1)
    LM = [(1e-3, "1 ms"), (1, "1 s"), (3.6e3, "1 h"), (DAY, "1 day"), (YR, "1 yr"), (10 * YR, "10 yr")]
    for xv, _ in LM:
        ax.axvline(xv, color="#9AA0A6", lw=0.4, ls=(0, (1, 2.5)), alpha=0.5, zorder=0)
    ax.text(5e-5, 4e8, "dynamic tier\nrequirement", fontsize=8.6, color="#8A4B10", va="bottom",
            ha="left", linespacing=1.25, weight="bold", clip_on=True)
    ax.annotate("", xy=(1.0, END_DY_LO), xytext=(1.0, END_DY_HI),
                arrowprops=dict(arrowstyle="<->", lw=0.8, color="#8A4B10", mutation_scale=7))
    ax.text(0.5, 1e7, "range\n10$^6$–10$^8$", fontsize=7.9, color="#8A4B10", ha="right", va="center",
            linespacing=1.25, clip_on=True)
    ax.annotate("", xy=(RET_DY_LO, 2.8e8), xytext=(RET_DY, 2.8e8),
                arrowprops=dict(arrowstyle="<->", lw=0.7, color="#8A4B10", mutation_scale=6))
    ax.text(1.17e-3, 2.2e8, "1 episode", fontsize=7.6, color="#8A4B10", ha="center", va="top", clip_on=True)
    ax.text(2.4e8, 3.2e9, "static tier\nrequirement", fontsize=8.6, color="#1F4C7A", va="bottom",
            ha="center", weight="bold", clip_on=True, linespacing=1.25)
    ax.annotate("", xy=(RET_ST_LO, 2.4e9), xytext=(1e10, 2.4e9),
                arrowprops=dict(arrowstyle="<->", lw=0.7, color="#1F4C7A", mutation_scale=6))
    ax.text(9.3e7, 2.0e9, "1 rebuild interval", fontsize=7.6, color="#1F4C7A", ha="center", va="top", clip_on=True)

    # ---- literature points with an endurance value
    for r in pts:
        if r["endurance_cycles"] is None:
            continue
        kind = marker_kind(r)
        col = COLOR.get(r["key"], C_BIN)
        j = JITTER.get(r["key"], 1.0)
        xr, yr_ = r["retention_s"] * j, r["endurance_cycles"] * j
        draw_point(ax, xr, yr_, kind, col)
        off, ha = OFFSET[r["key"]]
        tc = col if kind else C_BINT
        bb = dict(facecolor="white", alpha=0.62, edgecolor="none", boxstyle="round,pad=0.14") if kind == 0 else None
        ax.annotate(r["label"], (xr, yr_), textcoords="offset points",
                    xytext=off, fontsize=8.1 if kind else 7.9, color=tc, ha=ha, va="center",
                    weight="bold" if kind == 2 else "normal", linespacing=1.2, bbox=bb, zorder=8, clip_on=True)

    # ---- charge-storage cells without a reported endurance: drawn at the top edge, as in
    # the draft, but without the upward arrows (see caption)
    for r in pts:
        if r["endurance_cycles"] is not None:
            continue
        col = COLOR.get(r["key"], C_BIN)
        if r["retention_mode"] == "analog":
            ax.plot([r["retention_s"]], [FLOOR], "o", color=C_CH, mec="white", mew=0.7, ms=6.6, zorder=7)
        else:
            ax.plot([r["retention_s"]], [FLOOR], "o", mfc="white", mec=C_BIN, mew=1.2, ms=5.0, zorder=5)
        off, ha = OFFSET[r["key"]]
        an = r["retention_mode"] == "analog"
        ax.annotate(r["label"], (r["retention_s"], FLOOR), textcoords="offset points", xytext=off,
                    fontsize=8.2 if an else 7.9, color=C_CH if an else C_BINT, ha=ha, va="center",
                    weight="bold" if an else "normal", clip_on=True)

    # ---- this work (open squares, as in the draft)
    tw = THIS_WORK
    ax.plot([tw["fecap_ret"]], [tw["fecap_end"]], "s", ms=6.2, mfc="none", mec=C_TW, mew=1.4, zorder=8)
    ax.annotate("this work\nFeCAP", (tw["fecap_ret"], tw["fecap_end"]), textcoords="offset points",
                xytext=(-9, -4), fontsize=8.3, color=C_TW, ha="right", va="center", weight="bold",
                linespacing=1.2, clip_on=True)
    ax.plot([tw["decap_ret"]], [tw["decap_end"]], "s", ms=6.2, mfc="none", mec=C_TW, mew=1.4, zorder=8)
    ax.annotate("this work\nDeCAP", (tw["decap_ret"], tw["decap_end"]),
                textcoords="offset points", xytext=(9, 0), fontsize=8.0, color=C_TW, ha="left",
                va="center", weight="bold", linespacing=1.2, clip_on=True)

    # ---- axes, legend
    ax.set_xlabel("Retention (s)", fontsize=9, fontweight="bold")
    ax.set_ylabel("Write endurance (cycles)", fontsize=9, fontweight="bold")
    ax.tick_params(axis="both", which="major", labelsize=9, pad=3.2, width=0.8, length=3.8)
    sec = ax.secondary_xaxis("top"); sec.set_xscale("log")
    sec.set_xticks([v for v, _ in LM]); sec.set_xticklabels([t for _, t in LM], fontsize=7.4)
    sec.tick_params(length=2.6, width=0.6, pad=2.0, labelsize=7.4)
    leg = [Line2D([], [], marker="o", ls="none", ms=6.4, color="#444444", mec="white", mew=0.6,
                  label="both axes in analog mode"),
           Line2D([], [], marker="o", ls="none", ms=6.0, mfc="#444444", fillstyle="left", mec="#444444",
                  mew=1.2, label="retention analog, endurance binary"),
           Line2D([], [], marker="o", ls="none", ms=5.0, mfc="white", mec=C_BIN, mew=1.2,
                  label="both axes in binary mode")]
    l1 = ax.legend(handles=leg, loc="lower left", fontsize=7.6, frameon=False, handletextpad=0.4,
                   borderaxespad=0.3, labelspacing=0.26, bbox_to_anchor=(0.01, 0.005),
                   title="measurement mode", title_fontsize=8.0, alignment="left")
    ax.add_artist(l1)
    for lab in ax.get_xticklabels() + ax.get_yticklabels():
        lab.set_fontweight("bold"); lab.set_fontsize(9)
    for lab in sec.get_xticklabels():
        lab.set_fontweight("bold")

    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / "fig4f.png", dpi=300, bbox_inches="tight", pad_inches=0.08)
    fig.savefig(OUT / "fig4f.pdf", bbox_inches="tight", pad_inches=0.08)
    print("ok")


if __name__ == "__main__":
    main()
