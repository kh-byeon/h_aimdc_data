#!/usr/bin/env python3
"""
Figures for the 4T2C notch-shift campaign of 2026-09-04/05 (chip6, row 0 / pair 0).

    python plot_4t2c_notch_campaign.py
    python plot_4t2c_notch_campaign.py --figures 1 3 --outdir DIR

Input: ``4t2c_notch_dataset_chip6_R0C0_0904-0905.xlsx`` (sheets README, SESSIONS,
NOTCH, CONDITIONS, FITS, CMSCAN_FIT, CMSCAN_PTS, NOISE, VALIDATION, CURVES),
documented in ``4t2c_notch_methods_results.md``.

This is a separate script from ``plot_4t2c_notch_response.py``, which plots the
2026-09-03 single-cell dataset. The two are not merged: the pin assignment
differs (methods doc section 1), and the earlier power-law framing was retired
after the on-line log-log exponent estimator was found to be biased by +0.3-0.4
(section 8). Conditions here are ranked by curvature CV, and the notch-shift
model is

    v0(w) = -w/alpha + b + c3 * w^3

with alpha the SL-to-storage-node divider ratio, b the branch-mismatch offset
(drifts session to session, tracks Vt) and c3 the cubic write compression.

Figure 1 ``4t2c_campaign_model.png``            -- sections 9.2, 9.3
  (a) raw notch curves, FINE3 alt, one per stored weight
  (b) v0 vs w over +-1.5 V with the linear and the cubic fit
  (c) fit residuals vs w: linear leaves 119-127 mV, the cubic 20-23 mV
  (d) the dense +-0.6 V scan, residual against the same cubic
  (e) the nine independent determinations of alpha

Figure 2 ``4t2c_campaign_operating_point.png``  -- sections 9.1, 9.4
  (a) common-mode scans with the piecewise-fitted Vt of each
  (b) Vt and the ideal common mode s* against wall-clock time
  (c) the notch offset b against the independently measured Vt

Figure 3 ``4t2c_campaign_conditions.png``       -- section 8
  (a) curvature CV vs common mode, by MBL, three replicates
  (b) curvature CV by MBL at each session's best common mode
  (c) the cost of the window: CV against auto_ratio
  (d) ADC headroom, which is what rules out MBL = -2.0 V

Figure 4 ``4t2c_campaign_noise_order.png``      -- sections 9.5, 9.6
  (a) per-point ADC scatter by session, and the power cycle
  (b) what that noise did to the notch uncertainty and the curvature CV
  (c) alt vs seq: the write-order effect on alpha, reproducible to 2 %
  (d) re-extraction against the instrument's on-line fit

Figure 5 ``4t2c_campaign_notches.png``         -- the main-text figure
  four notch curves from FINE3 alt on the measured sweep axis, joined across the
  full sweep, with the code scaled per block onto 0..1 between its notch floor
  and its highest measured point. Bare by design:
  no legend and no in-plot text, so the numbers belong in the caption -- the
  console table prints them. Change the blocks with --weights, --session and
  --order.

Figure 6 ``4t2c_campaign_notches_dense.png``
  panel 1(a) on its own at full size: every block of one dense pass (25 stored
  values), code scaled per block onto 0..1 between its notch floor and its
  highest measured point, shaded by w, annotated with the ensemble exponent p of
  code = C + A|v - v0|^p from the C-free symmetrised estimator of methods doc
  section 8 -- which the scaling does not affect. Follows --session and --order.

Figure 7 ``4t2c_campaign_mapping.png``
  panel 1(b) on its own at full size: v0 against the stored value over +-1.5 V
  at the best read condition, linear model only. Follows --opt-session.

The two notch figures are additionally written as ``<name>_fixed.png``, cropped
to v in +-1.5 V with the normalised code ending at 1; the default render keeps
whatever the data spans.

Every figure is also written a second time as ``<name>_bare.png``, with all
text stripped -- no titles, axis labels, legends, annotations, panel letters or
word-valued tick labels, only the numeric ticks that carry the scale -- for use
in a layout that supplies its own labelling. The two copies come off one figure
object, so they cannot disagree.

A block is identified by (source_file, w_store_V, w_pass, visit_k); source_file
also encodes the optscan condition and the finescan sweep order, neither of which
is carried as a column in CURVES.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt             # noqa: E402
import numpy as np                          # noqa: E402
import pandas as pd                         # noqa: E402
from matplotlib.colors import TwoSlopeNorm, LinearSegmentedColormap  # noqa: E402

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
OUTDIR = ROOT / "figures"
XLSX_GLOB = "4t2c_notch_dataset*.xlsx"

STEMS = {
    1: "4t2c_campaign_model",
    2: "4t2c_campaign_operating_point",
    3: "4t2c_campaign_conditions",
    4: "4t2c_campaign_noise_order",
    5: "4t2c_campaign_notches",
    6: "4t2c_campaign_notches_dense",
    7: "4t2c_campaign_mapping",
}

# Full-range session for the standalone mapping figure; --opt-session overrides.
MAIN_OPT = "OPT1"

# Half-width of the quadratic notch fit, matching NOTCH_FIT_SPAN in the
# measurement code (methods doc 7).
NOTCH_FIT_SPAN = 0.70

# Every figure is written twice: once as it reads on its own, and once with all
# text removed (notch_common.strip_text), for dropping into a layout that
# supplies its own labels.

# The two notch figures are each written twice. The default render lets the
# data set the axes, so nothing measured is hidden. The "_fixed" render crops to
# a common window -- v in NOTCH_V_XLIM, normalised code ending exactly at 1 --
# which is easier to place next to another panel but clips the outer arms of the
# widest blocks. Both are kept; the cropped one reports what it hides.
NOTCH_V_XLIM = (-1.5, 1.5)
FIXED_SUFFIX = "_fixed"

# Main-text figure: four stored values spanning the dense scan, evenly spaced.
MAIN_SESSION, MAIN_ORDER = "FINE3", "alt"
MAIN_W = (-0.6, -0.2, 0.2, 0.6)

# Notation, palette and style come from notch_common so that every notch
# figure in this folder -- 4T2C and FeFET -- reads as one set.
from notch_common import (            # noqa: E402
    DPI, FONT_BASE, FONT_PANEL, LW_CURVE, GRID_ALPHA, MARKERSIZE,
    CMAP_W, C_REF, C_MAIN, C_ALT, C_OK, C_WARN, C_PURPLE,
    LBL_V, LBL_W, LBL_V0, LBL_CODE, LBL_CODE_NORM, LBL_ALPHA,
    MODEL_LINEAR, MODEL_CUBIC, MODEL_POWER,
    apply_plot_style, style_ax, panel_label, exponent_cfree,
    strip_text, BARE_SUFFIX,
)

# ---------------------------------------------------------------------------
# Orange palette (local override)
# ---------------------------------------------------------------------------
# Every colour in this figure set is a shade of orange: the colour key is a
# single-hue orange ramp and the categorical series are picked off the same
# ramp, spaced far enough apart in lightness that they stay separable in
# greyscale.  The names imported from notch_common are rebound here only, so
# the other notch scripts keep the shared Okabe-Ito palette.
ORANGE_RAMP = ["#FFF5EB", "#FEE6CE", "#FDD0A2", "#FDAE6B", "#FD8D3C",
               "#F16913", "#D94801", "#A63603", "#7F2704"]
CMAP_ORANGE = LinearSegmentedColormap.from_list("notch_orange", ORANGE_RAMP)
try:                                  # so plt.get_cmap("notch_orange") works too
    matplotlib.colormaps.register(CMAP_ORANGE, name="notch_orange", force=True)
except (AttributeError, ValueError):  # older matplotlib, or already registered
    pass

# Pale ends of a single-hue ramp vanish on a white page, so the colour key runs
# over the usable middle-to-dark stretch instead of the full 0-1 range.
CMAP_W = LinearSegmentedColormap.from_list(
    "notch_orange_w", CMAP_ORANGE(np.linspace(0.34, 1.0, 256)))

C_REF = "#4A2C12"       # very dark brown -- ideal / reference lines
C_MAIN = "#D94801"      # strong orange   -- primary series
C_ALT = "#F79A4A"       # light orange    -- second series
C_OK = "#FDC58A"        # pale orange     -- the good case
C_WARN = "#7F2704"      # burnt orange    -- the failure case
C_PURPLE = "#A63603"    # deep orange     -- fourth series

SESSION_C = {"OPT1": "#7F2704", "OPT2": "#A63603", "OPT3": "#D94801",
             "FINE1": "#F16913", "FINE2": "#FD9E4F", "FINE3": "#FDC58A"}
MBL_C = {-1.0: "#FD9E4F", -1.5: "#D94801", -2.0: "#7F2704"}
ORDER_C = {"alt": "#A63603", "seq": "#F79A4A"}


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def find_one(data_dir: Path, pattern: str) -> Optional[Path]:
    hits = sorted(data_dir.glob(pattern))
    if len(hits) > 1:
        print(f"[warn] {len(hits)} files match {pattern!r}; using {hits[-1].name}")
    return hits[-1] if hits else None


def load_dataset(data_dir: Path) -> dict:
    xlsx = find_one(data_dir, XLSX_GLOB)
    if xlsx is None:
        raise FileNotFoundError(f"no file matching {XLSX_GLOB} in {data_dir}")
    book = pd.read_excel(xlsx, sheet_name=None)
    tables = {k: v for k, v in book.items() if k != "README"}
    # visit_k is NaN for the optscan rows; -1 keeps it usable as a group key.
    for key in ("NOTCH", "CURVES"):
        if key in tables:
            tables[key]["visit_k"] = tables[key]["visit_k"].fillna(-1)
    if "SESSIONS" in tables:
        tables["SESSIONS"]["start"] = pd.to_datetime(tables["SESSIONS"]["start"])
    print(f"[in ] {xlsx.name}: {', '.join(sorted(tables))}")
    return tables


def save_figure(fig: plt.Figure, out_path: Path) -> Path:
    """Write the figure, then a text-free copy beside it, and close it."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=DPI, facecolor="white", bbox_inches="tight")
    print(f"[ok] wrote {out_path}")

    strip_text(fig)
    bare = out_path.with_name(out_path.stem + BARE_SUFFIX + out_path.suffix)
    fig.savefig(bare, dpi=DPI, facecolor="white", bbox_inches="tight")
    print(f"[ok] wrote {bare}")
    plt.close(fig)
    return bare


