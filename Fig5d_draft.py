import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
from matplotlib.lines import Line2D
from pathlib import Path

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
YR, DAY, WEEK = 3.156e7, 8.64e4, 6.05e5

RET_ST_LO, RET_ST_HI, END_ST = 10 * DAY, 1e4 * DAY, 1e1
RET_DY_LO, RET_DY, END_DY_LO, END_DY_HI = 3.7e-5, 3.7e-2, 1e6, 1e8

Y_MAX = 1e11
ARROW_TOP = 8.0e10  # just below y-max so arrowheads stay inside the frame

fig, ax = plt.subplots(figsize=(5.55, 4.60))
fig.subplots_adjust(left=0.155, right=0.965, top=0.90, bottom=0.145)
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlim(1e-5, 1e10); ax.set_ylim(1e2, Y_MAX)

ax.add_patch(Rectangle((RET_ST_LO, END_ST), 1e11, 1e14, fc=C_STAT, alpha=0.26, ec="none", zorder=0))
ax.add_patch(Rectangle((RET_DY, END_DY_LO), 1e11, 1e14, fc=C_DYN, alpha=0.30, ec="none", zorder=0))
ax.plot([RET_DY, 1e11], [END_DY_HI, END_DY_HI], color="#8A4B10", lw=0.7,
        ls=(0, (4, 2.5)), zorder=2, alpha=0.85)
#ax.plot([RET_ST_HI, RET_ST_HI], [END_ST, 1e12], color="#1F4C7A", lw=0.7,
#        ls=(0, (4, 2.5)), zorder=2, alpha=0.85)
ax.add_patch(Rectangle((RET_ST_LO, END_DY_LO), 1e11, 1e14, fc="none", ec="#4A4A4A",
                       lw=0.9, hatch="////", alpha=0.7, zorder=2))
ax.axvspan(RET_DY_LO, RET_DY, color=C_DYN, alpha=0.13, lw=0, zorder=0)
for xv in (RET_DY_LO, RET_DY):
    ax.plot([xv, xv], [1e1, Y_MAX], color="#8A4B10", lw=0.7, ls=(0, (2, 2)), zorder=1)
LM = [(1e-3, "1 ms"), (1, "1 s"), (3.6e3, "1 h"), (DAY, "1 day"), (YR, "1 yr"), (10 * YR, "10 yr")]
for xv, _ in LM:
    ax.axvline(xv, color="#9AA0A6", lw=0.4, ls=(0, (1, 2.5)), alpha=0.5, zorder=0)

ax.text(5e-5, 4e8, "dynamic tier\nrequirement", fontsize=8.6, color="#8A4B10",
        va="bottom", ha="left", linespacing=1.25, weight="bold", clip_on=True)
#ax.text(5.5e-5, 2.0e3, "endur. $\\geq$(k+repl.)$\\times Q_{day}\\times$365$\\times$Y\n"
#                        "reten. $\\geq$1 re-ranking episode",
#        fontsize=5.8, color="#8A4B10", va="top", ha="left", linespacing=1.3)
ax.annotate("", xy=(1.0, END_DY_LO), xytext=(1.0, END_DY_HI),
            arrowprops=dict(arrowstyle="<->", lw=0.8, color="#8A4B10", mutation_scale=7))
ax.text(2, 1e7, "range\n10$^6$–10$^8$", fontsize=7.9, color="#8A4B10",
        ha="left", va="center", linespacing=1.25, clip_on=True)
#ax.text(4e-2, 3.2e1, "one re-ranking episode\n$N(t_{bcast}$+$t_{sense}$+$t_{dig})$ + $Wt_{write}$",
#        fontsize=7.7, color="#8A4B10", ha="left", va="center", linespacing=1.3, clip_on=True)
ax.annotate("", xy=(RET_DY_LO, 2.8e8), xytext=(RET_DY, 2.8e8),
            arrowprops=dict(arrowstyle="<->", lw=0.7, color="#8A4B10", mutation_scale=6))
ax.text(1.17e-3, 2.2e8, "1 episode", fontsize=7.6, color="#8A4B10",
        ha="center", va="top", clip_on=True)
ax.text(9.3e7, 8e8, "static tier\nrequirement", fontsize=8.6, color="#1F4C7A",
        va="bottom", ha="center", weight="bold", clip_on=True, linespacing=1.25)
ax.annotate("", xy=(RET_ST_LO, 6.2e8), xytext=(1e10, 6.2e8),
            arrowprops=dict(arrowstyle="<->", lw=0.7, color="#1F4C7A", mutation_scale=6))
