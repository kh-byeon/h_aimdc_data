# -*- coding: utf-8 -*-
"""4T2C 거리연산 논문 그림 초안 생성기.

사용법:
    python plot_figures.py                      # 같은 폴더의 xlsx 를 읽어 figures/ 에 PNG 생성
    python plot_figures.py path/to/book.xlsx    # 경로 지정

Python 3.7 호환 (walrus / f-string= 미사용). 필요: pandas, matplotlib, openpyxl.
Fig5 는 Fig5_distance_map_2D 시트가 채워져 있을 때만 그려진다.
"""
from __future__ import print_function

import os
import sys

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

XLSX = sys.argv[1] if len(sys.argv) > 1 else "4t2c_distance_paper_20260904.xlsx"
OUTDIR = os.path.join(os.path.dirname(os.path.abspath(XLSX)) or ".", "figures")
DPI = 300

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 8,
    "axes.linewidth": 0.8,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 6.5,
    "legend.frameon": False,
    "lines.linewidth": 1.0,
    "savefig.bbox": "tight",
})

ROWC = {0: "#1f77b4", 1: "#d62728", 2: "#2ca02c", 3: "#9467bd"}


def load(sheet):
    """헤더는 2 행, 1 행은 설명 주석."""
    try:
        df = pd.read_excel(XLSX, sheet_name=sheet, header=1)
    except Exception as e:
        print("  ! %s 읽기 실패: %s" % (sheet, e))
        return None
    if df.empty:
        return None
    return df


def save(fig, name):
    if not os.path.isdir(OUTDIR):
        os.makedirs(OUTDIR)
    p = os.path.join(OUTDIR, name)
    fig.savefig(p, dpi=DPI)
    plt.close(fig)
    print("  ->", p)


# --------------------------------------------------------------- Fig 2
def fig2():
    df = load("Fig2_notch_curves")
    if df is None:
        return
    cells = sorted(df["cell"].unique())
    n = len(cells)
    ncol = 4
    nrow = int(np.ceil(n / float(ncol)))
    fig, axes = plt.subplots(nrow, ncol, figsize=(2.0 * ncol, 1.7 * nrow), sharex=True)
    axes = np.atleast_1d(axes).ravel()
    for ax, cell in zip(axes, cells):
        d = df[df["cell"] == cell]
        ws = sorted(d["w_store_V"].unique())
        cm = plt.cm.viridis(np.linspace(0, 0.9, len(ws)))
        for w, c in zip(ws, cm):
            s = d[d["w_store_V"] == w].sort_values("v_V")
            ax.plot(s["v_V"], s["I_uA"], "-", color=c, label="%+.1f" % w)
        ax.set_title(cell, fontsize=8)
        ax.tick_params(direction="in", top=True, right=True)
    for ax in axes[n:]:
        ax.axis("off")
    axes[0].legend(title="w (V)", title_fontsize=6.5, ncol=2, loc="upper center")
    for ax in axes[max(0, n - ncol):n]:
        ax.set_xlabel("differential SL amplitude $v$ (V)")
    for i in range(0, n, ncol):
        axes[i].set_ylabel(r"RBL current ($\mu$A)")
    fig.suptitle("Fig 2  Notch response of the 4T2C cell", fontsize=9, y=1.01)
    save(fig, "fig2_notch_curves.png")