def w_norm(w: np.ndarray) -> TwoSlopeNorm:
    lim = float(np.nanmax(np.abs(w)))
    return TwoSlopeNorm(vmin=-lim, vcenter=0.0, vmax=lim)


def clipped_low(ax: plt.Axes, y, tag: str) -> None:
    """Count normalised points sitting below the axis floor, and say so."""
    y = np.asarray(y, dtype=float)
    y = y[np.isfinite(y)]
    lo = ax.get_ylim()[0]
    n_out = int(np.sum(y < lo))
    if n_out:
        print(f"[note] {tag}: y starts at {lo:.2f}, {n_out} of {y.size} "
              "normalised points sit below it (readout noise at the notch "
              "floor) and are clipped")


def apply_v_xlim(ax: plt.Axes, v, tag: str) -> None:
    """Fix the sweep axis to NOTCH_V_XLIM and say what that hides.

    Clipping an axis is a claim about what is worth showing, so the count of
    measured points left outside is printed rather than quietly dropped.
    """
    if NOTCH_V_XLIM is None:
        return
    lo, hi = NOTCH_V_XLIM
    v = np.asarray(v, dtype=float)
    v = v[np.isfinite(v)]
    n_out = int(np.sum((v < lo) | (v > hi)))
    ax.set_xlim(lo, hi)
    if n_out:
        print(f"[note] {tag}: x limited to {lo:+.1f}..{hi:+.1f} V, "
              f"{n_out} of {v.size} measured points fall outside and are "
              "clipped")


# Tick spacing on the stored-value colour key, in volts.
W_TICK_STEP = 0.2


def add_w_colorbar(fig: plt.Figure, ax: plt.Axes, norm: TwoSlopeNorm) -> None:
    """Colour key for the stored value, on a round tick grid to its own ends.

    The default locator stops short of the extremes -- a +-0.6 V ramp gets ticks
    only to +-0.4 -- which leaves the reader guessing how far the colours go.
    Ticks are placed on a W_TICK_STEP grid instead, extended to cover vmin and
    vmax, so the ends are always labelled and the spacing stays readable.
    """
    n = int(np.floor(max(abs(norm.vmin), abs(norm.vmax)) / W_TICK_STEP + 1e-9))
    # Rounded, or 3 * 0.2 lands on 0.6000000000000001 and a tick meant for the
    # very end of the ramp falls outside it and is silently dropped.
    ticks = np.round(np.arange(-n, n + 1) * W_TICK_STEP, 10)
    ticks = ticks[(ticks >= norm.vmin - 1e-9) & (ticks <= norm.vmax + 1e-9)]
    if ticks.size < 2:               # a range narrower than one step
        ticks = np.linspace(norm.vmin, norm.vmax, 5)

    sm = plt.cm.ScalarMappable(norm=norm, cmap=plt.get_cmap(CMAP_W))
    cbar = fig.colorbar(sm, ax=ax, pad=0.02, ticks=ticks)
    cbar.set_label(LBL_W, fontweight="bold", fontsize=22)
    cbar.ax.tick_params(labelsize=14, width=1.4, length=5)
    for lab in cbar.ax.get_yticklabels():
        lab.set_fontweight("bold")
    cbar.outline.set_linewidth(1.2)


# ---------------------------------------------------------------------------
# Selection and model helpers
# ---------------------------------------------------------------------------
def best_condition(tables: dict, session: str) -> Optional[pd.Series]:
    """The optscan condition with the lowest curvature CV (methods doc 8)."""
    cond = tables.get("CONDITIONS")
    if cond is None:
        return None
    sub = cond[cond["session"] == session]
    return None if sub.empty else sub.loc[sub["curv_cv_pct"].idxmin()]


def blocks_of(tables: dict, source_file: str) -> pd.DataFrame:
    n = tables["NOTCH"]
    return n[n["source_file"] == source_file].sort_values("w_store_V")


def curves_of(tables: dict, source_file: str) -> pd.DataFrame:
    c = tables["CURVES"]
    return c[c["source_file"] == source_file]


def fine_source(tables: dict, session: str, order: str) -> Optional[str]:
    n = tables["NOTCH"]
    sub = n[(n["session"] == session) & (n["sweep_order"] == order)]
    return None if sub.empty else str(sub["source_file"].iloc[0])


def alpha_ensemble(fits: pd.DataFrame) -> tuple:
    """The nine small-signal determinations of alpha (methods doc 9.3).

    Small-w slope for the three full-range optscan campaigns, plain linear slope
    for the six +-0.6 V finescan passes: over that range the two are the same
    quantity, which is why the doc pools them into one ensemble.
    """
    opt = fits[fits["dataset"] == "optscan best cond"]
    fine = fits[fits["dataset"].str.startswith("finescan")]
    rows = [(f"{r.session} small-$w$", float(r.alpha_lin_smallw), r.session)
            for r in opt.itertuples()]
    rows += [(f"{r.session} {r.dataset.split()[-1]}", float(r.alpha_lin), r.session)
             for r in fine.itertuples()]
    vals = np.array([v for _, v, _ in rows], dtype=float)
    return rows, float(vals.mean()), float(vals.std(ddof=1))


def cm_pairs(tables: dict) -> pd.DataFrame:
    """Pair each measurement session with its own common-mode scan.

    CM3/CM4/CM5 are step 1 *inside* OPT1/OPT2/OPT3 and start about 4 s before the
    session they belong to, so "the last CM scan before this session" picks the
    previous one. Nearest in time, with each measurement session keeping only its
    closest scan, reproduces the four pairs of methods doc 9.4 and drops the two
    standalone repeats CM1/CM2.
    """
    cm, ss, fits = tables["CMSCAN_FIT"], tables["SESSIONS"], tables["FITS"]
    t = dict(zip(ss["session"], ss["start"]))
    meas = [s for s in ss["session"] if not str(s).startswith("CM")]
    best: dict = {}
    for c in cm["session"]:
        m = min(meas, key=lambda s: abs((t[s] - t[c]).total_seconds()))
        gap = abs((t[m] - t[c]).total_seconds())
        if m not in best or gap < best[m][1]:
            best[m] = (c, gap)
    rows = []
    for m, (c, gap) in best.items():
        b = fits[fits["session"] == m]["b_lin_smallw_V"].mean()
        if not np.isfinite(b):
            continue
        row = cm[cm["session"] == c].iloc[0]
        rows.append({"session": m, "cm": c, "gap_s": gap,
                     "Vt_V": float(row["Vt_V"]),
                     "slcm_star_V": float(row["slcm_star_V"]),
                     "b_V": float(b), "start": t[m]})
    return pd.DataFrame(rows).sort_values("start").reset_index(drop=True)


def tag_multiple(tag: str) -> float:
    """The common mode a condition asked for, as a multiple of s*.

    CONDITIONS reports s as an absolute voltage and s* is MBL-dependent, so the
    tag is the only place the intended multiple survives: "기준" and "s=0" mean
    s = 0, "중앙" the window centre, "중앙xN" that centre scaled by N.
    """
    t = str(tag).strip()
    if not t.startswith("중앙"):
        return 0.0
    rest = t[len("중앙"):]
    if rest.startswith("x"):
        try:
            return float(rest[1:])
        except ValueError:
            return np.nan
    return 1.0



def model_v0(w, alpha: float, b: float, c3: float = 0.0):
    return -np.asarray(w, dtype=float) / alpha + b + c3 * np.asarray(w, float) ** 3


def cm_time(tables: dict, session: str):
    """Wall-clock start of any session, common-mode scans included."""
    ss = tables["SESSIONS"]
    hit = ss[ss["session"] == session]
    if not hit.empty:
        return hit["start"].iloc[0]
    stamp = tables["CMSCAN_FIT"]
    hit = stamp[stamp["session"] == session]
    return pd.to_datetime("2026" + str(hit["run_stamp"].iloc[0]),
                          format="%Y%m%d_%H%M%S")