ax.text(9.3e7, 5.2e8, "1 rebuild interval", fontsize=7.6, color="#1F4C7A",
        ha="center", va="top", clip_on=True)
#ax.text(8e9, 1.4e1, "endur. $\\geq$1 write per index rebuild\nreten. $\\geq$rebuild interval",
#        fontsize=5.8, color="#1F4C7A", va="bottom", ha="right", linespacing=1.3)
#ax.annotate("", xy=(RET_ST_LO, 3.4e11), xytext=(RET_ST_HI, 3.4e11),
#            arrowprops=dict(arrowstyle="<->", lw=0.8, color="#1F4C7A", mutation_scale=7))
#ax.text(1e7, 4.6e11, "required retention: 10$^4$–10$^6$ queries", fontsize=5.9,
#        color="#1F4C7A", ha="center", va="bottom")


# ret, end, colour, label, offset, ha, mode: 2 = both analog, 1 = retention only, 0 = binary
PTS = [
  (0.9e5,    0.9e4,  C_FE, "28 nm HKMG FeFET, 3-bit MLC",     (38, 10), "right", 2),
  (3e3,    1e8,  C_RR, "SrCoO$_x$ TPT-RAM",               (10,  10), "right", 2),
  (3.15e8, 1e3,  C_RR, "HfO$_2$ RRAM,\nmulti-level ISPVA", (20, -14), "right", 2),
  (WEEK,   1e6,  C_PC, "MLC PCM, 3 bit/cell",             (-28, 9), "center", 1),
  (1e3,    1e5,  C_FL, "charge-trap memristor, 8 states", (-10,  0), "right",  1),
  (3.15e8, 2e7,  C_BIN, "ITO FeFET",                      (-10, 10), "right", 0),
  (3.15e8, 1e6,  C_BIN, "MoS$_2$ FeFET\n(1 $\\mu$s write)",   (0, 17), "center", 0),
  (1e5,    1e7,  C_BIN, "SnS$_2$ FeFET",                  (-2, 9), "right", 0),
  (1e6,    1e6,  C_BIN, "IGZO/HZO FeFET",                 (8, -8),"right", 0),
  (1e4,    1e4,  C_BIN, "self-rectifying HfO$_2$ RRAM",   (-6,  -3), "right", 0),
  (1.1e5,    1.1e4,  C_BIN, "MoS$_2$ charge-trap flash",      (10,  -5), "left",  0),
]
for ret, end, col, lab, off, ha, mode in PTS:
    kw = dict(ms=5.6, mec=col, mew=1.3, ls="none", zorder=6)
    if mode == 2:
        ax.plot([ret], [end], "o", color=col, mec="white", mew=0.7, ms=6.6, zorder=7)
        tc, fs, wt = col, 8.2, "bold"
    elif mode == 1:
        ax.plot([ret], [end], "o", mfc=col, fillstyle="left", ms=6.2, mec=col,
                mew=1.3, ls="none", zorder=7)
        tc, fs, wt = col, 8.1, "normal"
    else:
        ax.plot([ret], [end], "o", mfc="white", mec=C_BIN, mew=1.2, ms=5.0,
                ls="none", zorder=5)
        tc, fs, wt = C_BINT, 7.9, "normal"
    bb = dict(facecolor="white", alpha=0.62, edgecolor="none",
              boxstyle="round,pad=0.14") if mode == 0 else None
    ax.annotate(lab, (ret, end), textcoords="offset points", xytext=off,
                fontsize=fs, color=tc, ha=ha, va="center", linespacing=1.2,
                weight=wt, bbox=bb, zorder=8, clip_on=True)

#ax.text(1.3e6, 6e9, "inside the corner:\nonly binary\nmeasurements",
#        fontsize=6.4, color=C_TW, ha="left", va="center", linespacing=1.3, weight="bold")

CHARGE = [(1e-4, "Si 2T gain cell", -13, 10, 14), (1e1, "MoS$_2$ 2T1C", -13, 2, 0),
          (1.3e2, "IGZO 2T1C gain cell", -26, 2, 0)]