# --------------------------------------------------------------- Fig 3
def fig3():
    df = load("Fig3_vnotch_vs_w")
    fitdf = load("Fig3b_alpha_fit")
    adf = load("Fig3c_alpha_percell")
    if df is None:
        return
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(6.6, 2.6),
                                  gridspec_kw={"width_ratios": [2, 1]})
    for cell in sorted(df["cell"].unique()):
        d = df[df["cell"] == cell].sort_values("w_store_V")
        ax.errorbar(d["w_store_V"], d["v_notch_V"], yerr=d["v_notch_se_V"],
                    marker="o", ms=3, capsize=2, lw=0.9, label=cell)
    if fitdf is not None:
        f = fitdf[(fitdf["scope"] == "cell") & (fitdf["cell"] == "R2C0")]
        if len(f):
            w = np.linspace(df["w_store_V"].min(), df["w_store_V"].max(), 20)
            ax.plot(w, float(f["slope_V_per_V"].iloc[0]) * w + float(f["intercept_V"].iloc[0]),
                    "k--", lw=1.0,
                    label="fit R2C0 ($R^2$=%.3f)" % float(f["r2"].iloc[0]))
    ax.set_xlabel("stored value $w$ (V)")
    ax.set_ylabel("notch position $v_0$ (V)")
    ax.tick_params(direction="in", top=True, right=True)
    ax.legend(ncol=2, loc="upper right")
    ax.set_title("(a) $v_0 = -w/\\alpha + b$", fontsize=8, loc="left")

    if adf is not None:
        a = adf.sort_values("cell")
        ax2.bar(range(len(a)), a["alpha"], color="#4c72b0", width=0.65)
        med = float(np.median(a["alpha"]))
        ax2.axhline(med, color="k", ls="--", lw=0.9,
                    label="median %.3f" % med)
        ax2.set_xticks(range(len(a)))
        ax2.set_xticklabels(a["cell"], rotation=60, fontsize=6)
        ax2.set_ylabel(r"coupling ratio $\alpha$")
        ax2.tick_params(direction="in", top=True, right=True)
        ax2.legend()
        ax2.set_title("(b) per-cell $\\alpha$", fontsize=8, loc="left")
    save(fig, "fig3_alpha_linearity.png")


# --------------------------------------------------------------- Fig 4
def fig4():
    df = load("Fig4_superposition")
    st = load("Fig4b_superposition_stats")
    if df is None:
        return
    rows = sorted(df["row"].unique())
    fig, axes = plt.subplots(1, len(rows), figsize=(1.85 * len(rows), 2.1),
                             sharex=True, sharey=True)
    axes = np.atleast_1d(axes)
    lo = min(df["code_pred"].min(), df["code_meas"].min())
    hi = max(df["code_pred"].max(), df["code_meas"].max())
    for ax, r in zip(axes, rows):
        d = df[df["row"] == r]
        bad = (st is not None) and float(st[st["row"] == r]["r2"].iloc[0]) < 0.5
        ax.plot([lo, hi], [lo, hi], "k-", lw=0.8, zorder=1)
        ax.scatter(d["code_pred"], d["code_meas"], s=6,
                   facecolors="none" if bad else ROWC[r],
                   edgecolors=ROWC[r], lw=0.6, zorder=2)
        ttl = "row %d" % r
        if st is not None:
            s = st[st["row"] == r].iloc[0]
            ttl += "\n$R^2$=%.3f  nRMSE=%.1f%%" % (s["r2"], 100 * s["nrmse"])
        ax.set_title(ttl, fontsize=7)
        ax.set_xlabel("predicted code")
        ax.tick_params(direction="in", top=True, right=True)
        ax.set_aspect("equal", adjustable="box")
    axes[0].set_ylabel("measured code")
    fig.suptitle("Fig 4  Superposition (prediction from 1-D calibration only)",
                 fontsize=9, y=1.06)
    save(fig, "fig4_superposition.png")

    cmp_ = load("Fig4c_mbl_compare")
    if cmp_ is not None:
        fig, ax = plt.subplots(figsize=(3.0, 2.2))
        for mbl, mk in ((-1.0, "o"), (-1.5, "s")):
            d = cmp_[cmp_["mbl_V"] == mbl].sort_values("row")
            ax.plot(d["row"], 100 * d["nrmse"], mk + "-", ms=4,
                    label="MBL %.1f V" % mbl)
        ax.set_xticks(sorted(cmp_["row"].unique()))
        ax.set_xlabel("row")
        ax.set_ylabel("normalized RMSE (%)")
        ax.tick_params(direction="in", top=True, right=True)
        ax.legend()
        ax.set_title("Fig 4 inset  read-bias dependence", fontsize=8, loc="left")
        save(fig, "fig4c_mbl_compare.png")