# ---------------------------------------------------------------------------
# Figure 1: the notch-shift model
# ---------------------------------------------------------------------------
def plot_model(tables: dict, out_path: Path) -> dict:
    fits = tables["FITS"]
    stats: dict = {}

    fig = plt.figure(figsize=(18, 10.5))
    gs = fig.add_gridspec(2, 3, height_ratios=(1.0, 0.92), hspace=0.44,
                          wspace=0.36, left=0.055, right=0.975, top=0.90,
                          bottom=0.085)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[0, 2])
    ax_d = fig.add_subplot(gs[1, 0:2])
    ax_e = fig.add_subplot(gs[1, 2])

    # (a) raw notch curves from the quietest session ---------------------------
    src = fine_source(tables, "FINE3", "alt")
    if src:
        blk = blocks_of(tables, src)
        cur = curves_of(tables, src)
        norm = w_norm(blk["w_store_V"].to_numpy(float))
        cmap = plt.get_cmap(CMAP_W)
        for w, g in cur.groupby("w_store_V"):
            g = g.sort_values("v_V")
            ax_a.plot(g["v_V"], g["code_avg"], "-", color=cmap(norm(w)), lw=1.5,
                      alpha=0.9)
        ax_a.plot(blk["v_notch_V"], blk["floor_code"], "k^", ms=7, mfc="white",
                  mew=1.4, zorder=6, label="notch")
        ax_a.legend(loc="upper center", frameon=True, framealpha=0.9)
        add_w_colorbar(fig, ax_a, norm)
        stats["fine3_blocks"] = int(blk["w_store_V"].nunique())
    ax_a.set_xlabel(LBL_V, fontweight="bold")
    ax_a.set_ylabel(LBL_CODE, fontweight="bold")
    ax_a.set_title("FINE3 alt, 25 stored values", fontsize=15,
                   fontweight="bold", pad=6)
    style_ax(ax_a)
    panel_label(ax_a, "a", dx=-0.20)

    # (b) the full-range mapping and the two models ----------------------------
    cond = best_condition(tables, "OPT1")
    row = fits[(fits["session"] == "OPT1") & (fits["w_range"] == "+-1.5")]
    if cond is not None and not row.empty:
        r = row.iloc[0]
        blk = blocks_of(tables, str(cond["source_file"]))
        blk = blk[blk["w_pass"] == 1]
        w = blk["w_store_V"].to_numpy(float)
        v0 = blk["v_notch_V"].to_numpy(float)
        ww = np.linspace(w.min() * 1.04, w.max() * 1.04, 300)
        ax_b.plot(ww, model_v0(ww, r["alpha_lin"], r["b_lin_V"]), color=C_WARN,
                  ls="--", lw=2.0,
                  label=(r"linear $\alpha$ = " + f"{r['alpha_lin']:.3f}, rms "
                         + f"{r['resid_lin_mV']:.0f} mV"))
        ax_b.plot(ww, model_v0(ww, r["alpha_cub"], r["b_cub_V"], r["c3_V_per_V3"]),
                  color=C_OK, ls="-", lw=2.0,
                  label=(r"cubic $\alpha$ = " + f"{r['alpha_cub']:.3f}, rms "
                         + f"{r['resid_cub_mV']:.0f} mV"))
        ax_b.errorbar(w, v0, yerr=blk["v_notch_se_V"], fmt="o", color=C_MAIN,
                      ms=MARKERSIZE, mfc="white", mew=1.6, capsize=3, zorder=5,
                      label="OPT1 best condition")
        stats["opt1"] = {k: float(r[k]) for k in
                         ("alpha_lin", "alpha_cub", "c3_V_per_V3",
                          "resid_lin_mV", "resid_cub_mV")}
    ax_b.set_xlabel(LBL_W, fontweight="bold")
    ax_b.set_ylabel(LBL_V0, fontweight="bold")
    ax_b.set_title(MODEL_CUBIC, fontsize=15,
                   fontweight="bold", pad=6)
    style_ax(ax_b)
    panel_label(ax_b, "b")
    ax_b.legend(loc="upper right", frameon=True, framealpha=0.9, fontsize=12)

    # (c) residuals, all three full-range campaigns ----------------------------
    for sess in ("OPT1", "OPT2", "OPT3"):
        cond = best_condition(tables, sess)
        row = fits[(fits["session"] == sess) & (fits["w_range"] == "+-1.5")]
        if cond is None or row.empty:
            continue
        r = row.iloc[0]
        blk = blocks_of(tables, str(cond["source_file"]))
        blk = blk[blk["w_pass"] == 1]
        w = blk["w_store_V"].to_numpy(float)
        v0 = blk["v_notch_V"].to_numpy(float)
        col = SESSION_C[sess]
        ax_c.plot(w, 1e3 * (v0 - model_v0(w, r["alpha_lin"], r["b_lin_V"])),
                  "s--", color=col, lw=1.4, ms=5, mfc="white", mew=1.3,
                  alpha=0.85, label=f"{sess} linear")
        ax_c.plot(w, 1e3 * (v0 - model_v0(w, r["alpha_cub"], r["b_cub_V"],
                                          r["c3_V_per_V3"])),
                  "o-", color=col, lw=1.8, ms=6, label=f"{sess} cubic")
    ax_c.axhline(0.0, color=C_REF, lw=1.2)
    ax_c.set_xlabel(LBL_W, fontweight="bold")
    ax_c.set_ylabel("Residual (mV)", fontweight="bold")
    ax_c.set_title("one cubic term, six-fold smaller residual", fontsize=15,
                   fontweight="bold", pad=6)
    style_ax(ax_c)
    panel_label(ax_c, "c")
    ax_c.legend(loc="upper center", ncol=3, frameon=True, framealpha=0.9,
                fontsize=11, columnspacing=0.8, handletextpad=0.4)

    # (d) the dense scan, as a residual to the straight line -------------------
    # v0(w) over +-0.6 V is a straight line to the eye, so plotting it says
    # nothing; the residual is where the cubic shows up. The same c3 measured
    # over +-1.5 V is drawn through it (methods doc 9.2): the 500 mV departure
    # at large w and this 8 mV ripple are one term.
    c3_full = float(fits[fits["w_range"] == "+-1.5"]["c3_V_per_V3"].mean())
    resid = {}
    for order in ("alt", "seq"):
        src = fine_source(tables, "FINE3", order)
        row = fits[(fits["session"] == "FINE3") &
                   (fits["dataset"] == f"finescan {order}")]
        if src is None or row.empty:
            continue
        r = row.iloc[0]
        blk = blocks_of(tables, src)
        blk = blk[blk["w_pass"] == 1].sort_values("w_store_V")
        w = blk["w_store_V"].to_numpy(float)
        v0 = blk["v_notch_V"].to_numpy(float)
        d = 1e3 * (v0 - model_v0(w, r["alpha_lin"], r["b_lin_V"]))
        col = ORDER_C[order]
        ax_d.errorbar(w, d, yerr=1e3 * blk["v_notch_se_V"], fmt="o-", color=col,
                      lw=1.6, ms=6, mfc="white", mew=1.6, capsize=2, zorder=5,
                      label=(order + r": $\alpha$ = " + f"{r['alpha_lin']:.4f}, "
                             + r"own $c_3$ = " + f"{r['c3_V_per_V3']:+.3f}"
                             + r" $\pm$ " + f"{r['c3_se']:.3f}"))
        resid[order] = (w, d)
        stats[f"fine3_{order}"] = float(r["alpha_lin"])
    ax_d.axhline(0.0, color=C_REF, lw=1.2)
    if resid:
        w = next(iter(resid.values()))[0]
        ww = np.linspace(w.min(), w.max(), 200)
        cub = 1e3 * c3_full * ww ** 3
        # Reference, not a fit to these points: the dense passes prefer a
        # smaller c3 (0.128-0.160) than the full range (0.178). They agree
        # within the dense-scan error, which is what methods doc 9.2 claims --
        # and the visible gap is the higher-order term that doc flags as
        # unresolved.
        ax_d.plot(ww, cub - cub.mean(), color=C_OK, ls="--", lw=2.2, zorder=4,
                  label=r"reference: $c_3$ = " + f"{c3_full:+.3f}"
                        + r" V/V$^3$ from the $\pm$1.5 V runs")
    if len(resid) == 2:
        (w_a, d_a), (w_s, d_s) = resid["alt"], resid["seq"]
        common = np.intersect1d(w_a, w_s)
        if common.size > 2:
            ia = np.searchsorted(w_a, common)
            is_ = np.searchsorted(w_s, common)
            rr = float(np.corrcoef(d_a[ia], d_s[is_])[0, 1])
            stats["resid_r"] = rr
            ax_d.text(0.015, 0.04, f"the two passes agree: $r$ = {rr:+.2f}",
                      transform=ax_d.transAxes, fontsize=14, fontweight="bold",
                      color=C_REF)
    ax_d.set_xlabel(LBL_W, fontweight="bold")
    ax_d.set_ylabel("Residual to the straight line (mV)", fontweight="bold")
    ax_d.set_title("FINE3 after the power cycle: the ripple the cubic predicts",
                   fontsize=15, fontweight="bold", pad=6)
    style_ax(ax_d)
    panel_label(ax_d, "d", dx=-0.085)
    ax_d.legend(loc="upper left", frameon=True, framealpha=0.9, fontsize=12)

    # (e) the nine alpha determinations ----------------------------------------
    rows, a_mean, a_sd = alpha_ensemble(fits)
    ax_e.axvspan(a_mean - a_sd, a_mean + a_sd, color=C_MAIN, alpha=0.16,
                 label=f"{a_mean:.4f} " + r"$\pm$ " + f"{a_sd:.4f}")
    ax_e.axvline(a_mean, color=C_MAIN, lw=1.8)
    for i, (label, val, sess) in enumerate(rows):
        ax_e.plot([val], [i], "o", color=SESSION_C.get(sess, C_REF), ms=9,
                  mfc="white", mew=2.0)
    ax_e.set_yticks(np.arange(len(rows)))
    ax_e.set_yticklabels([lab for lab, _, _ in rows], fontsize=12)
    ax_e.invert_yaxis()
    ax_e.set_xlabel(LBL_ALPHA, fontweight="bold")
    ax_e.set_title("nine determinations over 14.5 h", fontsize=15,
                   fontweight="bold", pad=6)
    style_ax(ax_e)
    panel_label(ax_e, "e", dx=-0.46)
    ax_e.legend(loc="lower right", frameon=True, framealpha=0.9)
    stats["alpha_mean"], stats["alpha_sd"] = a_mean, a_sd

    c3 = fits[fits["w_range"] == "+-1.5"]["c3_V_per_V3"]
    stats["c3_mean"], stats["c3_sd"] = float(c3.mean()), float(c3.std(ddof=1))

    fig.suptitle("4T2C notch shift: the model   (chip6 R0C0, 2026-09-04/05)",
                 fontsize=FONT_PANEL + 1, fontweight="bold")
    save_figure(fig, out_path)
    return stats


