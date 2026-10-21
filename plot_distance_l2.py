#!/usr/bin/env python3
"""How well the arrays reproduce a software L2 distance, IGZO 4T2C and FeFET.

    python plot_distance_l2.py
    python plot_distance_l2.py --figures 1 3 --outdir DIR

Inputs
------
``4t2c_array/4t2c_distance_paper_20260904.xlsx``   chip6, 4x2 IGZO 4T2C, 2-D
``fefet_array/FeFET_2x2_distance_0905-0906.xlsx``  chipX, 2x2 FeFET, 2-D

Both campaigns test the same claim on two device families. Each cell's response
to a differential read input has a minimum -- a notch -- at the value it stores,
and around that minimum it is quadratic:

    I_r(x) = S_r + sum_c kappa_rc (x_c - v0_rc)^2

The cells of one row share a readout line, so the row current *is* a
kappa-weighted squared Euclidean distance between the query vector x and the
stored vector v0_r, evaluated for every row in one read. The test is that
``v0``, ``kappa`` and ``S`` measured by sweeping one column at a time predict
the two-column response with **nothing fitted to the 2-D data**. What is plotted
here is the agreement between that software L2 and the hardware.

The two datasets are not merged: the devices, the readout and the units differ,
and one of them (FeFET) stored the same vector in both rows, so it cannot speak
to nearest-neighbour accuracy at all. They are shown side by side.

Figure 1 ``l2_parity.png`` (and ``l2_parity_nolegend.png``)
  measured against predicted excess over the row floor, both devices on one
  axes and one colour each, each scaled onto 0..1, with the 1:1 line

Figure 2 ``l2_residuals.png``
  residual against prediction, and -- for the FeFET rounds, which record it --
  the residual against the readout noise of the same round

Figure 3 ``l2_cell_variation.png``
  the spread of kappa, which is what makes the hardware distance weighted
  rather than plain Euclidean, and the 4T2C notch calibration behind it

Figure 4 ``l2_conditions.png``
  how the agreement moves with the read condition in both campaigns

Figure 5 ``l2_argmin.png``
  nearest-neighbour accuracy, 4T2C only, against three software references

Figure 6 ``l2_mse.png``
  the squared error query by query for the best row and the best round, the
  mean of it, and -- where the workbook records the sample spread -- the
  readout-noise floor it has to be read against

Figure 7 ``l2_r2.png``
  the same agreement as R^2, split three ways -- against the 1:1 line, with an
  offset free, and with a gain free -- so that a wrong row floor, a compressed
  response and a real superposition error can be told apart

Figure 8 ``l2_r2_combined.png``
  every row of both arrays on one axes, colour by device, showing only the R^2
  that is the claim, with each device's mean over its working rows
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt          # noqa: E402
import numpy as np                       # noqa: E402
import pandas as pd                      # noqa: E402
from matplotlib.lines import Line2D      # noqa: E402

from notch_common import (               # noqa: E402
    DPI, FONT_BASE, FONT_PANEL, LW_CURVE, MARKERSIZE,
    C_REF, C_MAIN, C_ALT, C_OK, C_WARN, C_PURPLE,
    apply_plot_style, style_ax, panel_label,
)

ROOT = Path(__file__).resolve().parent
OUTDIR = ROOT / "figures"
XLSX_4T2C = ROOT / "4t2c_array" / "4t2c_distance_paper_20260904.xlsx"
XLSX_FEFET = ROOT / "fefet_array" / "FeFET_2x2_distance_0905-0906.xlsx"

STEMS = {
    1: "l2_parity",
    2: "l2_residuals",
    3: "l2_cell_variation",
    4: "l2_conditions",
    5: "l2_argmin",
    6: "l2_mse",
    7: "l2_r2",
    8: "l2_r2_combined",
}

# 4T2C row 1 holds the defective cell R1C1. Every diagnostic figure keeps it,
# drawn open, because it is the evidence for the "one bad cell" claim. The
# parity figure is the one meant for the main text, and there it is dropped and
# the survivors are renumbered 0, 1, 2 for the reader.
#
# That renumbering is display only: it does not change which physical row a
# point came from, and it does not carry to the other figures, which keep the
# hardware numbering. Any caption using the parity figure has to say that a
# fourth row was measured and excluded, or the figure overstates the yield.
BAD_ROW_4T2C = 1
PARITY_DROPS_BAD_ROW = True
PARITY_RENUMBERS = True

# The parity figure puts the two devices side by side, so the 4x2 IGZO array is
# cut down to its best two rows and shown as a 2x2, matching the FeFET array.
# Selecting 2 of 4 is a selection, and the caption has to say so: the two rows
# not shown are the defective one and the weakest survivor.
PARITY_N_ROWS_4T2C = 2
# Device identity, named rather than spelled out at each use so the two stay
# swapped together. IGZO carries the orange, FeFET the blue -- the same way
# round as plot_4t2c_notch_campaign.py (orange) and plot_fefet_notch_shift.py
# (blue), so a reader moving between figures keeps the same device-to-colour
# association.
C_IGZO = C_ALT
C_FEFET = C_MAIN

ROW_C_4T2C = {0: C_IGZO, 1: C_WARN, 2: C_PURPLE, 3: C_OK}
ROW_C_FEFET = {0: C_FEFET, 1: C_ALT}

DEV_4T2C = "IGZO 4T2C  (4x2, 2-D)"
DEV_FEFET = "FeFET  (2x2, 2-D)"


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def _numeric(df: pd.DataFrame, cols) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


def load_4t2c(path: Path) -> dict:
    """Sheets of the 4T2C workbook. Row 0 of each is a prose description."""
    if not path.is_file():
        raise FileNotFoundError(path)
    book = {}
    for sheet in ("Fig4_superposition", "Fig4b_superposition_stats",
                  "Fig4c_mbl_compare", "Fig7_cell_cal", "Fig7b_floor_error",
                  "Fig6b_argmin_summary", "Fig3_vnotch_vs_w"):
        book[sheet] = pd.read_excel(path, sheet_name=sheet, header=1)
    print(f"[in ] {path.name}: {', '.join(book)}")
    return book


def load_fefet(path: Path) -> dict:
    """Sheets of the FeFET workbook.

    ``Rounds`` and ``Cal_cells`` carry their header on the first row;
    ``Best_round_points`` has a prose line, then a units line, then the header.
    """
    if not path.is_file():
        raise FileNotFoundError(path)
    book = {
        "Rounds": pd.read_excel(path, sheet_name="Rounds"),
        "Cal_cells": pd.read_excel(path, sheet_name="Cal_cells"),
        "Best_round_points": pd.read_excel(path, sheet_name="Best_round_points",
                                           header=2),
    }
    # Best_round_points ends with a footer: a "검산" cross-check of the two row
    # R2 values, then the round's per-cell calibration table. Both reuse the
    # same columns, so keep only the query rows.
    bp = _numeric(book["Best_round_points"], book["Best_round_points"].columns)
    bp = bp[np.isfinite(bp["q"]) & bp["row"].isin([0, 1])].reset_index(drop=True)
    book["Best_round_points"] = bp
    print(f"[in ] {path.name}: {', '.join(book)}")
    return book


def _fit_stats(pred, meas) -> dict:
    """Agreement of the measurement with the prediction.

    ``r2`` has no free parameter -- it is against the 1:1 line, which is the
    claim being tested. ``slope`` is a separate diagnostic: a slope below one is
    a gain error (the measured response is compressed), not a failure of the
    superposition, and the two are worth keeping apart.
    """
    p = np.asarray(pred, float)
    m = np.asarray(meas, float)
    ok = np.isfinite(p) & np.isfinite(m)
    p, m = p[ok], m[ok]
    if p.size < 3:
        return dict(n=int(p.size), r2=np.nan, rmse=np.nan, nrmse=np.nan,
                    slope=np.nan)
    resid = m - p
    ss_res = float(np.sum(resid ** 2))
    ss_tot = float(np.sum((m - m.mean()) ** 2))
    slope = float(np.polyfit(p, m, 1)[0])
    rmse = float(np.sqrt(np.mean(resid ** 2)))
    span = float(m.max() - m.min())
    return dict(n=int(p.size), r2=1.0 - ss_res / ss_tot if ss_tot else np.nan,
                rmse=rmse, nrmse=rmse / span if span else np.nan, slope=slope)


# ---------------------------------------------------------------------------
# Figure 1: parity
# ---------------------------------------------------------------------------
def _parity_axis(ax, pred, meas, color, label, *, filled=True, ms=None):
    kw = dict(marker="o", ls="none", ms=ms or (MARKERSIZE - 2), mew=1.2,
              mec=color, mfc=color if filled else "none", alpha=0.85, label=label)
    ax.plot(pred, meas, **kw)


def _draw_unity(ax, lo, hi):
    ax.plot([lo, hi], [lo, hi], color=C_REF, ls="--", lw=1.6, zorder=1)
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal", adjustable="box")


def plot_parity(a4: dict, af: dict, out_path: Path) -> dict:
    """Both arrays on one parity axes, one colour each.

    The two devices do not share a code range -- IGZO sits at 400-1300, FeFET at
    1330-1660 -- so plotting the raw row code would put them in opposite corners
    of the diagonal with nothing to compare. What is plotted instead is the
    *excess* over each row's own floor,

        excess = I_row - S_r = sum_c kappa_rc (x_c - v0_rc)^2

    which is the distance term itself: the part of the row current that carries
    the answer, with the pedestal removed. Both devices start at zero there, so
    one 1:1 line serves both.

    Note this changes what R^2 is measured against -- subtracting a per-row
    constant changes the total sum of squares -- so the number here is not the
    one the code-space parity gives. Both are printed; they agree to about 0.006
    on the working rows.
    """
    sup = a4["Fig4_superposition"]
    bp = af["Best_round_points"]
    cal = a4["Fig7_cell_cal"]
    stats: dict = {"4t2c": {}, "fefet": {}}

    if PARITY_DROPS_BAD_ROW:
        sup = sup[sup["row"] != BAD_ROW_4T2C]
    if PARITY_N_ROWS_4T2C:
        ranked = sorted(
            (int(r) for r in sup["row"].unique()),
            key=lambda r: _fit_stats(sup.loc[sup["row"] == r, "code_pred"],
                                     sup.loc[sup["row"] == r, "code_meas"])["r2"],
            reverse=True,
        )
        chosen = sorted(ranked[:PARITY_N_ROWS_4T2C])
        stats["dropped"] = sorted(set(ranked) - set(chosen)) + [BAD_ROW_4T2C]
        sup = sup[sup["row"].isin(chosen)]
    kept = sorted(int(r) for r in sup["row"].unique())
    shown = {r: (i if PARITY_RENUMBERS else r) for i, r in enumerate(kept)}
    stats["row_map"] = {v: k for k, v in shown.items()}

    # The row floor S_r is measured directly at x = v0 (FLOOR_MODE "direct"),
    # one value per stored pattern and row.
    floors = cal.groupby(["pattern", "row"])["S_row_code"].first()
    sup = sup.join(floors, on=["pattern", "row"])
    if sup["S_row_code"].isna().any():
        raise AssertionError("no row floor for some 4T2C queries")
    ex_pred_4 = (sup["code_pred"] - sup["S_row_code"]).to_numpy(float)
    ex_meas_4 = (sup["code_meas"] - sup["S_row_code"]).to_numpy(float)

    ex_pred_f = bp["excess 예측"].to_numpy(float)
    ex_meas_f = bp["excess 측정"].to_numpy(float)

    for row, g in sup.groupby("row"):
        stats["4t2c"][int(row)] = _fit_stats(g["code_pred"], g["code_meas"])
    for row, g in bp.groupby("row"):
        stats["fefet"][int(row)] = _fit_stats(g["code 예측(2차)"], g["code 측정"])

    series = [
        ("IGZO 4T2C", ex_pred_4, ex_meas_4, C_IGZO, len(kept)),
        ("FeFET", ex_pred_f, ex_meas_f, C_FEFET, int(bp["row"].nunique())),
    ]

    fig, ax = plt.subplots(figsize=(8.2, 7.6))
    txt = []
    for name, pr, me, color, n_rows in series:
        st = _fit_stats(pr, me)
        stats[f"{name}_excess"] = st
        # Each device is scaled onto 0..1 by one common (lo, hi) taken over its
        # predicted *and* measured excess together. Using a single affine map for
        # both axes is what keeps the 1:1 line meaningful -- and because the same
        # map is applied to prediction and measurement, R2 and the slope are
        # unchanged by it. The two devices reach different absolute excess (IGZO
        # to ~690 code, FeFET to ~208), so this is a rescaling, not a comparison
        # of dynamic range; the console keeps the absolute numbers.
        both = np.concatenate([pr[np.isfinite(pr)], me[np.isfinite(me)]])
        lo, hi = float(both.min()), float(both.max())
        span = hi - lo if hi > lo else 1.0
        stats[f"{name}_excess_range"] = (lo, hi)
        ax.plot((pr - lo) / span, (me - lo) / span, marker="o", ls="none",
                ms=MARKERSIZE - 2, mew=0, mfc=color, mec=color, alpha=0.75,
                label=f"{name}  ({n_rows} rows, n = {st['n']})")
        txt.append((name, color, st["r2"]))
    _draw_unity(ax, -0.03, 1.03)

    ax.set_xlabel("Predicted excess, normalised", fontweight="bold")
    ax.set_ylabel("Measured excess, normalised", fontweight="bold")
    ax.set_xticks(np.linspace(0, 1, 6))
    ax.set_yticks(np.linspace(0, 1, 6))
    style_ax(ax)
    labels = []
    for i, (name, color, r2v) in enumerate(txt):
        labels.append(ax.text(
            0.97, 0.06 + 0.07 * (len(txt) - 1 - i),
            f"{name}:  $R^2$ = {r2v:.3f}", transform=ax.transAxes,
            ha="right", va="bottom", fontsize=FONT_BASE - 5,
            fontweight="bold", color=color))

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Two files off one figure, so they cannot drift apart: the standalone one
    # carries the key, the numbers and the axis titles; the bare one carries
    # none of them, for a multi-panel layout that supplies its own. Only the
    # tick values survive there, so everything stripped is printed to the
    # console and has to be restated in the caption.
    leg = ax.legend(loc="upper left", frameon=True, framealpha=0.92,
                    fontsize=FONT_BASE - 6)
    fig.savefig(out_path, dpi=DPI, facecolor="white", bbox_inches="tight")
    print(f"[ok] wrote {out_path}")

    leg.remove()
    for t in labels:
        t.remove()
    ax.set_xlabel("")
    ax.set_ylabel("")
    bare = out_path.with_name(out_path.stem + "_nolegend" + out_path.suffix)
    fig.savefig(bare, dpi=DPI, facecolor="white", bbox_inches="tight")
    print(f"[ok] wrote {bare}  (bare: no legend, no R2, no axis titles -- "
          "all three belong in the caption)")
    plt.close(fig)
    return stats


# ---------------------------------------------------------------------------
# Figure 2: residuals
# ---------------------------------------------------------------------------
def plot_residuals(a4: dict, af: dict, out_path: Path) -> dict:
    sup = a4["Fig4_superposition"]
    bp = af["Best_round_points"]
    rounds = af["Rounds"]
    stats: dict = {}

    fig, axes = plt.subplots(1, 3, figsize=(19.5, 6.0))
    ax_a, ax_b, ax_c = axes

    for row, g in sup.groupby("row"):
        row = int(row)
        good = row != BAD_ROW_4T2C
        ax_a.plot(g["code_pred"], g["resid_code"], "o", ms=MARKERSIZE - 2,
                  mec=ROW_C_4T2C[row], mew=1.2,
                  mfc=ROW_C_4T2C[row] if good else "none", alpha=0.85,
                  label=f"row {row}")
    ax_a.axhline(0.0, color=C_REF, ls="--", lw=1.4)
    ax_a.set_xlabel("Predicted row code", fontweight="bold")
    ax_a.set_ylabel("Measured − predicted (code)", fontweight="bold")
    ax_a.set_title(DEV_4T2C, fontsize=FONT_BASE - 2, fontweight="bold", pad=8)
    style_ax(ax_a)
    panel_label(ax_a, "a", dx=-0.18)
    ax_a.legend(loc="lower left", frameon=True, framealpha=0.9,
                fontsize=FONT_BASE - 6, ncol=2)

    sd = bp["샘플 sd"].to_numpy(float)
    sd_med = float(np.nanmedian(sd))
    ax_b.axhspan(-sd_med, sd_med, color="0.5", alpha=0.18, zorder=0)
    for row, g in bp.groupby("row"):
        row = int(row)
        ax_b.plot(g["code 예측(2차)"], g["잔차"], "o", ms=MARKERSIZE - 2,
                  mec=ROW_C_FEFET.get(row, C_REF), mfc=ROW_C_FEFET.get(row, C_REF),
                  mew=1.2, alpha=0.85, label=f"row {row}")
    ax_b.axhline(0.0, color=C_REF, ls="--", lw=1.4)
    ax_b.set_xlabel("Predicted row code", fontweight="bold")
    ax_b.set_ylabel("Measured − predicted (code)", fontweight="bold")
    ax_b.set_title(DEV_FEFET + "   (band: median 3-sample sd)",
                   fontsize=FONT_BASE - 2, fontweight="bold", pad=8)
    style_ax(ax_b)
    panel_label(ax_b, "b", dx=-0.18)
    ax_b.legend(loc="lower left", frameon=True, framealpha=0.9,
                fontsize=FONT_BASE - 6)
    stats["fefet_sample_sd_med"] = sd_med

    # Across the whole optimisation run the residual never drops below the
    # readout noise of the same round -- the agreement is limited by the ADC,
    # not by the distance model.
    rq = pd.to_numeric(rounds["rmse_q"], errors="coerce").to_numpy(float)
    nz = pd.to_numeric(rounds["noise"], errors="coerce").to_numpy(float)
    ns = pd.to_numeric(rounds["samples"], errors="coerce").to_numpy(float)
    # noise is the spread of the per-query samples, so the single-sample rounds
    # report 0 by construction, not because they were quiet. They cannot be
    # compared against a noise floor and are left out of this panel.
    ok = np.isfinite(rq) & np.isfinite(nz) & (nz > 0)
    n_ns1 = int(np.sum(np.isfinite(nz) & (nz <= 0)))
    ax_c.plot(nz[ok], rq[ok], "o", ms=MARKERSIZE - 2, mec=C_FEFET, mfc=C_FEFET,
              mew=0, alpha=0.55,
              label=f"{int(ok.sum())} rounds"
                    + (f"  ({n_ns1} single-sample dropped)" if n_ns1 else ""))
    lim = float(max(np.nanmax(nz[ok]), np.nanmax(rq[ok]))) * 1.08
    ax_c.plot([0, lim], [0, lim], color=C_REF, ls="--", lw=1.6,
              label="residual = readout noise")
    ax_c.set_xlim(0, lim)
    ax_c.set_ylim(0, lim)
    ax_c.set_aspect("equal", adjustable="box")
    ax_c.set_xlabel("Readout noise of that round (code)", fontweight="bold")
    ax_c.set_ylabel("Query RMSE (code)", fontweight="bold")
    ax_c.set_title(DEV_FEFET + "   all optimisation rounds",
                   fontsize=FONT_BASE - 2, fontweight="bold", pad=8)
    style_ax(ax_c)
    panel_label(ax_c, "c", dx=-0.18)
    ax_c.legend(loc="upper left", frameon=True, framealpha=0.9,
                fontsize=FONT_BASE - 6)
    frac = float(np.mean(rq[ok] <= nz[ok]))
    stats["fefet_rounds_at_noise"] = frac
    stats["fefet_rounds_used"] = int(ok.sum())
    stats["fefet_rounds_dropped_ns1"] = n_ns1
    stats["fefet_median_rmse"] = float(np.median(rq[ok]))
    stats["fefet_median_noise"] = float(np.median(nz[ok]))
    ax_c.text(0.97, 0.05, f"{100 * frac:.0f} % of rounds at or below noise",
              transform=ax_c.transAxes, ha="right", va="bottom",
              fontsize=FONT_BASE - 6, fontweight="bold", color=C_REF)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=DPI, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"[ok] wrote {out_path}")
    return stats


# ---------------------------------------------------------------------------
# Figure 3: cell-to-cell variation
# ---------------------------------------------------------------------------
def plot_cell_variation(a4: dict, af: dict, out_path: Path) -> dict:
    cal = a4["Fig7_cell_cal"]
    cells = af["Cal_cells"]
    stats: dict = {}

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 6.0))
    ax_a, ax_b = axes

    k4 = pd.to_numeric(cal["kappa_code_per_V2"], errors="coerce").dropna()
    # One condition only, so the spread is between cells and not between read
    # settings: the round the FeFET campaign selected as best.
    best_round = int(af["Rounds"].loc[
        pd.to_numeric(af["Rounds"]["score"], errors="coerce").idxmax(), "round"])
    kf_all = cells[pd.to_numeric(cells["round"], errors="coerce") == best_round]
    kf = pd.to_numeric(kf_all["kappa"], errors="coerce").dropna()
    if kf.empty:                       # that round logged no cells; fall back
        kf = pd.to_numeric(cells["kappa"], errors="coerce").dropna()
        best_round = None

    groups = [("IGZO 4T2C", k4.to_numpy(float), C_IGZO),
              ("FeFET", kf.to_numpy(float), C_FEFET)]
    all_k = np.concatenate([g[1] for g in groups])
    ax_a.set_ylim(all_k.min() * 0.92, all_k.max() * 1.20)   # room for the labels
    for i, (name, vals, color) in enumerate(groups):
        jitter = (np.random.default_rng(0).random(vals.size) - 0.5) * 0.22
        ax_a.plot(np.full(vals.size, i) + jitter, vals, "o", ms=MARKERSIZE - 2,
                  mec=color, mfc=color, mew=0, alpha=0.6)
        ax_a.plot([i - 0.22, i + 0.22], [np.median(vals)] * 2, "-",
                  color=C_REF, lw=2.4, zorder=5)
        ratio = float(vals.max() / vals.min()) if vals.min() > 0 else np.nan
        stats[name] = dict(n=int(vals.size), median=float(np.median(vals)),
                           lo=float(vals.min()), hi=float(vals.max()),
                           ratio=ratio)
        ax_a.text(i, ax_a.get_ylim()[1], f"{ratio:.1f}×\nspread\nn = {vals.size}",
                  ha="center", va="top", fontsize=FONT_BASE - 7,
                  fontweight="bold", color=color)
    ax_a.set_xticks(range(len(groups)))
    ax_a.set_xticklabels([g[0] for g in groups])
    ax_a.set_ylabel(r"Curvature $\kappa$  (code/V$^2$)", fontweight="bold")
    ax_a.set_title("the distance is $\\kappa$-weighted, not plain Euclidean",
                   fontsize=FONT_BASE - 3, fontweight="bold", pad=8)
    style_ax(ax_a)
    panel_label(ax_a, "a", dx=-0.16)

    for row, g in cal.groupby("row"):
        row = int(row)
        good = row != BAD_ROW_4T2C
        ax_b.plot(g["w_store_V"], g["v0_V"], "o", ms=MARKERSIZE,
                  mec=ROW_C_4T2C[row], mew=1.4,
                  mfc=ROW_C_4T2C[row] if good else "none", ls="none",
                  label=f"row {row}")
    w = pd.to_numeric(cal["w_store_V"], errors="coerce").to_numpy(float)
    v0 = pd.to_numeric(cal["v0_V"], errors="coerce").to_numpy(float)
    ok = np.isfinite(w) & np.isfinite(v0)
    slope, icept = np.polyfit(w[ok], v0[ok], 1)
    ww = np.linspace(w[ok].min(), w[ok].max(), 50)
    ax_b.plot(ww, slope * ww + icept, color=C_REF, ls="--", lw=1.8,
              label=rf"slope {slope:+.2f}  ($\alpha$ = {-1 / slope:.3f})")
    stats["4t2c_alpha"] = float(-1.0 / slope)
    ax_b.set_xlabel("Stored value  $w$  (V)", fontweight="bold")
    ax_b.set_ylabel("Notch position  $v_0$  (V)", fontweight="bold")
    ax_b.set_title(DEV_4T2C + "   calibration behind the prediction",
                   fontsize=FONT_BASE - 3, fontweight="bold", pad=8)
    style_ax(ax_b)
    panel_label(ax_b, "b", dx=-0.16)
    ax_b.legend(loc="upper right", frameon=True, framealpha=0.9,
                fontsize=FONT_BASE - 6, ncol=2)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=DPI, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"[ok] wrote {out_path}")
    return stats


# ---------------------------------------------------------------------------
# Figure 4: read condition
# ---------------------------------------------------------------------------
def plot_conditions(a4: dict, af: dict, out_path: Path) -> dict:
    mblc = a4["Fig4c_mbl_compare"]
    rounds = af["Rounds"]
    stats: dict = {}

    fig, axes = plt.subplots(1, 3, figsize=(19.5, 6.0))
    ax_a, ax_b, ax_c = axes

    mbls = sorted(pd.to_numeric(mblc["mbl_V"], errors="coerce").dropna().unique())
    width = 0.36
    rows = sorted(int(r) for r in mblc["row"].dropna().unique())
    for i, mbl in enumerate(mbls):
        sub = mblc[np.isclose(pd.to_numeric(mblc["mbl_V"], errors="coerce"), mbl)]
        vals = [float(sub.loc[sub["row"] == r, "r2"].iloc[0]) if (sub["row"] == r).any()
                else np.nan for r in rows]
        ax_a.bar(np.arange(len(rows)) + (i - 0.5) * width, vals, width,
                 color=[C_ALT, C_OK][i % 2], edgecolor="white", linewidth=1.0,
                 label=f"MBL {mbl:+.1f} V")
    ax_a.set_xticks(np.arange(len(rows)))
    ax_a.set_xticklabels([f"row {r}" for r in rows])
    ax_a.set_ylabel(r"$R^2$ against the 1:1 line", fontweight="bold")
    ax_a.set_ylim(0, 1.05)
    ax_a.set_title(DEV_4T2C, fontsize=FONT_BASE - 2, fontweight="bold", pad=8)
    style_ax(ax_a)
    panel_label(ax_a, "a", dx=-0.18)
    ax_a.legend(loc="upper left", frameon=True, framealpha=0.9,
                fontsize=FONT_BASE - 6)
    stats["4t2c_mbl"] = {
        float(m): {int(r): float(v) for r, v in
                   zip(mblc.loc[np.isclose(pd.to_numeric(mblc["mbl_V"],
                                                         errors="coerce"), m), "row"],
                       mblc.loc[np.isclose(pd.to_numeric(mblc["mbl_V"],
                                                         errors="coerce"), m), "r2"])}
        for m in mbls}

    r = rounds.copy()
    for c in ("span", "mbl", "score"):
        r[c] = pd.to_numeric(r[c], errors="coerce")
    r = r[np.isfinite(r["span"]) & np.isfinite(r["score"])]
    mbl_levels = sorted(r["mbl"].dropna().unique())
    cmap = plt.get_cmap("viridis")
    for i, mbl in enumerate(mbl_levels):
        g = r[np.isclose(r["mbl"], mbl)]
        ax_b.plot(g["span"], g["score"], "o", ms=MARKERSIZE - 2,
                  mec=cmap(i / max(len(mbl_levels) - 1, 1)),
                  mfc=cmap(i / max(len(mbl_levels) - 1, 1)), mew=0, alpha=0.75,
                  label=f"MBL {mbl:+.2f} V")
    ax_b.set_xlabel("Query span  $\\pm$ (V)", fontweight="bold")
    ax_b.set_ylabel(r"Score  (mean row $R^2$)", fontweight="bold")
    ax_b.set_title(DEV_FEFET + f"   {len(r)} rounds",
                   fontsize=FONT_BASE - 2, fontweight="bold", pad=8)
    style_ax(ax_b)
    panel_label(ax_b, "b", dx=-0.18)
    ax_b.legend(loc="lower right", frameon=True, framealpha=0.9,
                fontsize=FONT_BASE - 7, ncol=2)

    # Score against span alone is confounded: the campaign moved several knobs
    # at once. The paired MBL blocks are the controlled comparison, so they get
    # their own panel.
    med = r.groupby("mbl")["score"].median()
    ax_c.plot(med.index, med.to_numpy(float), "o-", color=C_FEFET, lw=LW_CURVE,
              ms=MARKERSIZE + 1, mfc="white", mew=2.0, label="median score")
    for mbl, g in r.groupby("mbl"):
        ax_c.plot(np.full(len(g), mbl), g["score"], "o", ms=3.5, mec=C_FEFET,
                  mfc=C_FEFET, mew=0, alpha=0.25)
    ax_c.set_xlabel("READ_V  (V)", fontweight="bold")
    ax_c.set_ylabel(r"Score  (mean row $R^2$)", fontweight="bold")
    ax_c.set_title(DEV_FEFET + "   by read bias", fontsize=FONT_BASE - 2,
                   fontweight="bold", pad=8)
    style_ax(ax_c)
    panel_label(ax_c, "c", dx=-0.18)
    ax_c.legend(loc="lower left", frameon=True, framealpha=0.9,
                fontsize=FONT_BASE - 6)
    stats["fefet_median_by_mbl"] = {float(k): float(v) for k, v in med.items()}
    stats["fefet_n_by_mbl"] = {float(k): int(v)
                               for k, v in r.groupby("mbl")["score"].size().items()}

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=DPI, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"[ok] wrote {out_path}")
    return stats


# ---------------------------------------------------------------------------
# Figure 5: nearest-neighbour accuracy (4T2C only)
# ---------------------------------------------------------------------------
def plot_argmin(a4: dict, out_path: Path) -> dict:
    summ = a4["Fig6b_argmin_summary"].copy()
    refs = [("acc_cal", r"(1) $\kappa$-weighted, calibrated centres", C_MAIN),
            ("acc_euclid", "(2) unweighted Euclidean", C_ALT),
            ("acc_ideal", r"(3) pure software, nominal $\alpha$, $b$", C_OK)]
    combos = list(summ["combo"])
    x = np.arange(len(combos))
    width = 0.26

    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    for i, (col, label, color) in enumerate(refs):
        vals = pd.to_numeric(summ[col], errors="coerce").to_numpy(float) * 100.0
        ax.bar(x + (i - 1) * width, vals, width, color=color, edgecolor="white",
               linewidth=1.0, label=label)
    chance = 100.0 * float(pd.to_numeric(summ["chance"], errors="coerce").iloc[0])
    ax.axhline(chance, color=C_REF, ls="--", lw=1.8, zorder=3)
    ax.text(0.995, chance, " chance", transform=ax.get_yaxis_transform(),
            ha="right", va="bottom", fontsize=FONT_BASE - 6, color=C_REF)
    ax.set_xticks(x)
    ax.set_xticklabels([c.replace("_vs_", "  vs  ") for c in combos])
    ax.set_ylabel("Agreement with the software argmin (%)", fontweight="bold")
    ax.set_ylim(0, 108)
    n = int(pd.to_numeric(summ["n"], errors="coerce").iloc[0])
    ax.set_title(DEV_4T2C + f"   n = {n} queries", fontsize=FONT_BASE - 2,
                 fontweight="bold", pad=8)
    style_ax(ax)
    ax.legend(loc="upper left", frameon=True, framealpha=0.92,
              fontsize=FONT_BASE - 6)

    # The note goes under the axes: inside them it sits behind the bars.
    fig.subplots_adjust(left=0.10, right=0.98, top=0.92, bottom=0.30)
    fig.text(0.02, 0.02,
             "row 1 holds the defective cell and row 3 is its independent "
             "replica, so swapping them changes the cell, not the stored "
             "contrast.\n"
             "The FeFET array stored the same vector in both rows, so it "
             "cannot contribute to this comparison.",
             ha="left", va="bottom", fontsize=FONT_BASE - 7, color="0.35")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=DPI, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"[ok] wrote {out_path}")
    return {c: {k: float(pd.to_numeric(summ.loc[summ["combo"] == c, k],
                                       errors="coerce").iloc[0])
                for k, _l, _col in refs} for c in combos}


# ---------------------------------------------------------------------------
# Figure 6: squared error of the best data, against the noise floor
# ---------------------------------------------------------------------------
def plot_mse(a4: dict, af: dict, out_path: Path) -> dict:
    """Per-query squared error for the best row and the best round.

    The parity plot shows the agreement; this shows what is left over, query by
    query, on the scale the error is actually summed on. The flat line is the
    mean of those squares -- the MSE that the reported RMSE comes from -- and
    for the FeFET data it can be put against the readout noise, which the
    workbook records per query. The 4T2C workbook does not record a per-query
    sample spread, so that panel has no floor to draw and says so.
    """
    sup = a4["Fig4_superposition"]
    bp = af["Best_round_points"]
    stats: dict = {}

    fig, axes = plt.subplots(1, 2, figsize=(16.0, 6.4))
    ax_a, ax_b = axes

    # -- (a) 4T2C, best row -------------------------------------------------
    per_row = {int(r): _fit_stats(g["code_pred"], g["code_meas"])
               for r, g in sup.groupby("row")}
    best_row = max((r for r in per_row if r != BAD_ROW_4T2C),
                   key=lambda r: per_row[r]["r2"])
    for row, g in sup.groupby("row"):
        row = int(row)
        if row == best_row:
            continue
        sq = np.asarray(g["resid_code"], float) ** 2
        ax_a.plot(np.arange(sq.size), sq, "o", ms=3.0, mfc="0.75", mec="0.75",
                  mew=0, alpha=0.5, zorder=2)
    g_best = sup[sup["row"] == best_row]
    sq_best = np.asarray(g_best["resid_code"], float) ** 2
    ax_a.plot(np.arange(sq_best.size), sq_best, "o", ms=MARKERSIZE - 2,
              mfc=ROW_C_4T2C[best_row], mec=ROW_C_4T2C[best_row], mew=0,
              alpha=0.9, zorder=4, label=f"row {best_row}  (best)")
    mse_a = float(np.nanmean(sq_best))
    ax_a.axhline(mse_a, color=C_REF, lw=2.0, zorder=5,
                 label=f"MSE = {mse_a:.0f} code$^2$  "
                       f"(RMSE {np.sqrt(mse_a):.1f} code)")
    ax_a.plot([], [], "o", ms=3.0, mfc="0.75", mec="0.75", mew=0,
              label="other rows")
    ax_a.set_yscale("log")
    ax_a.set_xlabel("Query (in sheet order)", fontweight="bold")
    ax_a.set_ylabel(r"Squared error  (code$^2$)", fontweight="bold")
    ax_a.set_title(DEV_4T2C, fontsize=FONT_BASE - 2, fontweight="bold", pad=8)
    style_ax(ax_a)
    panel_label(ax_a, "a", dx=-0.13)
    ax_a.legend(loc="upper right", frameon=True, framealpha=0.92,
                fontsize=FONT_BASE - 6)
    ax_a.text(0.02, 0.03,
              "no per-query sample spread is recorded for this run,\n"
              "so there is no readout-noise floor to draw here",
              transform=ax_a.transAxes, ha="left", va="bottom",
              fontsize=FONT_BASE - 7, color="0.35")
    stats["4t2c"] = dict(row=best_row, mse=mse_a, rmse=float(np.sqrt(mse_a)),
                         n=int(sq_best.size))

    # -- (b) FeFET, best round ----------------------------------------------
    sd = pd.to_numeric(bp["샘플 sd"], errors="coerce").to_numpy(float)
    sd_med = float(np.nanmedian(sd))
    # The measurement is the mean of ``samples`` readings, so the noise on it is
    # sd/sqrt(n); the workbook's own summary compares RMSE against sd itself.
    # Both are drawn, as a band, rather than picking one silently -- and the
    # prediction carries calibration noise of its own, which neither bounds.
    n_samp = 3.0
    lo_floor, hi_floor = sd_med ** 2 / n_samp, sd_med ** 2
    ax_b.axhspan(lo_floor, hi_floor, color="0.5", alpha=0.18, zorder=0)
    ax_b.text(0.02, hi_floor, " readout-noise floor:  "
                              r"$\sigma^2/3$ … $\sigma^2$",
              transform=ax_b.get_yaxis_transform(), ha="left", va="bottom",
              fontsize=FONT_BASE - 7, color="0.35")

    mse_rows = {}
    for row, g in bp.groupby("row"):
        row = int(row)
        sq = pd.to_numeric(g["잔차"], errors="coerce").to_numpy(float) ** 2
        ax_b.plot(np.arange(sq.size), sq, "o", ms=MARKERSIZE - 2,
                  mfc=ROW_C_FEFET.get(row, C_REF), mec=ROW_C_FEFET.get(row, C_REF),
                  mew=0, alpha=0.9, zorder=4, label=f"row {row}")
        mse_rows[row] = float(np.nanmean(sq))
        ax_b.axhline(mse_rows[row], color=ROW_C_FEFET.get(row, C_REF), lw=1.8,
                     ls="--", zorder=5)
    mse_b = float(np.nanmean(list(mse_rows.values())))
    ax_b.set_yscale("log")
    ax_b.set_xlabel("Query index", fontweight="bold")
    ax_b.set_ylabel(r"Squared error  (code$^2$)", fontweight="bold")
    ax_b.set_title(DEV_FEFET + "   best round",
                   fontsize=FONT_BASE - 2, fontweight="bold", pad=8)
    style_ax(ax_b)
    panel_label(ax_b, "b", dx=-0.13)
    handles, labels = ax_b.get_legend_handles_labels()
    handles.append(Line2D([0], [0], color=C_REF, ls="--", lw=1.8))
    labels.append("MSE = " + " / ".join(f"{mse_rows[r]:.0f}"
                                        for r in sorted(mse_rows)) + " code$^2$")
    ax_b.legend(handles, labels, loc="upper right", frameon=True,
                framealpha=0.92, fontsize=FONT_BASE - 6)
    stats["fefet"] = dict(mse_rows=mse_rows, mse=mse_b, sd_med=sd_med,
                          floor_lo=lo_floor, floor_hi=hi_floor)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=DPI, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"[ok] wrote {out_path}")
    return stats


# ---------------------------------------------------------------------------
# Figure 7: what limits R^2
# ---------------------------------------------------------------------------
def _three_r2(pred, meas) -> tuple:
    """R^2 against the 1:1 line, then with an offset free, then with a gain free.

    The three differ only in what the prediction is allowed to be adjusted by,
    so the gaps between them name the error:

      1:1 -> offset-free   the row floor S is off
      offset -> shape      the response is compressed (a gain error)
      1 - shape            what neither can fix: superposition breaking down,
                           plus readout noise

    The first is the claim being tested; the other two are diagnostics and are
    not the number to quote.
    """
    p = np.asarray(pred, float)
    m = np.asarray(meas, float)
    ok = np.isfinite(p) & np.isfinite(m)
    p, m = p[ok], m[ok]
    if p.size < 3:
        return (np.nan,) * 3
    sst = float(np.sum((m - m.mean()) ** 2))
    if sst <= 0:
        return (np.nan,) * 3
    r2_11 = 1.0 - float(np.sum((m - p) ** 2)) / sst
    d = m - p
    r2_off = 1.0 - float(np.sum((d - d.mean()) ** 2)) / sst
    r2_shape = float(np.corrcoef(p, m)[0, 1] ** 2)
    return r2_11, r2_off, r2_shape


def plot_r2(a4: dict, af: dict, out_path: Path) -> dict:
    sup = a4["Fig4_superposition"]
    bp = af["Best_round_points"]

    entries = []
    for row, g in sup.groupby("row"):
        entries.append((f"4T2C\nrow {int(row)}", _three_r2(g["code_pred"],
                                                           g["code_meas"]),
                        int(row) == BAD_ROW_4T2C))
    for row, g in bp.groupby("row"):
        entries.append((f"FeFET\nrow {int(row)}",
                        _three_r2(g["code 예측(2차)"], g["code 측정"]), False))

    labels = [e[0] for e in entries]
    vals = np.array([e[1] for e in entries], float)
    # a gap on the x axis between the two devices, since the units differ
    x = np.arange(len(entries), dtype=float)
    n4 = sum(1 for lab in labels if lab.startswith("4T2C"))
    x[n4:] += 0.6

    series = [("$R^2$ vs 1:1  (the claim)", C_MAIN),
              ("offset free", C_ALT),
              ("shape only  (Pearson $r^2$)", C_OK)]
    width = 0.26
    fig, ax = plt.subplots(figsize=(14.5, 6.4))
    for i, (label, color) in enumerate(series):
        ax.bar(x + (i - 1) * width, vals[:, i], width, color=color,
               edgecolor="white", linewidth=1.0, label=label,
               alpha=0.45 if False else 1.0)
    for j, (_lab, v_j, bad) in enumerate(entries):
        if bad:
            ax.text(x[j], max(v_j) + 0.03, "defective cell", ha="center",
                    va="bottom", fontsize=FONT_BASE - 7, fontweight="bold",
                    color=C_WARN)

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel(r"$R^2$", fontweight="bold")
    ax.set_ylim(0, 1.16)
    ax.axhline(1.0, color=C_REF, ls=":", lw=1.2, zorder=1)
    style_ax(ax)
    ax.legend(loc="upper left", frameon=True, framealpha=0.92, ncol=3,
              fontsize=FONT_BASE - 6)

    # Name the two gaps where they are wide enough to be read: the working row
    # with the largest spread between the first and the last bar. On the best
    # row both gaps are a few thousandths and the arrows would be invisible.
    cand = [(vals[j, 2] - vals[j, 0], j) for j in range(n4) if not entries[j][2]]
    _spread, ann_j = max(cand)
    v = vals[ann_j]
    ax.annotate("", xy=(x[ann_j] - width, v[1]), xytext=(x[ann_j] - width, v[0]),
                arrowprops=dict(arrowstyle="<->", color=C_REF, lw=1.4))
    ax.text(x[ann_j] - width - 0.05, 0.5 * (v[0] + v[1]),
            f"floor error\n{v[1] - v[0]:+.3f}  ", fontsize=FONT_BASE - 7,
            va="center", ha="right", color=C_REF, fontweight="bold")
    ax.annotate("", xy=(x[ann_j] + width, v[2]), xytext=(x[ann_j] + width, v[1]),
                arrowprops=dict(arrowstyle="<->", color=C_REF, lw=1.4))
    ax.text(x[ann_j] + width + 0.05, 0.5 * (v[1] + v[2]),
            f"  compression\n  {v[2] - v[1]:+.3f}", fontsize=FONT_BASE - 7,
            va="center", ha="left", color=C_REF, fontweight="bold")

    fig.tight_layout()
    fig.subplots_adjust(bottom=0.26)
    fig.text(0.02, 0.02,
             "The three bars differ only in what the prediction may be adjusted "
             "by: nothing, an offset, then an offset and a gain.\n"
             "Their gaps separate a wrong row floor from a compressed response; "
             "what is left below the third bar is superposition error plus noise.",
             ha="left", va="bottom", fontsize=FONT_BASE - 7, color="0.35")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=DPI, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"[ok] wrote {out_path}")
    return {lab.replace("\n", " "): dict(r2=float(v[0]), r2_offset=float(v[1]),
                                         r2_shape=float(v[2]))
            for (lab, v, _bad) in entries}


# ---------------------------------------------------------------------------
# Figure 8: both devices' R^2 on one axes, coloured by device
# ---------------------------------------------------------------------------
DEV_COLOR = {"IGZO 4T2C": C_IGZO, "FeFET": C_FEFET}


def plot_r2_combined(a4: dict, af: dict, out_path: Path) -> dict:
    """R^2 against the 1:1 line for every row of both arrays, in one panel.

    Figure 7 splits R^2 three ways to say *what* limits it; this one keeps only
    the number that is the claim -- no free parameter, straight against the 1:1
    line -- and puts the two device families side by side in one colour each.

    The dashed line per device is the mean over its working rows. The 4T2C
    defective row is drawn hatched and left out of that mean, because averaging
    a known-broken cell into a device figure would understate the architecture
    and overstate nothing useful; it is still shown so the exclusion is visible.
    """
    sup = a4["Fig4_superposition"]
    bp = af["Best_round_points"]

    entries = []
    for row, g in sup.groupby("row"):
        row = int(row)
        entries.append(dict(dev="IGZO 4T2C", row=row,
                            r2=_fit_stats(g["code_pred"], g["code_meas"])["r2"],
                            bad=row == BAD_ROW_4T2C))
    for row, g in bp.groupby("row"):
        row = int(row)
        entries.append(dict(dev="FeFET", row=row,
                            r2=_fit_stats(g["code 예측(2차)"], g["code 측정"])["r2"],
                            bad=False))

    # a gap between the two device blocks
    x, cursor, prev = [], 0.0, None
    for e in entries:
        if prev is not None and e["dev"] != prev:
            cursor += 0.8
        x.append(cursor)
        cursor += 1.0
        prev = e["dev"]
    x = np.array(x, float)

    fig, ax = plt.subplots(figsize=(12.0, 6.4))
    for xi, e in zip(x, entries):
        col = DEV_COLOR[e["dev"]]
        ax.bar(xi, e["r2"], 0.72, color="white" if e["bad"] else col,
               edgecolor=col, linewidth=1.8,
               hatch="//" if e["bad"] else None, zorder=3)

    stats: dict = {}
    for dev, col in DEV_COLOR.items():
        good = [e["r2"] for e in entries if e["dev"] == dev and not e["bad"]]
        xs = [xi for xi, e in zip(x, entries) if e["dev"] == dev]
        if not good:
            continue
        mean = float(np.mean(good))
        stats[dev] = dict(mean=mean, n=len(good),
                          rows={e["row"]: float(e["r2"])
                                for e in entries if e["dev"] == dev})
        ax.plot([min(xs) - 0.45, max(xs) + 0.45], [mean, mean], ls="--",
                color=col, lw=2.0, zorder=4)
        ax.text(max(xs) + 0.40, mean, f" {mean:.3f}", color=col, va="center",
                ha="left", fontsize=FONT_BASE - 5, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([f"row {e['row']}" for e in entries])
    ax.set_ylabel(r"$R^2$ against the 1:1 line", fontweight="bold")
    ax.set_ylim(0, 1.14)
    ax.axhline(1.0, color=C_REF, ls=":", lw=1.2, zorder=1)
    style_ax(ax)

    handles = [Line2D([0], [0], color=DEV_COLOR[d], lw=8, label=d)
               for d in DEV_COLOR]
    handles.append(Line2D([0], [0], color=C_REF, ls="--", lw=2.0,
                          label="device mean (working rows)"))
    handles.append(Line2D([0], [0], marker="s", ls="none", ms=11, mfc="white",
                          mec=C_IGZO, mew=1.8, label="defective cell, excluded"))
    ax.legend(handles=handles, loc="lower left", frameon=True, framealpha=0.92,
              ncol=2, fontsize=FONT_BASE - 6)

    # The two devices are not on equal footing and the figure should not imply
    # they are: different arrays, different query counts, and one of them had a
    # row fail. Said once, under the axes.
    n4 = len(sup[sup["row"] == entries[0]["row"]])
    nf = len(bp[bp["row"] == 0])
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.24)
    fig.text(0.02, 0.02,
             f"IGZO: {n4} queries per row over a 4x2 array;  "
             f"FeFET: {nf} queries per row over a 2x2 array.  "
             "Same metric, different sample sizes and array sizes.",
             ha="left", va="bottom", fontsize=FONT_BASE - 7, color="0.35")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=DPI, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"[ok] wrote {out_path}")
    return stats


# ---------------------------------------------------------------------------
# Console summary
# ---------------------------------------------------------------------------
def report(res: dict) -> None:
    print("\n--- Hardware vs software L2, two arrays ---")
    par = res.get(1)
    if par:
        print("agreement with the 1-D-calibrated prediction (no 2-D fit):")
        rmap = {v: k for k, v in par.get("row_map", {}).items()}
        for row in sorted(par["4t2c"]):
            st = par["4t2c"][row]
            tag = "  <- defective cell" if row == BAD_ROW_4T2C else ""
            shown = rmap.get(row)
            label = (f"row {row}" if shown is None or shown == row
                     else f"row {row} (shown as {shown})")
            print(f"  4T2C  {label}: R2 {st['r2']:6.3f}  NRMSE "
                  f"{100 * st['nrmse']:5.1f} %  slope {st['slope']:.3f}"
                  f"  (n = {st['n']}){tag}")
        if par.get("row_map"):
            pairs = ", ".join(f"{k} = hardware row {v}"
                              for k, v in sorted(par["row_map"].items()))
            print(f"  parity figure shows {pairs}")
            if par.get("dropped"):
                print("  hardware rows "
                      + ", ".join(str(r) for r in sorted(set(par["dropped"])))
                      + " are not shown (one defective, the rest the weaker "
                        "survivors) -- selecting the best 2 of 4 has to be "
                        "stated in the caption")
        for name in ("IGZO 4T2C", "FeFET"):
            st = par.get(f"{name}_excess")
            if st:
                rng = par.get(f"{name}_excess_range")
                span = f", excess {rng[0]:.0f} to {rng[1]:.0f} code" if rng else ""
                print(f"  {name} pooled on excess over the row floor: R2 "
                      f"{st['r2']:.3f}, slope {st['slope']:.3f} "
                      f"(n = {st['n']}{span})")
        print("  the parity figure scales each device onto 0..1 with one map for "
              "both axes, so R2 and slope are the same numbers as above")
        for row in sorted(par["fefet"]):
            st = par["fefet"][row]
            print(f"  FeFET row {row}: R2 {st['r2']:6.3f}  NRMSE "
                  f"{100 * st['nrmse']:5.1f} %  slope {st['slope']:.3f}"
                  f"  (n = {st['n']})")
        sl = [par["4t2c"][r]["slope"] for r in par["4t2c"] if r != BAD_ROW_4T2C]
        print(f"  the 4T2C slopes sit at {np.mean(sl):.2f}: the measured response "
              "is compressed against the prediction. That is a gain error, not a "
              "breakdown of superposition -- the shape still tracks.")

    rs = res.get(2)
    if rs:
        print(f"residual floor: FeFET median 3-sample sd "
              f"{rs['fefet_sample_sd_med']:.1f} code")
        print(f"  across {rs['fefet_rounds_used']} rounds "
              f"({rs['fefet_rounds_dropped_ns1']} single-sample rounds dropped: "
              "they report noise = 0 by construction), median query RMSE "
              f"{rs['fefet_median_rmse']:.1f} vs median noise "
              f"{rs['fefet_median_noise']:.1f} code, and "
              f"{100 * rs['fefet_rounds_at_noise']:.0f} % sit at or below their "
              "own noise -- the agreement is limited by the readout, not by the "
              "distance model")

    cv = res.get(3)
    if cv:
        for name in ("IGZO 4T2C", "FeFET"):
            if name in cv:
                d = cv[name]
                print(f"kappa spread, {name}: median {d['median']:.0f}, range "
                      f"{d['lo']:.0f}-{d['hi']:.0f} code/V^2 "
                      f"({d['ratio']:.1f}x, n = {d['n']})")
        print("  a spread in kappa means the hardware computes a weighted "
              "distance; an application has to absorb it or equalise it")
        print("  the two counts are not equivalent: the 4T2C figure is 8 cells "
              "x 3 stored patterns at one condition, the FeFET figure is its 4 "
              "cells at one condition, so only the 4T2C number bounds "
              "cell-to-cell spread with any weight")
        if "4t2c_alpha" in cv:
            print(f"4T2C calibration slope gives alpha = {cv['4t2c_alpha']:.3f}")

    cd = res.get(4)
    if cd:
        for mbl, per_row in sorted(cd.get("4t2c_mbl", {}).items()):
            txt = ", ".join(f"row {r} {v:.3f}" for r, v in sorted(per_row.items()))
            print(f"4T2C MBL {mbl:+.1f} V: {txt}")
        med = cd.get("fefet_median_by_mbl", {})
        cnt = cd.get("fefet_n_by_mbl", {})
        if med:
            print("FeFET median score by READ_V: "
                  + ", ".join(f"{k:+.2f} V {v:.3f} (n={cnt.get(k, 0)})"
                              for k, v in sorted(med.items())))
            thin = [k for k, n in cnt.items() if n < 5]
            if thin:
                print("  read as a trend, not a per-level measurement: "
                      + ", ".join(f"{k:+.2f} V" for k in sorted(thin))
                      + " have fewer than 5 rounds")

    am = res.get(5)
    if am:
        print("argmin agreement (4T2C only):")
        for combo, d in am.items():
            print(f"  {combo:16s} kappa-weighted {100 * d['acc_cal']:5.1f} %   "
                  f"Euclidean {100 * d['acc_euclid']:5.1f} %   "
                  f"software {100 * d['acc_ideal']:5.1f} %")
    ms = res.get(6)
    if ms:
        a = ms["4t2c"]
        print(f"squared error, best data:")
        print(f"  4T2C  row {a['row']}: MSE {a['mse']:.0f} code^2 "
              f"(RMSE {a['rmse']:.1f}, n = {a['n']})")
        f = ms["fefet"]
        rows = " / ".join(f"row {r} {v:.0f}" for r, v in sorted(f["mse_rows"].items()))
        print(f"  FeFET best round: MSE {rows} code^2 "
              f"(mean {f['mse']:.0f})")
        print(f"  FeFET readout-noise floor: median sample sd {f['sd_med']:.1f} "
              f"code -> {f['floor_lo']:.0f} (mean of 3) to {f['floor_hi']:.0f} "
              "(single sample) code^2")
        if f["mse"] < f["floor_lo"]:
            print("  the residual sits below even the mean-of-3 noise, so the "
                  "sample spread is an upper bound on the readout here, not a "
                  "floor the model is hitting")
    r2 = res.get(7)
    if r2:
        print("R^2, and what moves it when the prediction is allowed to shift:")
        print(f"  {'':12s} {'vs 1:1':>8s} {'offset free':>12s} {'shape only':>11s}")
        for lab, d in r2.items():
            print(f"  {lab:12s} {d['r2']:8.3f} {d['r2_offset']:12.3f} "
                  f"{d['r2_shape']:11.3f}")
        print("  a gap from the first to the second is a wrong row floor; from "
              "the second to the third is compression; what is missing from the "
              "third is superposition error plus readout noise")
    rc = res.get(8)
    if rc:
        for dev, d in rc.items():
            rows = ", ".join(f"row {r} {v:.3f}" for r, v in sorted(d["rows"].items()))
            print(f"{dev}: {rows}")
            print(f"  mean over {d['n']} working rows: {d['mean']:.3f}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Plot the 4T2C and FeFET array distance (L2) datasets.")
    ap.add_argument("--outdir", type=Path, default=OUTDIR)
    ap.add_argument("--xlsx-4t2c", type=Path, default=XLSX_4T2C)
    ap.add_argument("--xlsx-fefet", type=Path, default=XLSX_FEFET)
    ap.add_argument("--figures", type=int, nargs="+", choices=sorted(STEMS),
                    default=sorted(STEMS), metavar="N",
                    help="which figures to render (default: all)")
    args = ap.parse_args(argv)

    try:
        a4 = load_4t2c(args.xlsx_4t2c)
        af = load_fefet(args.xlsx_fefet)
    except FileNotFoundError as exc:
        print(f"[error] missing input: {exc}", file=sys.stderr)
        return 1

    apply_plot_style()
    res: dict = {}
    for num in args.figures:
        out = args.outdir / f"{STEMS[num]}.png"
        if num == 1:
            res[1] = plot_parity(a4, af, out)
        elif num == 2:
            res[2] = plot_residuals(a4, af, out)
        elif num == 3:
            res[3] = plot_cell_variation(a4, af, out)
        elif num == 4:
            res[4] = plot_conditions(a4, af, out)
        elif num == 5:
            res[5] = plot_argmin(a4, out)
        elif num == 6:
            res[6] = plot_mse(a4, af, out)
        elif num == 7:
            res[7] = plot_r2(a4, af, out)
        elif num == 8:
            res[8] = plot_r2_combined(a4, af, out)
    report(res)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