# --------------------------------------------------------------- Fig 5
def fig5():
    df = load("Fig5_distance_map_2D")
    if df is None or "x0" not in [c.lower() for c in df.columns]:
        print("  (Fig5 시트 비어 있음 — grid 스윕 결과를 먼저 채우세요)")
        return
    df.columns = [c.lower() for c in df.columns]
    rows = sorted(df["row"].unique())
    xs = np.sort(df["x0"].unique())
    ys = np.sort(df["x1"].unique())
    grids = {}
    for r in rows:
        d = df[df["row"] == r]
        g = np.full((len(ys), len(xs)), np.nan)
        for _, e in d.iterrows():
            g[np.searchsorted(ys, e["x1"]), np.searchsorted(xs, e["x0"])] = e["code"]
        grids[r] = g

    fig, axes = plt.subplots(1, len(rows) + 1,
                             figsize=(1.9 * (len(rows) + 1), 2.1))
    ext = [xs.min(), xs.max(), ys.min(), ys.max()]
    for ax, r in zip(axes, rows):
        im = ax.imshow(grids[r], origin="lower", extent=ext, aspect="auto",
                       cmap="viridis")
        ax.contour(xs, ys, grids[r], 8, colors="w", linewidths=0.4, alpha=0.6)
        ax.set_title("row %d" % r, fontsize=8)
        ax.set_xlabel("$x_0$ (V)")
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
    axes[0].set_ylabel("$x_1$ (V)")
    stack = np.dstack([grids[r] for r in rows])
    amin = np.argmin(stack, axis=2)
    axm = axes[-1]
    axm.imshow(amin, origin="lower", extent=ext, aspect="auto",
               cmap=matplotlib.colors.ListedColormap([ROWC[r] for r in rows]))
    axm.set_title("hardware argmin", fontsize=8)
    axm.set_xlabel("$x_0$ (V)")
    fig.suptitle("Fig 5  2-D distance map and decision boundary", fontsize=9, y=1.06)
    save(fig, "fig5_distance_map.png")


# --------------------------------------------------------------- Fig 6
def fig6():
    s = load("Fig6b_argmin_summary")
    if s is None:
        return
    if s["acc_cal"].isna().all():
        d = load("Fig6_argmin_detail")
        if d is None:
            return
        s = d.groupby("combo").agg(
            acc_cal=("match_cal", "mean"), acc_euclid=("match_euclid", "mean"),
            acc_ideal=("match_ideal", "mean")).reset_index()
    fig, ax = plt.subplots(figsize=(4.4, 2.4))
    combos = list(s["combo"])
    x = np.arange(len(combos))
    w = 0.26
    for i, (col, lab, c) in enumerate((
            ("acc_cal", u"① $\\kappa$-weighted", "#1f77b4"),
            ("acc_euclid", u"② Euclidean (cal. centers)", "#ff7f0e"),
            ("acc_ideal", u"③ software (nominal $\\alpha$)", "#2ca02c"))):
        ax.bar(x + (i - 1) * w, 100 * s[col], w, label=lab, color=c)
    ax.axhline(50, color="k", ls="--", lw=0.9)
    ax.text(len(combos) - 0.5, 51.5, "chance", ha="right", fontsize=6)
    ax.set_xticks(x)
    ax.set_xticklabels([c.replace("_vs_", " vs ").replace("row", "row ")
                        for c in combos], fontsize=7)
    ax.set_ylabel("argmin agreement (%)")
    ax.set_ylim(0, 105)
    ax.tick_params(direction="in", top=True, right=True)
    ax.legend(ncol=1, loc="lower right")
    ax.set_title("Fig 6  Nearest-neighbour accuracy (n = 96)", fontsize=8, loc="left")
    save(fig, "fig6_argmin_accuracy.png")