# ---------------------------------------------------------------------------
# Figure 2: the operating point and its drift
# ---------------------------------------------------------------------------
def plot_operating_point(tables: dict, out_path: Path) -> dict:
    cm, pts = tables["CMSCAN_FIT"], tables["CMSCAN_PTS"]
    stats: dict = {}

    fig = plt.figure(figsize=(18, 6.2))
    gs = fig.add_gridspec(1, 3, wspace=0.30, left=0.055, right=0.985, top=0.84,
                          bottom=0.145)
    ax_a, ax_b, ax_c = (fig.add_subplot(gs[0, i]) for i in range(3))

    order = list(cm["session"])
    shade = CMAP_ORANGE(np.linspace(0.35, 1.0, len(order)))
    cols = dict(zip(order, shade))

    # (a) the scans themselves --------------------------------------------------
    for sess, g in pts.groupby("session"):
        g = g.sort_values("gate_est_V")
        ax_a.plot(g["gate_est_V"], g["code_avg"], "-o", color=cols.get(sess, C_REF),
                  lw=1.6, ms=3.5, mew=0, label=sess)
    for sess in order:
        r = cm[cm["session"] == sess].iloc[0]
        ax_a.axvline(float(r["Vt_V"]), color=cols[sess], ls=":", lw=1.4, alpha=0.8)
    ax_a.set_xlabel(r"Estimated gate voltage $n = \alpha s$ (V)", fontweight="bold")
    ax_a.set_ylabel(LBL_CODE, fontweight="bold")
    ax_a.set_title(r"common-mode scans; dotted = fitted $V_t$", fontsize=15,
                   fontweight="bold", pad=6)
    style_ax(ax_a)
    panel_label(ax_a, "a", dx=-0.16)
    ax_a.legend(loc="upper left", ncol=2, frameon=True, framealpha=0.9,
                fontsize=12)

    # (b) the threshold drift ---------------------------------------------------
    # Everything else the common-mode fit reports is an affine function of Vt:
    # the window is (Vt + V_MBL, Vt] so its width is fixed at |V_MBL| and its
    # centre is Vt + V_MBL/2, and s* = (V_MBL/2 + Vt)/alpha. Drawing any of them
    # would repeat this trace at a different offset, and drawing the 1 V window
    # band flattens the 103 mV drift that is the actual result. They are stated
    # instead.
    t0 = cm_time(tables, order[0])
    hours = np.array([(cm_time(tables, s) - t0).total_seconds() / 3600.0
                      for s in order])
    vt = cm["Vt_V"].to_numpy(float)
    star = cm["slcm_star_V"].to_numpy(float)
    ax_b.plot(hours, vt, "o-", color=C_MAIN, lw=LW_CURVE, ms=MARKERSIZE + 1,
              mfc="white", mew=2.0)
    for k, (h, v, s) in enumerate(zip(hours, vt, order)):
        ax_b.annotate(s, (h, v), textcoords="offset points",
                      xytext=(0, 12 if k % 2 == 0 else -20), ha="center",
                      fontsize=12, fontweight="bold")
    mbl = float(cm["mbl_V"].iloc[0])
    _, a_mean, _ = alpha_ensemble(tables["FITS"])
    ax_b.text(0.035, 0.06,
              rf"window = $(V_t {mbl:+.1f}, V_t]$, width $|V_{{MBL}}|$ = "
              rf"{abs(mbl):.1f} V" "\n"
              rf"$s^{{*}} = (V_{{MBL}}/2 + V_t)/\alpha$, so $\Delta s^{{*}} = "
              rf"\Delta V_t/\alpha$",
              transform=ax_b.transAxes, fontsize=13, fontweight="bold",
              va="bottom", ha="left",
              bbox=dict(boxstyle="round,pad=0.35", facecolor="white",
                        edgecolor=C_REF, alpha=0.9, linewidth=0.8))
    span = float(vt.max() - vt.min())
    ax_b.set_ylim(vt.min() - 0.42 * span, vt.max() + 0.22 * span)
    ax_b.set_xlabel("Hours from CM1", fontweight="bold")
    ax_b.set_ylabel(r"Threshold $V_t$ (V)", fontweight="bold")
    d_vt, d_star = 1e3 * (vt[-1] - vt[0]), 1e3 * (star[-1] - star[0])
    ax_b.set_title(rf"$V_t$ {d_vt:+.0f} mV in {hours[-1]:.1f} h, moving "
                   rf"$s^{{*}}$ by {d_star:+.0f} mV", fontsize=15,
                   fontweight="bold", pad=6)
    style_ax(ax_b)
    panel_label(ax_b, "b")
    stats["dVt_mV"], stats["dstar_mV"] = float(d_vt), float(d_star)

    # (c) the offset b against the threshold -----------------------------------
    pairs = cm_pairs(tables)
    if len(pairs) >= 2:
        v = pairs["Vt_V"].to_numpy(float)
        b = pairs["b_V"].to_numpy(float)
        slope, icept = np.polyfit(v, b, 1)
        r = float(np.corrcoef(v, b)[0, 1])
        vv = np.linspace(v.min() - 0.012, v.max() + 0.012, 100)
        _, a_mean, _ = alpha_ensemble(tables["FITS"])
        ax_c.plot(vv, slope * vv + icept, color=C_REF, ls="--", lw=1.8,
                  label=f"slope {slope:+.2f}")
        ax_c.plot(vv, (1.0 / a_mean) * (vv - v.mean()) + b.mean(), color=C_OK,
                  ls=":", lw=2.0, label=r"$1/\alpha$ = " + f"{1.0 / a_mean:.2f}")
        for _, row in pairs.iterrows():
            ax_c.plot([row["Vt_V"]], [row["b_V"]], "o",
                      color=SESSION_C.get(row["session"], C_MAIN), ms=11,
                      mfc="white", mew=2.2, zorder=5)
            ax_c.annotate(f"{row['session']}\n({row['cm']})",
                          (row["Vt_V"], row["b_V"]), textcoords="offset points",
                          xytext=(10, -4), fontsize=11, fontweight="bold")
        ax_c.set_title(f"$r$ = {r:+.3f}, $n$ = {len(pairs)}", fontsize=15,
                       fontweight="bold", pad=6)
        stats["db_dVt"], stats["r"] = float(slope), r
        stats["inv_alpha"] = float(1.0 / a_mean)
    ax_c.set_xlabel(r"$V_t$ from the preceding common-mode scan (V)",
                    fontweight="bold")
    ax_c.set_ylabel(r"Notch offset  $b$  (V)", fontweight="bold")
    style_ax(ax_c)
    panel_label(ax_c, "c")
    ax_c.legend(loc="upper left", frameon=True, framealpha=0.9)

    fig.suptitle("4T2C operating point: threshold drift and the notch offset",
                 fontsize=FONT_PANEL + 1, fontweight="bold")
    save_figure(fig, out_path)
    return stats