FLOOR = 1.5e10
for ret, lab, dy, mode, dx in CHARGE:
    cc = C_CH if mode == 2 else C_BIN
    if mode == 2:
        ax.plot([ret], [FLOOR], "o", color=C_CH, mec="white", mew=0.7, ms=6.6, zorder=7)
    else:
        ax.plot([ret], [FLOOR], "o", mfc="white", mec=C_BIN, mew=1.2, ms=5.0, zorder=5)
    ax.add_patch(FancyArrowPatch((ret, FLOOR * 1.6), (ret, ARROW_TOP), arrowstyle="-|>",
                                 mutation_scale=7, lw=0.9, color=cc, zorder=6, clip_on=True))
    ax.annotate(lab, (ret, FLOOR), textcoords="offset points", xytext=(dx, dy),
                fontsize=8.2 if mode == 2 else 7.9,
                color=C_CH if mode == 2 else C_BINT, ha="center", va="center",
                weight="bold" if mode == 2 else "normal", clip_on=True)
#ax.text(1.35e-5, 4.2e11, "charge storage: no fatigue mechanism,\nendurance not a binding constraint",
#        fontsize=5.9, color=C_CH, ha="left", va="top", linespacing=1.25)

# IGZO 4T2C retention: measured for 10 h (3.6e4 s); the stored-value drift stayed
# below the dynamic tier's retrieval-quality tolerance (0.4 V, Fig. 2c) throughout,
# so both axes are lower bounds (arrows), like the other capacitive points.
RET_IGZO_TW = 3.6e4
ax.plot([RET_IGZO_TW], [FLOOR], "s", ms=6.2, mfc="none", mec=C_TW, mew=1.4, zorder=8)
ax.annotate("this work\nIGZO 4T2C", (RET_IGZO_TW, FLOOR), textcoords="offset points",
            xytext=(30, 0), fontsize=8.3, color=C_TW, ha="left", va="center",
            weight="bold", linespacing=1.2, clip_on=True, zorder=9,
            bbox=dict(facecolor="white", alpha=0.8, edgecolor="none", boxstyle="round,pad=0.15"))
ax.add_patch(FancyArrowPatch((RET_IGZO_TW, FLOOR * 1.6), (RET_IGZO_TW, ARROW_TOP), arrowstyle="-|>",
                             mutation_scale=8, lw=1.1, color=C_TW, zorder=8, clip_on=True))
ax.add_patch(FancyArrowPatch((RET_IGZO_TW * 1.7, FLOOR), (RET_IGZO_TW * 7, FLOOR), arrowstyle="-|>",
                             mutation_scale=8, lw=1.1, color=C_TW, zorder=8, clip_on=True))
ax.plot([3e8], [1e5], "s", ms=6.2, mfc="none", mec=C_TW, mew=1.4, zorder=7)
ax.annotate("this work\nFeFET", (2e6, 1.5e5), textcoords="offset points", xytext=(10, 3),
            fontsize=8.3, color=C_TW, ha="left", va="center", weight="bold",
            linespacing=1.2, clip_on=True)

ax.set_xlabel("", fontsize=9, fontweight="bold")
ax.set_ylabel("", fontsize=9, fontweight="bold")
ax.tick_params(axis="both", which="major", labelsize=9, pad=3.2, width=0.8, length=3.8)
sec = ax.secondary_xaxis("top"); sec.set_xscale("log")
sec.set_xticks([v for v, _ in LM]); sec.set_xticklabels([t for _, t in LM], fontsize=7.4)
sec.tick_params(length=2.6, width=0.6, pad=2.0, labelsize=7.4)

g = "#555555"
leg1 = [Line2D([], [], marker="o", ls="none", ms=6.4, color="#444444", mec="white",
               mew=0.6, label="both axes in analog mode"),
        Line2D([], [], marker="o", ls="none", ms=6.0, mfc="#444444", fillstyle="left",
               mec="#444444", mew=1.2, label="retention analog, endurance binary"),
        Line2D([], [], marker="o", ls="none", ms=5.0, mfc="white", mec=C_BIN, mew=1.2,
               label="both axes in binary mode")]
l1 = ax.legend(handles=leg1, loc="lower left", fontsize=7.9, frameon=False,
               handletextpad=0.4, borderaxespad=0.3, labelspacing=0.26,
               bbox_to_anchor=(0.01, 0.005), title="measurement mode",
               title_fontsize=8.1, alignment="left")
l1._legend_box.align = "left"
ax.add_artist(l1)
for lab in ax.get_xticklabels() + ax.get_yticklabels():
    lab.set_fontweight("bold")
    lab.set_fontsize(9)
for lab in sec.get_xticklabels():
    lab.set_fontweight("bold")
fig.savefig(Path(__file__).resolve().parent / "Fig5d_v2.png", dpi=300,
            bbox_inches="tight", pad_inches=0.08)
print("ok")