# --------------------------------------------------------------- Fig 7
def fig7():
    c = load("Fig7_cell_cal")
    f = load("Fig7b_floor_error")
    if c is None:
        return
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.3))
    fig.subplots_adjust(wspace=0.42)
    a, b, d = axes
    a.hist(c["kappa_code_per_V2"], bins=10, color="#4c72b0", edgecolor="w")
    a.axvline(c["kappa_code_per_V2"].mean(), color="k", ls="--", lw=0.9,
              label="mean %.0f" % c["kappa_code_per_V2"].mean())
    a.set_xlabel(r"curvature $\kappa$ (code/V$^2$)")
    a.set_ylabel("count")
    a.legend()
    a.set_title("(a) $\\kappa$ spread %.1f$\\times$" % (
        c["kappa_code_per_V2"].max() / c["kappa_code_per_V2"].min()),
        fontsize=8, loc="left")

    for r in sorted(c["row"].unique()):
        s = c[c["row"] == r]
        b.scatter(s["w_store_V"], s["v0_V"], s=14, color=ROWC[r], label="row %d" % r)
    ww = np.linspace(c["w_store_V"].min(), c["w_store_V"].max(), 20)
    b.plot(ww, -ww / 0.588 + 0.0076, "k--", lw=0.9, label=r"$-w/\alpha+b$")
    b.set_xlabel("stored $w$ (V)")
    b.set_ylabel("calibrated $v_0$ (V)")
    b.legend(ncol=2)
    b.set_title("(b) calibrated centers", fontsize=8, loc="left")

    if f is not None:
        for r in sorted(f["row"].unique()):
            s = f[f["row"] == r].sort_values("pattern")
            d.plot(s["pattern"], s["delta_code"], "o-", ms=4,
                   color=ROWC[r], label="row %d" % r)
        d.axhline(0, color="k", lw=0.7)
        d.set_xticks(sorted(f["pattern"].unique()))
        d.set_xlabel("stored pattern")
        d.set_ylabel("floor error (code)")
        d.legend(ncol=2)
        d.set_title("(c) extrapolated $-$ direct floor", fontsize=8, loc="left")
    for ax in axes:
        ax.tick_params(direction="in", top=True, right=True)
    fig.suptitle("Fig 7  Cell-to-cell variation", fontsize=9, y=1.06)
    save(fig, "fig7_cell_variation.png")


# --------------------------------------------------------------- Sup
def sup():
    b = load("SupB_wwl_pinscan")
    if b is not None:
        pins = sorted(b["pin"].unique())
        rows = sorted(b["row"].unique())
        m = np.zeros((len(rows), len(pins)))
        for _, e in b.iterrows():
            m[rows.index(e["row"]), pins.index(e["pin"])] = e["dw_V"]
        fig, ax = plt.subplots(figsize=(3.4, 2.0))
        im = ax.imshow(m, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
        ax.set_xticks(range(len(pins)))
        ax.set_xticklabels(["A%d" % p for p in pins])
        ax.set_yticks(range(len(rows)))
        ax.set_yticklabels(["row %d" % r for r in rows])
        ax.set_xlabel("pulsed WWL pin")
        fig.colorbar(im, ax=ax, fraction=0.046, label=r"$\Delta w$ (V)")
        ax.set_title("Sup B  WWL write-select degeneracy", fontsize=8, loc="left")
        save(fig, "supB_wwl_pinscan.png")

    c = load("SupC_mblscan")
    if c is not None:
        fig, ax = plt.subplots(figsize=(3.2, 2.2))
        for r in sorted(c["row"].unique()):
            s = c[c["row"] == r].sort_values("mbl_V")
            ax.plot(s["mbl_V"], s["code"], "o-", ms=3, color=ROWC[r],
                    label="row %d" % r)
        ax.set_xlabel("MBL (V)   [all other nodes at 0 V]")
        ax.set_ylabel("ADC code")
        ax.tick_params(direction="in", top=True, right=True)
        ax.legend(ncol=2)
        ax.set_title("Sup C  bias-independent floor current", fontsize=8, loc="left")
        save(fig, "supC_mblscan.png")

    a = load("SupA_condition_scan")
    if a is not None and "nrmse" in a.columns:
        d = a[(a["run"] == "scan_1602") & a["nrmse"].notna()]
        if len(d):
            fig, ax = plt.subplots(figsize=(4.0, 2.2))
            ax.bar(range(len(d)), d["nrmse"], color="#4c72b0")
            lab = ["mbl%.1f/span%.1f/w%.2f/half%.1f" % (
                e["mbl_V"], e["span_V"], e["w_V"], e["half_V"])
                for _, e in d.iterrows()]
            ax.set_xticks(range(len(d)))
            ax.set_xticklabels(lab, rotation=75, fontsize=5)
            ax.set_ylabel("nRMSE")
            ax.tick_params(direction="in", top=True, right=True)
            ax.set_title("Sup A  condition scan (paired)", fontsize=8, loc="left")
            save(fig, "supA_condition_scan.png")


if __name__ == "__main__":
    print("reading", XLSX)
    for fn in (fig2, fig3, fig4, fig5, fig6, fig7, sup):
        print("[%s]" % fn.__name__)
        try:
            fn()
        except Exception as exc:
            print("  ! 실패:", exc)
    print("done ->", OUTDIR)