# ---------------------------------------------------------------------------
# Figure 3: the read-condition search
# ---------------------------------------------------------------------------
def plot_conditions(tables: dict, out_path: Path) -> dict:
    cond = tables["CONDITIONS"].copy()
    stats: dict = {}

    # s is reported as an absolute voltage, and s* differs with V_MBL (it is
    # (V_MBL/2 + Vt)/alpha), so it cannot be recovered by scaling within a
    # session. The tag carries the intended multiple directly: "기준"/"s=0" is
    # s = 0, "중앙" is the window centre, "중앙x0.5" and "중앙x1.5" the two
    # flanks.
    cond["s_rel"] = [tag_multiple(t) for t in cond["tag"]]

    fig = plt.figure(figsize=(17, 10))
    gs = fig.add_gridspec(2, 2, hspace=0.40, wspace=0.26, left=0.06,
                          right=0.985, top=0.90, bottom=0.08)
    ax_a, ax_b = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])
    ax_c, ax_d = fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])

    # (a) CV against common mode, at the nominal window rule --------------------
    base = cond[np.isclose(cond["auto_ratio"], 0.5)]
    for mbl in sorted(base["mbl_V"].unique(), reverse=True):
        g = base[base["mbl_V"] == mbl]
        col = MBL_C.get(float(mbl), C_REF)
        for sess, gg in g.groupby("session"):
            gg = gg.sort_values("s_rel")
            ax_a.plot(gg["s_rel"], gg["curv_cv_pct"], "-o", color=col, lw=1.5,
                      ms=6, mfc="white", mew=1.5, alpha=0.85)
        ax_a.plot([], [], "-o", color=col, lw=1.8, ms=7, mfc="white", mew=1.6,
                  label=rf"$V_{{MBL}}$ = {mbl:.1f} V")
    ax_a.axvline(1.0, color=C_REF, ls="--", lw=1.6)
    ax_a.text(1.0, ax_a.get_ylim()[1], " window centre", fontsize=13,
              fontweight="bold", va="top", ha="left", color=C_REF)
    ax_a.set_xlabel(r"Common mode $s$ (multiples of $s^{*}$)", fontweight="bold")
    ax_a.set_ylabel("Curvature CV across $w$ (%)", fontweight="bold")
    ax_a.set_title("three replicates per MBL; lower is better", fontsize=15,
                   fontweight="bold", pad=6)
    style_ax(ax_a)
    panel_label(ax_a, "a", dx=-0.115)
    ax_a.legend(loc="upper left", frameon=True, framealpha=0.9)

    # (b) the best each MBL can do ---------------------------------------------
    width = 0.26
    mbls = sorted(base["mbl_V"].unique(), reverse=True)
    sessions = sorted(base["session"].unique())
    for i, sess in enumerate(sessions):
        vals = []
        for mbl in mbls:
            sub = base[(base["session"] == sess) & (base["mbl_V"] == mbl)]
            vals.append(sub["curv_cv_pct"].min() if not sub.empty else np.nan)
        ax_b.bar(np.arange(len(mbls)) + (i - 1) * width, vals, width,
                 color=SESSION_C.get(sess, C_REF), label=sess,
                 edgecolor="white", linewidth=1.0)
    ax_b.set_xticks(np.arange(len(mbls)))
    ax_b.set_xticklabels([f"{m:.1f} V" for m in mbls])
    ax_b.set_xlabel(r"$V_{MBL}$", fontweight="bold")
    ax_b.set_ylabel("Best curvature CV (%)", fontweight="bold")
    ax_b.set_title(r"$-1.0$ V wins in all three replicates", fontsize=15,
                   fontweight="bold", pad=6)
    style_ax(ax_b)
    panel_label(ax_b, "b")
    ax_b.legend(loc="upper left", frameon=True, framealpha=0.9)

    # (c) the window rule -------------------------------------------------------
    centre = cond[np.isclose(cond["mbl_V"], -1.0) &
                  np.isclose(cond["s_rel"], 1.0)]
    for sess, g in centre.groupby("session"):
        g = g.sort_values("auto_ratio")
        ax_c.plot(g["auto_ratio"], g["curv_cv_pct"], "-o",
                  color=SESSION_C.get(sess, C_REF), lw=1.8, ms=8, mfc="white",
                  mew=1.8, label=sess)
    ax_c.set_xlabel("auto_ratio (fractional rise above the floor)",
                    fontweight="bold")
    ax_c.set_xticks(sorted(centre["auto_ratio"].unique()))
    ax_c.set_ylabel("Curvature CV (%)", fontweight="bold")
    ax_c.set_title(r"at $V_{MBL} = -1.0$ V and the window centre", fontsize=15,
                   fontweight="bold", pad=6)
    style_ax(ax_c)
    panel_label(ax_c, "c", dx=-0.115)
    ax_c.legend(loc="upper right", frameon=True, framealpha=0.9)
    if not centre.empty:
        stats["ratio_cv"] = (centre.groupby("auto_ratio")["curv_cv_pct"]
                             .mean().round(2).to_dict())

    # (d) headroom is what rules out -2.0 V ------------------------------------
    for mbl in sorted(base["mbl_V"].unique(), reverse=True):
        g = base[base["mbl_V"] == mbl]
        ax_d.plot(g["floor_code"], g["headroom"], "o",
                  color=MBL_C.get(float(mbl), C_REF), ms=9, mfc="white", mew=2.0,
                  label=rf"$V_{{MBL}}$ = {mbl:.1f} V")
    ax_d.axhline(0.0, color=C_WARN, ls="--", lw=1.8)
    ax_d.text(0.02, 0.11, "ADC saturated below this line",
              transform=ax_d.transAxes, fontsize=13, fontweight="bold",
              color=C_WARN)
    ax_d.set_xlabel("Notch floor (LSB)", fontweight="bold")
    ax_d.set_ylabel("ADC headroom (LSB)", fontweight="bold")
    ax_d.set_title("a lower MBL lifts the whole curve into the rail",
                   fontsize=15, fontweight="bold", pad=6)
    style_ax(ax_d)
    panel_label(ax_d, "d")
    ax_d.legend(loc="upper right", frameon=True, framealpha=0.9)

    best = cond.loc[cond.groupby("session")["curv_cv_pct"].idxmin()]
    stats["best"] = best[["session", "cond_idx", "mbl_V", "slcm_V",
                          "auto_ratio", "curv_cv_pct"]].to_dict("records")

    fig.suptitle("4T2C read-condition search: 45 conditions ranked by "
                 "curvature CV", fontsize=FONT_PANEL + 1, fontweight="bold")
    save_figure(fig, out_path)
    return stats


# ---------------------------------------------------------------------------
# Figure 4: readout noise and write order
# ---------------------------------------------------------------------------
def plot_noise_order(tables: dict, out_path: Path) -> dict:
    noise, fits, val = tables["NOISE"], tables["FITS"], tables["VALIDATION"]
    stats: dict = {}

    fig = plt.figure(figsize=(17, 10))
    gs = fig.add_gridspec(2, 2, hspace=0.42, wspace=0.26, left=0.06,
                          right=0.985, top=0.90, bottom=0.08)
    ax_a, ax_b = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])
    ax_c, ax_d = fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])

    seq = ["OPT1", "OPT2", "OPT3", "FINE1", "FINE2", "FINE3"]
    noise = noise.set_index("session").reindex(seq).reset_index()
    xs = np.arange(len(seq))

    # (a) per-point ADC scatter --------------------------------------------------
    ax_a.bar(xs, noise["pt_sd_median_code"],
             color=[SESSION_C.get(s, C_REF) for s in seq], edgecolor="white",
             linewidth=1.2)
    ax_a.plot(xs, noise["pt_sd_median_code_300_400"], "k^--", ms=8, lw=1.4,
              mfc="white", mew=1.6, label="at ADC code 300-400")
    ax_a.axvline(4.5, color=C_WARN, ls="--", lw=2.0)
    ax_a.text(4.55, ax_a.get_ylim()[1] * 0.94, " power cycle", color=C_WARN,
              fontsize=14, fontweight="bold", va="top")
    for x, v in zip(xs, noise["pt_sd_median_code"]):
        ax_a.annotate(f"{v:.1f}", (x, v), textcoords="offset points",
                      xytext=(-16, 5), ha="center", fontsize=13,
                      fontweight="bold")
    ax_a.set_xticks(xs)
    ax_a.set_xticklabels(seq)
    ax_a.set_ylim(0, 1.22 * float(np.nanmax(noise["pt_sd_median_code"])))
    ax_a.set_ylabel("Per-point ADC SD (code)", fontweight="bold")
    ax_a.set_title("overnight excess noise, removed by a power cycle",
                   fontsize=15, fontweight="bold", pad=6)
    style_ax(ax_a)
    panel_label(ax_a, "a", dx=-0.115)
    ax_a.legend(loc="upper left", frameon=True, framealpha=0.9)
    stats["pt_sd"] = dict(zip(seq, noise["pt_sd_median_code"].round(2)))

    # (b) and what it cost the measurement -------------------------------------
    se = [fits[fits["session"] == s]["se_notch_med_mV"].mean() for s in seq]
    cv = [fits[fits["session"] == s]["curv_cv_pct"].mean() for s in seq]
    ax_b.plot(noise["pt_sd_median_code"], se, "o", color=C_MAIN, ms=11,
              mfc="white", mew=2.2, label="notch se")
    ax_b2 = ax_b.twinx()
    ax_b2.plot(noise["pt_sd_median_code"], cv, "s", color=C_ALT, ms=10,
               mfc="white", mew=2.2, label="curvature CV")
    for x, y, s in zip(noise["pt_sd_median_code"], se, seq):
        ax_b.annotate(s, (x, y), textcoords="offset points", xytext=(8, -3),
                      fontsize=12, fontweight="bold")
    ax_b.set_xlabel("Per-point ADC SD (code)", fontweight="bold")
    ax_b.set_ylabel("Notch uncertainty (mV)", fontweight="bold", color=C_MAIN)
    ax_b2.set_ylabel("Curvature CV (%)", fontweight="bold", color=C_ALT,
                     fontsize=15)
    ax_b2.tick_params(labelsize=14)
    ax_b.set_title("the readout sets what the device claim can be",
                   fontsize=15, fontweight="bold", pad=6)
    style_ax(ax_b)
    panel_label(ax_b, "b")
    h1, l1 = ax_b.get_legend_handles_labels()
    h2, l2 = ax_b2.get_legend_handles_labels()
    ax_b.legend(h1 + h2, l1 + l2, loc="upper left", frameon=True, framealpha=0.9)

    # (c) the write-order effect ------------------------------------------------
    fine = ["FINE1", "FINE2", "FINE3"]
    xs3 = np.arange(len(fine))
    deltas = []
    for order in ("alt", "seq"):
        vals = [float(fits[(fits["session"] == s) &
                           (fits["dataset"] == f"finescan {order}")]
                      ["alpha_lin"].iloc[0]) for s in fine]
        ax_c.plot(xs3, vals, "o-", color=ORDER_C[order], lw=2.0, ms=11,
                  mfc="white", mew=2.2, label=order)
        deltas.append(vals)
    d = np.array(deltas[0]) - np.array(deltas[1])
    for x, hi, lo, dd in zip(xs3, deltas[0], deltas[1], d):
        ax_c.annotate("", xy=(x, hi), xytext=(x, lo),
                      arrowprops=dict(arrowstyle="<->", color=C_REF, lw=1.4))
        side = -9 if x == xs3[-1] else 9
        ax_c.annotate(rf"$\Delta$ = {dd:+.4f}", (x, 0.5 * (hi + lo)),
                      textcoords="offset points", xytext=(side, -4),
                      ha="right" if side < 0 else "left", fontsize=12,
                      fontweight="bold")
    ax_c.set_xticks(xs3)
    ax_c.set_xticklabels(fine)
    ax_c.set_ylabel(r"Fitted $\alpha$", fontweight="bold")
    ax_c.set_title(rf"write order shifts $\alpha$ by {d.mean():+.4f} "
                   rf"(SD {d.std(ddof=1):.4f}), three for three",
                   fontsize=15, fontweight="bold", pad=6)
    style_ax(ax_c)
    panel_label(ax_c, "c", dx=-0.115)
    ax_c.legend(loc="lower right", frameon=True, framealpha=0.9)
    stats["dalpha_mean"], stats["dalpha_sd"] = float(d.mean()), float(d.std(ddof=1))

    # (d) re-extraction against the instrument ---------------------------------
    lab = [f"{r.session}\n{r.sweep_order}" for r in val.itertuples()]
    xs4 = np.arange(len(val))
    ax_d.bar(xs4, val["rms_diff_mV"], 0.55,
             color=[SESSION_C.get(s, C_REF) for s in val["session"]],
             edgecolor="white", linewidth=1.2, label="rms difference")
    ax_d.plot(xs4, val["max_abs_diff_mV"], "kv", ms=9, mfc="white", mew=1.8,
              label="worst single block")
    for s, g in val.groupby("session"):
        med = fits[fits["session"] == s]["se_notch_med_mV"].mean()
        idx = [i for i, v in enumerate(val["session"]) if v == s]
        ax_d.hlines(med, min(idx) - 0.4, max(idx) + 0.4, color=C_WARN, ls="--",
                    lw=2.0)
    ax_d.plot([], [], color=C_WARN, ls="--", lw=2.0,
              label="notch uncertainty of that session")
    ax_d.set_xticks(xs4)
    ax_d.set_xticklabels(lab, fontsize=13)
    top = max(float(val["max_abs_diff_mV"].max()),
              float(fits["se_notch_med_mV"].max()))
    ax_d.set_ylim(0, 1.30 * top)
    ax_d.set_ylabel("Difference from the on-line fit (mV)", fontweight="bold")
    # The rms is what the doc's claim is about; the worst FINE2 block does clear
    # that session's notch uncertainty, so the title says rms explicitly.
    ax_d.set_title("rms difference stays inside the notch uncertainty",
                   fontsize=15, fontweight="bold", pad=6)
    style_ax(ax_d)
    panel_label(ax_d, "d")
    ax_d.legend(loc="upper left", frameon=True, framealpha=0.9)

    fig.suptitle("4T2C readout noise, write order and extraction cross-check",
                 fontsize=FONT_PANEL + 1, fontweight="bold")
    save_figure(fig, out_path)
    return stats




# ---------------------------------------------------------------------------
# Figure 5: four notches, for the main text
# ---------------------------------------------------------------------------
def pick_weights(blocks: pd.DataFrame, wanted: list) -> list:
    """Nearest measured stored value to each request, in order, no repeats."""
    have = np.sort(blocks["w_store_V"].unique())
    out: list = []
    for target in wanted:
        free = [v for v in have if v not in out]
        if not free:
            break
        hit = float(min(free, key=lambda v: abs(v - target)))
        if abs(hit - target) > 1e-6:
            print(f"[warn] w = {target:+.2f} V not measured; using {hit:+.2f} V")
        out.append(hit)
    return out


def plot_notches(tables: dict, out_path: Path, session: str, order: str,
                 wanted: list, *, fixed_window: bool = False) -> dict:
    """Four notch curves on the measured sweep axis -- the main-text figure.

    Drawn from FINE3 by default: it is the quietest session (3.0 code per point
    after the power cycle), so the notch uncertainty is 3.2 mV against a spacing
    of 79 mV per 0.05 V of stored value, and the `alt` order is the one whose
    slope is not biased by write drift (methods doc 9.5, 9.6).

    The line joins the measured points across the whole sweep; the triangle is
    the fitted v0, taken from the quadratic through the points within
    NOTCH_FIT_SPAN of the sampled minimum (methods doc 7). That quadratic is not
    drawn: outside its fit span it sits 4-6 % of the swing above the data, so
    extending it to the sweep ends would misdescribe the wings.
    """
    n = tables["NOTCH"]
    sel_rows = n[(n["session"] == session) & (n["sweep_order"] == order) &
                 (n["w_pass"] == 1)]
    if sel_rows.empty:
        print(f"[warn] no blocks for {session}/{order}; skipping figure 5")
        return {}
    src = str(sel_rows["source_file"].iloc[0])
    cur_all = curves_of(tables, src)
    cur_all = cur_all[cur_all["w_pass"] == 1]

    sel = pick_weights(sel_rows, wanted)
    blocks = []
    for w in sel:
        row = sel_rows[np.isclose(sel_rows["w_store_V"], w)]
        blk = cur_all[np.isclose(cur_all["w_store_V"], w)].sort_values("v_V")
        if row.empty or blk.empty:
            print(f"[warn] no data for w = {w:+.2f} V; skipping")
            continue
        blocks.append((w, blk, row.iloc[0]))
    if not blocks:
        return {}

    norm = w_norm(np.array([w for w, _, _ in blocks], dtype=float))
    cmap = plt.get_cmap(CMAP_W)

    fig, ax = plt.subplots(figsize=(11.5, 7.6))
    stats: dict = {"session": session, "order": order, "rows": []}
    y_all: list = []

    for w, blk, row in blocks:
        col = cmap(norm(w))
        v0 = float(row["v_notch_V"])
        kappa = float(row["curvature_code_per_V2"])
        floor = float(row["floor_code"])
        code = blk["code_avg"].to_numpy(float)
        swing = float(code.max()) - floor
        if swing <= 0:
            continue

        # The line runs through the measured points over the whole sweep, so
        # each notch reads as one unbroken curve. It is a guide to the eye, not
        # the extraction fit: that quadratic is only valid within
        # NOTCH_FIT_SPAN of the minimum, and extending it across the full sweep
        # overshoots the outermost points by 4-6 % of the swing, because the
        # branches leave saturation out there. v0 (the triangle) still comes
        # from the quadratic.
        y = (code - floor) / swing
        y_all.append(y)
        ax.plot(blk["v_V"], y, "-o", color=col, lw=1.8,
                ms=MARKERSIZE + 1, mew=0, alpha=0.95, zorder=4)
        ax.plot([v0], [0.0], "v", color=col, ms=13, mfc="white", mew=2.0,
                zorder=6)

        stats["rows"].append({
            "w": w, "v0": v0, "v0_se": float(row["v_notch_se_V"]),
            "kappa": kappa, "floor": floor, "swing": swing,
            "asym": float(row["asym"]), "n": int(row["n_points"]),
        })

    ax.set_xlabel(LBL_V, fontweight="bold", fontsize=FONT_BASE + 2)
    ax.set_ylabel(LBL_CODE_NORM, fontweight="bold", fontsize=FONT_BASE + 2)
    ax.tick_params(labelsize=FONT_BASE)
    if fixed_window:
        # Exactly 0 to 1: the floor is 0 and the peak is 1 by construction, so
        # the frame is the normalisation. Readout noise puts a few points just
        # below the floor and those are clipped, so they are counted.
        ax.set_ylim(0.0, 1.0)
        clipped_low(ax, np.concatenate([r_y for r_y in y_all]), "figure 5")
        apply_v_xlim(ax, np.concatenate([b["v_V"].to_numpy(float)
                                         for _w, b, _r in blocks]), "figure 5")
    else:
        # The floor is 0 by normalisation, so the axis starts there in both
        # renders; only the top and the sweep range differ between them.
        ax.set_ylim(0.0, 1.06)
        clipped_low(ax, np.concatenate(y_all) if y_all else np.array([]),
                    "figure 5 (default)")
    style_ax(ax)

    # No legend, no in-plot text: the colour-to-w mapping and the numbers below
    # go in the caption. The console table carries them.
    se_med = float(np.median([r["v0_se"] for r in stats["rows"]]))
    v0s = sorted(r["v0"] for r in stats["rows"])
    ws = sorted(r["w"] for r in stats["rows"])
    step_w = abs(ws[1] - ws[0]) if len(ws) > 1 else np.nan
    step_v = float(np.mean(np.abs(np.diff(v0s)))) if len(v0s) > 1 else np.nan
    stats["step_w"] = step_w
    stats["step_mV"] = 1e3 * step_v
    stats["se_med_mV"] = 1e3 * se_med
    stats["step_mV"] = 1e3 * step_v
    stats["sigma"] = step_v / se_med if se_med > 0 else np.nan

    save_figure(fig, out_path)
    return stats


def plot_dense_notches(tables: dict, out_path: Path, session: str,
                       order: str, *, fixed_window: bool = False) -> dict:
    """Every block of one dense pass, on its own -- figure 1(a) standalone.

    Same content as panel 1(a) but at full size: all 25 stored values of the
    pass, code normalised per block, shaded by w, and the ensemble exponent p.
    This
    is the one that shows the notch walking continuously across the sweep axis,
    which the four-block main-text figure trades away for legibility.
    """
    n = tables["NOTCH"]
    rows = n[(n["session"] == session) & (n["sweep_order"] == order) &
             (n["w_pass"] == 1)]
    if rows.empty:
        print(f"[warn] no blocks for {session}/{order}; skipping figure 6")
        return {}
    src = str(rows["source_file"].iloc[0])
    cur = curves_of(tables, src)
    cur = cur[cur["w_pass"] == 1]

    norm = w_norm(rows["w_store_V"].to_numpy(float))
    cmap = plt.get_cmap(CMAP_W)

    fig, ax = plt.subplots(figsize=(12.5, 7.6))
    ps, swings, y_all = [], [], []
    for _, r in rows.iterrows():
        g = cur[np.isclose(cur["w_store_V"], r["w_store_V"]) &
                np.isclose(cur["visit_k"], r["visit_k"])].sort_values("v_V")
        if g.empty:
            continue
        code = g["code_avg"].to_numpy(float)
        floor = float(r["floor_code"])
        swing = float(code.max()) - floor
        if swing <= 0:
            continue
        swings.append(swing)
        y = (code - floor) / swing
        y_all.append(y)
        ax.plot(g["v_V"], y, "-",
                color=cmap(norm(r["w_store_V"])), lw=1.7, alpha=0.9)
        # p is built from differences and a ratio, so it is invariant under any
        # affine rescaling of the code axis: normalising y leaves it unchanged.
        q = exponent_cfree(g["v_V"], code, float(r["v_notch_V"]))
        if np.isfinite(q):
            ps.append((float(r["w_store_V"]), q))

    ax.set_xlabel(LBL_V, fontweight="bold", fontsize=FONT_BASE + 2)
    ax.set_ylabel(LBL_CODE_NORM, fontweight="bold", fontsize=FONT_BASE + 2)
    ax.tick_params(labelsize=FONT_BASE)
    if fixed_window:
        ax.set_ylim(0.0, 1.0)
        clipped_low(ax, np.concatenate(y_all) if y_all else np.array([]),
                    "figure 6")
        apply_v_xlim(ax, cur["v_V"].to_numpy(float), "figure 6")
    else:
        ax.set_ylim(0.0, 1.14)     # headroom for the exponent box
        clipped_low(ax, np.concatenate(y_all) if y_all else np.array([]),
                    "figure 6 (default)")
    style_ax(ax)
    add_w_colorbar(fig, ax, norm)

    # One ensemble number, not 25: the estimator's per-curve SD is 0.16, so a
    # single block's exponent is noise (methods doc 8).
    if ps:
        q = np.array([v for _, v in ps], dtype=float)
        p_mean = float(q.mean())
        p_sem = float(q.std(ddof=1) / np.sqrt(q.size)) if q.size > 1 else np.nan
        # Inside the headroom on the default render; above the frame on the
        # cropped one, where the curve peaks reach the top edge.
        ax.text(0.5, 1.02 if fixed_window else 0.965,
                MODEL_POWER + ",   "
                + rf"$p$ = {p_mean:.2f} $\pm$ {p_sem:.2f}   "
                rf"({q.size} blocks, C-free estimator)",
                transform=ax.transAxes, ha="center",
                va="bottom" if fixed_window else "top",
                fontsize=FONT_BASE - 1, fontweight="bold", color=C_REF,
                bbox=dict(boxstyle="round,pad=0.38", facecolor="white",
                          edgecolor=C_REF, alpha=0.92, linewidth=0.9))

    stats = {
        "session": session, "order": order,
        "p": ps,
        "p_mean": float(np.mean([v for _, v in ps])) if ps else np.nan,
        "p_sd": (float(np.std([v for _, v in ps], ddof=1))
                 if len(ps) > 1 else np.nan),
        "p_sem": (float(np.std([v for _, v in ps], ddof=1) / np.sqrt(len(ps)))
                  if len(ps) > 1 else np.nan),
        "blocks": int(rows["w_store_V"].nunique()),
        "points": int(len(cur)),
        "w_lo": float(rows["w_store_V"].min()),
        "w_hi": float(rows["w_store_V"].max()),
        "v0_lo": float(rows["v_notch_V"].min()),
        "v0_hi": float(rows["v_notch_V"].max()),
        "swing_lo": min(swings) if swings else np.nan,
        "swing_hi": max(swings) if swings else np.nan,
        "se_med_mV": 1e3 * float(rows["v_notch_se_V"].median()),
        "curv_cv_pct": 100.0 * float(rows["curvature_code_per_V2"].std(ddof=1)
                                     / rows["curvature_code_per_V2"].mean()),
    }
    save_figure(fig, out_path)
    return stats


def plot_mapping_solo(tables: dict, out_path: Path, session: str) -> dict:
    """The notch-shift mapping on its own -- panel 1(b) standalone.

    v0 against the stored value over the full +-1.5 V range, at that session's
    best read condition, with the straight line only.

    Note what the figure then shows: over +-1.5 V the line leaves 119-127 mV rms
    against a 4-6 mV notch uncertainty, and the data visibly bow away from it at
    both ends. The fitted alpha is also range-dependent (0.705-0.716 here against
    0.619-0.627 over +-0.6 V), which is the same departure seen as a parameter
    shift. Methods doc 9.2 resolves both with one cubic term; that term is not
    drawn here. The cubic fit is still computed and printed to the console.
    """
    fits = tables["FITS"]
    cond = best_condition(tables, session)
    row = fits[(fits["session"] == session) & (fits["w_range"] == "+-1.5")]
    if cond is None or row.empty:
        print(f"[warn] no full-range fit for {session}; skipping figure 7")
        return {}
    r = row.iloc[0]

    blk = blocks_of(tables, str(cond["source_file"]))
    blk = blk[blk["w_pass"] == 1]
    w = blk["w_store_V"].to_numpy(float)
    v0 = blk["v_notch_V"].to_numpy(float)

    fig, ax = plt.subplots(figsize=(9.6, 7.6))
    ww = np.linspace(w.min() * 1.05, w.max() * 1.05, 400)
    ax.plot(ww, model_v0(ww, r["alpha_lin"], r["b_lin_V"]), color=C_WARN,
            ls="--", lw=2.4, zorder=3,
            label=(r"$\alpha$ = " + f"{r['alpha_lin']:.3f},  rms "
                   + f"{r['resid_lin_mV']:.0f} mV"))
    ax.errorbar(w, v0, yerr=blk["v_notch_se_V"], fmt="o", color=C_MAIN,
                ms=MARKERSIZE + 3, mfc="white", mew=2.2, capsize=4, zorder=5)

    ax.set_xlabel(LBL_W, fontweight="bold", fontsize=FONT_BASE + 2)
    ax.set_ylabel(LBL_V0, fontweight="bold", fontsize=FONT_BASE + 2)
    ax.tick_params(labelsize=FONT_BASE)
    style_ax(ax)
    # No model name and no session name: which replicate this is belongs in the
    # caption.
    ax.legend(loc="upper right", frameon=True, framealpha=0.92,
              fontsize=FONT_BASE - 2)
    ax.text(0.03, 0.03,
            MODEL_LINEAR,
            transform=ax.transAxes, ha="left", va="bottom",
            fontsize=FONT_BASE, fontweight="bold", color=C_REF)

    stats = {
        "session": session,
        "cond_idx": int(cond["cond_idx"]),
        "n_w": int(len(w)),
        "alpha_lin": float(r["alpha_lin"]),
        "alpha_cub": float(r["alpha_cub"]),
        "c3": float(r["c3_V_per_V3"]),
        "c3_se": float(r["c3_se"]),
        "resid_lin_mV": float(r["resid_lin_mV"]),
        "resid_cub_mV": float(r["resid_cub_mV"]),
        "se_med_mV": 1e3 * float(blk["v_notch_se_V"].median()),
    }
    save_figure(fig, out_path)
    return stats

# ---------------------------------------------------------------------------
# Console summary
# ---------------------------------------------------------------------------
def report(tables: dict, res: dict) -> None:
    n = tables["NOTCH"]
    print("\n--- 4T2C notch campaign, chip6 R0C0, 2026-09-04/05 ---")
    print(f"blocks             : {len(n)} notches from "
          f"{len(tables['CURVES'])} bias points, "
          f"{n['session'].nunique()} sessions")

    m = res.get(1)
    if m:
        print(f"alpha (small w)    : {m['alpha_mean']:.4f} +- {m['alpha_sd']:.4f} "
              f"({100 * m['alpha_sd'] / m['alpha_mean']:.1f} %, 9 determinations)")
        print(f"c3 (full range)    : {m['c3_mean']:+.4f} +- {m['c3_sd']:.4f} V/V^3")
        o = m.get("opt1", {})
        if o:
            print(f"OPT1 +-1.5 V       : linear alpha {o['alpha_lin']:.3f} "
                  f"rms {o['resid_lin_mV']:.0f} mV  ->  cubic "
                  f"{o['alpha_cub']:.3f} rms {o['resid_cub_mV']:.0f} mV")
            print("  the linear alpha is range-dependent, which is the symptom "
                  "the cubic term removes")

    op = res.get(2)
    if op:
        print(f"Vt drift           : {op['dVt_mV']:+.0f} mV over the campaign, "
              f"moving s* by {op['dstar_mV']:+.0f} mV")
        if "db_dVt" in op:
            print(f"b vs Vt            : db/dVt = {op['db_dVt']:+.3f} against "
                  f"1/alpha = {op['inv_alpha']:.3f} (r = {op['r']:+.3f}, n = 4)")
            print("  alpha carries between sessions, b does not -- but b is "
                  "predictable from the common-mode scan")

    cd = res.get(3)
    if cd and cd.get("best"):
        print("best condition per replicate:")
        for r in cd["best"]:
            print(f"  {r['session']}  cond {int(r['cond_idx']):2d}  "
                  f"MBL {r['mbl_V']:+.1f} V  s {r['slcm_V']:+.2f} V  "
                  f"ratio {r['auto_ratio']:.2f}  ->  CV {r['curv_cv_pct']:.2f} %")

    ns = res.get(4)
    if ns:
        print(f"per-point ADC SD   : "
              + ", ".join(f"{k} {v:.1f}" for k, v in ns["pt_sd"].items()))
        print(f"write order        : alpha(alt) - alpha(seq) = "
              f"{ns['dalpha_mean']:+.4f} +- {ns['dalpha_sd']:.4f} "
              f"({100 * ns['dalpha_mean'] / 0.6231:.1f} % of alpha, 3 of 3)")
    nt = res.get(5)
    if nt and nt.get("rows"):
        print(f"main-text notches ({nt['session']} {nt['order']}):")
        print(f"  {'w (V)':>7} {'v0 (V)':>10} {'se (mV)':>8} {'kappa':>7} "
              f"{'floor':>7} {'asym':>6} {'pts':>4}")
        for r in nt["rows"]:
            print(f"  {r['w']:>+7.2f} {r['v0']:>+10.4f} {1e3 * r['v0_se']:>8.1f} "
                  f"{r['kappa']:>7.0f} {r['floor']:>7.0f} {r['asym']:>6.3f} "
                  f"{r['n']:>4d}")
        print(f"  notch step {nt['step_mV']:.0f} mV against se "
              f"{nt['se_med_mV']:.1f} mV = {nt['sigma']:.0f} sigma, so the four "
              "are separated far beyond the measurement floor")
        sw = [r["swing"] for r in nt["rows"]]
        print(f"  figure 5 divides each block by its own swing "
              f"({min(sw):.0f}-{max(sw):.0f} LSB, "
              f"{100 * (max(sw) - min(sw)) / np.mean(sw):.0f} % spread) -- the "
              "auto window held every block to a 44-49 % rise, so the "
              "normalisation barely rescales them")
    dn = res.get(6)
    if dn:
        print(f"dense pass ({dn['session']} {dn['order']}): {dn['blocks']} "
              f"blocks, {dn['points']} points, w {dn['w_lo']:+.2f} to "
              f"{dn['w_hi']:+.2f} V -> v0 {dn['v0_lo']:+.3f} to "
              f"{dn['v0_hi']:+.3f} V")
        print(f"  notch se {dn['se_med_mV']:.1f} mV, curvature CV "
              f"{dn['curv_cv_pct']:.1f} % across the {dn['blocks']} stored "
              "values")
        if np.isfinite(dn.get("p_mean", np.nan)):
            q = [v for _, v in dn["p"]]
            print(f"  exponent p = {dn['p_mean']:.3f} +- {dn['p_sem']:.3f} "
                  f"(SEM), per-curve SD {dn['p_sd']:.3f}, range "
                  f"{min(q):.2f}-{max(q):.2f}")
            print("  C-free symmetrised estimator (methods doc 8); it carries a "
                  "+0.03-0.05 bias, and its per-curve SD is why only the "
                  "ensemble is quoted")
        if np.isfinite(dn.get("swing_lo", np.nan)):
            lo, hi = dn["swing_lo"], dn["swing_hi"]
            print(f"  figure 6 divides each block by its own swing "
                  f"({lo:.0f}-{hi:.0f} LSB, "
                  f"{200 * (hi - lo) / (hi + lo):.0f} % spread); p is unchanged "
                  "by that, being invariant under any affine rescaling of y")
    mp = res.get(7)
    if mp:
        print(f"mapping ({mp['session']}, cond {mp['cond_idx']}, "
              f"{mp['n_w']} stored values):")
        print(f"  linear  alpha {mp['alpha_lin']:.3f}   rms "
              f"{mp['resid_lin_mV']:.0f} mV")
        print(f"  cubic   alpha {mp['alpha_cub']:.3f}   c3 "
              f"{mp['c3']:+.3f} +- {mp['c3_se']:.3f} V/V^3   rms "
              f"{mp['resid_cub_mV']:.0f} mV")
        print(f"  notch se {mp['se_med_mV']:.1f} mV, so the cubic residual "
              f"({mp['resid_cub_mV']:.0f} mV) is still "
              f"{mp['resid_cub_mV'] / mp['se_med_mV']:.0f}x the measurement "
              "floor -- a higher-order term is present but unresolved")
    print("note: conditions are ranked by curvature CV, not by a fitted "
          "exponent -- see methods doc section 8.\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
PLOTTERS = {
    1: plot_model,
    2: plot_operating_point,
    3: plot_conditions,
    4: plot_noise_order,
}


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Plot the 2026-09-04/05 4T2C notch-shift campaign.")
    ap.add_argument("--data-dir", type=Path, default=ROOT)
    ap.add_argument("--outdir", type=Path, default=OUTDIR)
    ap.add_argument("--figures", type=int, nargs="+", choices=sorted(STEMS),
                    default=sorted(STEMS), metavar="N",
                    help="which figures to render (default: all)")
    ap.add_argument("--session", default=MAIN_SESSION,
                    help="session for figure 5 (default: %(default)s)")
    ap.add_argument("--order", default=MAIN_ORDER, choices=("alt", "seq"),
                    help="sweep order for figure 5 (default: %(default)s)")
    ap.add_argument("--weights", type=float, nargs="+", default=list(MAIN_W),
                    metavar="W",
                    help="stored values for figure 5 (default: "
                         + " ".join(f"{w:+.1f}" for w in MAIN_W) + ")")
    ap.add_argument("--opt-session", default=MAIN_OPT,
                    help="full-range session for figure 7 (default: "
                         "%(default)s)")
    ap.add_argument("--tag", default="",
                    help="suffix for the figure-5 filename, so a second choice "
                         "of --weights does not overwrite the first")
    args = ap.parse_args(argv)

    if not args.data_dir.is_dir():
        print(f"[error] data dir not found: {args.data_dir}", file=sys.stderr)
        return 1
    try:
        tables = load_dataset(args.data_dir)
    except FileNotFoundError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1

    apply_plot_style()
    res: dict = {}
    for num in args.figures:
        if num == 5:
            stem = STEMS[5] + (f"_{args.tag}" if args.tag else "")
            res[5] = plot_notches(tables, args.outdir / f"{stem}.png",
                                  args.session, args.order, args.weights)
            plot_notches(tables,
                         args.outdir / f"{stem}{FIXED_SUFFIX}.png",
                         args.session, args.order, args.weights,
                         fixed_window=True)
        elif num == 6:
            res[6] = plot_dense_notches(tables, args.outdir / f"{STEMS[6]}.png",
                                        args.session, args.order)
            plot_dense_notches(
                tables, args.outdir / f"{STEMS[6]}{FIXED_SUFFIX}.png",
                args.session, args.order, fixed_window=True)
        elif num == 7:
            res[7] = plot_mapping_solo(tables, args.outdir / f"{STEMS[7]}.png",
                                       args.opt_session)
        else:
            res[num] = PLOTTERS[num](tables, args.outdir / f"{STEMS[num]}.png")
    report(tables, res)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
