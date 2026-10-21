#!/usr/bin/env python3
"""
4T2C notch-response figures from the 0903 auto-window dataset.

    python plot_4t2c_notch_response.py
    python plot_4t2c_notch_response.py --data-dir DIR --outdir DIR

Inputs (any of the three files in the directory; the workbook is preferred
because it is a superset of the two CSVs):

  ``4t2c_auto_dataset_0903.xlsx``   sheets README / notch / curves / matrix_* /
                                    p_vs_rise / alpha_local / symmetry / recheck_*
  ``4t2c_auto_0903_curves.csv``     = the ``curves`` sheet
  ``4t2c_auto_0903_notch.csv``      = the ``notch`` sheet

The measurement (chip6 / 4t2c_a, 2026-09-03, MBL -1.5 V, BL 0 V, SL differential,
TIA CH8 with Rf = 1 MOhm, 3 samples per point): for each stored weight w from
-1.5 to +1.5 V in 0.1 V steps, the SL differential voltage v is swept around the
notch and the TIA code recorded, out to where the code has risen ~50 % above the
notch floor. Each block is fitted with

    code = C + A * |v - v0|^p          (v0 = notch position, A ~ curvature/2)

``curves`` carries the raw points with dv = v - v0, dcode = code - floor,
dcode_norm = (code - C)/A and dcode_over_a2 = dcode/(curvature/2) -- the last one
equals dv^2 exactly when p = 2.

Figure 1 ``4t2c_notch_response.png``
  (a) raw notch curves, one per stored weight, shaded by w
  (b) normalised collapse dcode_norm vs dv against |dv|^p
  (c) p = 2 check: dcode/(curvature/2) against dv^2
  (d) curvature vs w -- flat means the shape does not depend on what is stored
  (e) fitted exponent p per w, with the ensemble mean

Figure 2 ``4t2c_notch_mapping.png``
  (a) notch position v0 vs stored weight, with the piecewise local-alpha fits
  (b) antisymmetry residual v0(+w) + v0(-w)
  (c) exponent vs the allowed rise window -- accuracy against operating range
  (d) w = -1.5 measured at pass 1 and again 31 blocks later (drift check)

Figure 3 ``4t2c_notch_selected.png``
  a single panel: the selected stored weights on the measured sweep axis with the
  code scaled per block onto 0..1 between its notch floor and its highest point,
  so the notches line up at 0 and only the position on v differs

Defaults to w = -1.5, -0.5, +0.5, +1.5 V (``SELECTED_W``); ``--weights`` takes any
list and snaps each request to the nearest measured weight, and ``--tag`` keeps
one choice from overwriting another.

Per the dataset README, a single block's p carries +-0.1 to 0.2, so panel 1(e) is
about the ensemble, not about any one w.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")           # save-only; no display needed (WSL, ssh, CI)

import matplotlib.pyplot as plt          # noqa: E402
import numpy as np                       # noqa: E402
import pandas as pd                      # noqa: E402
from matplotlib.colors import TwoSlopeNorm  # noqa: E402

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
OUTDIR = ROOT / "figures"

XLSX_GLOB = "4t2c_auto_dataset*.xlsx"
CURVES_GLOB = "4t2c_auto*curves.csv"
NOTCH_GLOB = "4t2c_auto*notch.csv"

FIG1_STEM = "4t2c_notch_response"
FIG2_STEM = "4t2c_notch_mapping"
FIG3_STEM = "4t2c_notch_selected"
FIG1_SIZE = (18, 10)
FIG2_SIZE = (13, 10)

# Four stored weights spanning the measured range, evenly spaced at 1.0 V.
# Override with --weights; a request that was not measured snaps to the nearest w.
SELECTED_W = (-1.5, -0.5, 0.5, 1.5)


CODE_MV = 1.221         # 1 TIA code = 1.221 mV = 1.221 nA (README)

# Notation, palette and style come from notch_common, shared with the other
# notch scripts in this folder so the figures read as one set.
from notch_common import (            # noqa: E402
    DPI, FONT_BASE, FONT_AXIS, FONT_PANEL, LW_CURVE, GRID_ALPHA, MARKERSIZE,
    CMAP_W, C_REF, C_FIT, C_MAIN, C_ALT, C_OK, C_WARN,
    LBL_V, LBL_W, LBL_V0, LBL_DV, LBL_CODE, LBL_CURV, LBL_P,
    apply_plot_style, style_ax, panel_label,
)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def _numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Every cell in these exports is stored as text; coerce what we can."""
    out = df.copy()
    for col in out.columns:
        if col == "timestamp":
            continue
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def find_one(data_dir: Path, pattern: str) -> Optional[Path]:
    hits = sorted(data_dir.glob(pattern))
    if len(hits) > 1:
        print(f"[warn] {len(hits)} files match {pattern!r}; using {hits[-1].name}")
    return hits[-1] if hits else None


def load_dataset(data_dir: Path) -> dict:
    """Return the available tables. The workbook wins; the CSVs are the fallback."""
    tables: dict = {}
    xlsx = find_one(data_dir, XLSX_GLOB)
    if xlsx is not None:
        book = pd.read_excel(xlsx, sheet_name=None)
        for name, df in book.items():
            if name != "README":
                tables[name] = _numeric(df)
        print(f"[in ] {xlsx.name}: sheets {', '.join(sorted(tables))}")

    for key, pattern in (("curves", CURVES_GLOB), ("notch", NOTCH_GLOB)):
        if key in tables:
            continue
        path = find_one(data_dir, pattern)
        if path is not None:
            tables[key] = _numeric(pd.read_csv(path, encoding="utf-8-sig"))
            print(f"[in ] {path.name} -> {key}")
    return tables


# ---------------------------------------------------------------------------
# Plot style
# ---------------------------------------------------------------------------
def w_norm(w: np.ndarray) -> TwoSlopeNorm:
    """Diverging scale centred on w = 0, spanning the measured weights."""
    lim = float(np.nanmax(np.abs(w)))
    return TwoSlopeNorm(vmin=-lim, vcenter=0.0, vmax=lim)


def add_w_colorbar(fig: plt.Figure, ax: plt.Axes, norm: TwoSlopeNorm) -> None:
    sm = plt.cm.ScalarMappable(norm=norm, cmap=plt.get_cmap(CMAP_W))
    cbar = fig.colorbar(sm, ax=ax, pad=0.02)
    cbar.set_label(LBL_W, fontweight="bold", fontsize=16)
    cbar.ax.tick_params(labelsize=14)


def ensemble_p(notch: pd.DataFrame, p_col: str,
               p_vs_rise: Optional[pd.DataFrame], allow_pct: float = 50.0) -> tuple:
    """Ensemble exponent and its standard error.

    Plain mean +- SEM across blocks, which is what the dataset's own ``p_vs_rise``
    aggregate reports; that row is used directly when present so this figure and
    panel 2(c) cannot disagree. An inverse-variance weighting would be the usual
    choice, but here the per-block errors track the fitted value, so weighting
    pulls the mean off the dataset's headline number.
    """
    if p_vs_rise is not None and "allow_rise_pct" in p_vs_rise.columns:
        hit = p_vs_rise[np.isclose(p_vs_rise["allow_rise_pct"], allow_pct)]
        if len(hit):
            return float(hit["p_mean"].iloc[0]), float(hit["p_sem"].iloc[0])
    y = notch[p_col].to_numpy(float)
    y = y[np.isfinite(y)]
    if y.size == 0:
        return float("nan"), float("nan")
    return float(y.mean()), float(y.std(ddof=1) / np.sqrt(y.size))


# ---------------------------------------------------------------------------
# Figure 1: the response itself
# ---------------------------------------------------------------------------
def plot_response(tables: dict, out_path: Path, title: str) -> dict:
    curves, notch = tables["curves"], tables["notch"]
    norm = w_norm(notch["w_store"].to_numpy(float))
    cmap = plt.get_cmap(CMAP_W)

    fig = plt.figure(figsize=FIG1_SIZE)
    gs = fig.add_gridspec(2, 3, height_ratios=(1.0, 0.85), hspace=0.45, wspace=0.36,
                          left=0.055, right=0.985, top=0.90, bottom=0.09)
    ax_a = fig.add_subplot(gs[0, 0:2])
    ax_b = fig.add_subplot(gs[0, 2])
    ax_c = fig.add_subplot(gs[1, 0])
    ax_d = fig.add_subplot(gs[1, 1])
    ax_e = fig.add_subplot(gs[1, 2])

    # (a) raw notch curves -----------------------------------------------------
    for w, blk in curves.groupby("w_store"):
        blk = blk.sort_values("v")
        ax_a.plot(blk["v"], blk["code_avg"], "-o", color=cmap(norm(w)), lw=1.6,
                  ms=3.5, mew=0)
    ax_a.plot(notch["v_notch"], notch["code_floor"], "k^", ms=8, mfc="white",
              mew=1.6, zorder=6, label="notch (parabolic fit)")
    ax_a.set_xlabel(LBL_V, fontweight="bold")
    ax_a.set_ylabel(LBL_CODE, fontweight="bold")
    style_ax(ax_a)
    panel_label(ax_a, "a", dx=-0.08)
    ax_a.legend(loc="upper center", frameon=True, framealpha=0.9)
    add_w_colorbar(fig, ax_a, norm)

    # (b) normalised collapse --------------------------------------------------
    p_col = "p_r50" if "p_r50" in notch.columns else "p_full"
    p_mean, p_sem = ensemble_p(notch, p_col, tables.get("p_vs_rise"))
    for w, blk in curves.groupby("w_store"):
        blk = blk.sort_values("dv")
        ax_b.plot(blk["dv"], blk["dcode_norm"], "-", color=cmap(norm(w)),
                  lw=1.2, alpha=0.85)
    dv_ref = np.linspace(curves["dv"].min(), curves["dv"].max(), 300)
    ax_b.plot(dv_ref, np.abs(dv_ref) ** p_mean, color=C_REF, ls="--", lw=2.2,
              zorder=6, label=rf"$|dv|^{{p}}$, $p$ = {p_mean:.3f}")
    ax_b.set_xlabel(LBL_DV, fontweight="bold")
    ax_b.set_ylabel("$(code - C)\\,/\\,A$", fontweight="bold")
    style_ax(ax_b)
    panel_label(ax_b, "b")
    ax_b.legend(loc="upper center", frameon=True, framealpha=0.9)

    # (c) the p = 2 check ------------------------------------------------------
    dv2 = curves["dv"].to_numpy(float) ** 2
    ratio_y = curves["dcode_over_a2"].to_numpy(float)
    ax_c.plot(dv2, ratio_y, "o", color=C_MAIN, ms=4, mew=0, alpha=0.55,
              label="measured points")
    lim = float(np.nanmax(dv2)) * 1.05
    ax_c.plot([0, lim], [0, lim], color=C_REF, ls="--", lw=2.0,
              label="ideal $p = 2$")
    ok = np.isfinite(dv2) & np.isfinite(ratio_y) & (dv2 > 0.01)
    ratio = ratio_y[ok] / dv2[ok]
    ax_c.set_xlim(0, lim)
    ax_c.set_ylim(0, lim)
    ax_c.set_xlabel("$dv^2$ (V$^2$)", fontweight="bold")
    ax_c.set_ylabel(r"$dcode\,/\,(\kappa/2)$ (V$^2$)", fontweight="bold")
    style_ax(ax_c)
    panel_label(ax_c, "c")
    ax_c.legend(loc="upper left", frameon=True, framealpha=0.9)
    ax_c.text(0.97, 0.06, f"median ratio {np.median(ratio):.3f}",
              transform=ax_c.transAxes, ha="right", fontsize=15, fontweight="bold")

    # (d) curvature vs stored weight ------------------------------------------
    kap = notch["curvature"].to_numpy(float)
    ax_d.plot(notch["w_store"], kap, "o-", color=C_OK, lw=LW_CURVE, ms=MARKERSIZE,
              mfc="white", mew=1.6)
    ax_d.axhline(kap.mean(), color=C_REF, ls="--", lw=1.6,
                 label=f"mean {kap.mean():.0f}")
    ax_d.fill_between([notch["w_store"].min(), notch["w_store"].max()],
                      kap.mean() - kap.std(ddof=1), kap.mean() + kap.std(ddof=1),
                      color=C_REF, alpha=0.12,
                      label=rf"$\pm 1\sigma$ ({100 * kap.std(ddof=1) / kap.mean():.1f} %)")
    ax_d.set_xlabel(LBL_W, fontweight="bold")
    ax_d.set_ylabel(LBL_CURV, fontweight="bold")
    span = kap.max() - kap.min()
    ax_d.set_ylim(kap.min() - 0.40 * span, kap.max() + 0.06 * span)
    style_ax(ax_d)
    panel_label(ax_d, "d")
    ax_d.legend(loc="lower center", ncol=2, frameon=True, framealpha=0.9, fontsize=13)

    # (e) exponent per stored weight ------------------------------------------
    ax_e.errorbar(notch["w_store"], notch[p_col],
                  yerr=notch[p_col.replace("p_", "p_se_")], fmt="o", color=C_MAIN,
                  ms=MARKERSIZE - 1, capsize=3, mfc="white", mew=1.6,
                  label=f"per block ({p_col})")
    ax_e.axhline(2.0, color=C_REF, ls="--", lw=1.8, label="ideal $L_2$")
    ax_e.axhspan(p_mean - p_sem, p_mean + p_sem, color=C_MAIN, alpha=0.18,
                 label=rf"mean {p_mean:.3f} $\pm$ {p_sem:.3f}")
    ax_e.set_xlabel(LBL_W, fontweight="bold")
    ax_e.set_ylabel(LBL_P, fontweight="bold")
    p_lo = float(np.nanmin(notch[p_col] - notch[p_col.replace("p_", "p_se_")]))
    p_hi = float(np.nanmax(notch[p_col] + notch[p_col.replace("p_", "p_se_")]))
    ax_e.set_ylim(p_lo - 0.05 * (p_hi - p_lo), p_hi + 0.32 * (p_hi - p_lo))
    style_ax(ax_e)
    panel_label(ax_e, "e")
    ax_e.legend(loc="upper left", frameon=True, framealpha=0.9, fontsize=13)

    fig.suptitle(title, fontsize=FONT_PANEL, fontweight="bold")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=DPI, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"[ok] wrote {out_path}")

    return {"p_col": p_col, "p_mean": p_mean, "p_sem": p_sem,
            "kappa_mean": float(kap.mean()), "kappa_std": float(kap.std(ddof=1)),
            "ratio_median": float(np.median(ratio)),
            "ratio_q": (float(np.percentile(ratio, 25)), float(np.percentile(ratio, 75)))}


# ---------------------------------------------------------------------------
# Figure 2: the mapping and the checks around it
# ---------------------------------------------------------------------------
def plot_mapping(tables: dict, out_path: Path, title: str) -> dict:
    notch = tables["notch"]
    fig, axes = plt.subplots(2, 2, figsize=FIG2_SIZE)
    ax_a, ax_b, ax_c, ax_d = axes[0, 0], axes[0, 1], axes[1, 0], axes[1, 1]
    stats: dict = {}

    # (a) notch position vs stored weight, with the local-alpha segments -------
    w = notch["w_store"].to_numpy(float)
    v0 = notch["v_notch"].to_numpy(float)
    ax_a.errorbar(w, v0, yerr=notch["v_notch_se"], fmt="o", color=C_MAIN,
                  ms=MARKERSIZE, capsize=3, mfc="white", mew=1.6,
                  label=r"$v_0$ $\pm$ 1 s.e.")
    alpha = tables.get("alpha_local")
    if alpha is not None:
        for i, row in alpha.iterrows():
            seg = np.array([row["w_lo"], row["w_hi"]], float)
            ax_a.plot(seg, row["slope"] * seg + row["intercept"], "-",
                      color=C_ALT, lw=2.4, alpha=0.9,
                      label="local fit" if i == 0 else None)
            ax_a.annotate(f"{row['alpha_local']:.2f}",
                          xy=(seg.mean(), row["slope"] * seg.mean() + row["intercept"]),
                          xytext=(0, 12 if seg.mean() >= 0 else -20),
                          textcoords="offset points", ha="center",
                          fontsize=13, fontweight="bold", color=C_ALT)
        stats["alpha_range"] = (float(alpha["alpha_local"].min()),
                                float(alpha["alpha_local"].max()))
    i0 = int(np.argmin(np.abs(w)))
    stats["v0_at_zero"] = float(v0[i0])
    stats["v0_se_at_zero"] = float(notch["v_notch_se"].to_numpy(float)[i0])
    ax_a.set_xlabel(LBL_W, fontweight="bold")
    ax_a.set_ylabel("Notch position $v_0$ (V)", fontweight="bold")
    style_ax(ax_a)
    panel_label(ax_a, "a", dx=-0.18)
    ax_a.legend(loc="upper right", frameon=True, framealpha=0.9)
    ax_a.text(0.03, 0.06, r"labels: local $\alpha$", transform=ax_a.transAxes,
              fontsize=14, fontweight="bold", color=C_ALT)

    # (b) antisymmetry ---------------------------------------------------------
    sym = tables.get("symmetry")
    if sym is not None:
        resid = sym["sum"].to_numpy(float)
        mean_abs = float(np.nanmean(np.abs(resid)))
        stats["sym_mean_abs"] = mean_abs
        ax_b.axhline(0.0, color=C_REF, ls="--", lw=1.6)
        ax_b.axhspan(-mean_abs, mean_abs, color=C_OK, alpha=0.15,
                     label=rf"mean $|$residual$|$ = {1e3 * mean_abs:.1f} mV")
        ax_b.plot(sym["w"], resid, "D-", color=C_OK, lw=LW_CURVE,
                  ms=MARKERSIZE - 1, mfc="white", mew=1.6,
                  label=r"$v_0(+w) + v_0(-w)$")
        ax_b.set_xlabel(r"$|w|$ (V)", fontweight="bold")
        ax_b.set_ylabel("Antisymmetry residual (V)", fontweight="bold")
        ax_b.legend(loc="lower left", frameon=True, framealpha=0.9)
    else:
        ax_b.text(0.5, 0.5, "no symmetry sheet", transform=ax_b.transAxes,
                  ha="center", va="center", fontsize=16)
    style_ax(ax_b)
    panel_label(ax_b, "b", dx=-0.18)

    # (c) exponent vs allowed rise window -------------------------------------
    pvr = tables.get("p_vs_rise")
    if pvr is not None:
        pvr = pvr[np.isfinite(pvr["allow_rise_pct"])].sort_values("allow_rise_pct")
        ax_c.axhline(2.0, color=C_REF, ls="--", lw=1.8, label="ideal $L_2$")
        ax_c.errorbar(pvr["allow_rise_pct"], pvr["p_mean"], yerr=pvr["p_sem"],
                      fmt="o-", color=C_MAIN, lw=LW_CURVE, ms=MARKERSIZE,
                      capsize=3, mfc="white", mew=1.6, label=r"ensemble $p$")
        for _, row in pvr.iterrows():
            ax_c.annotate(f"{row['mean_half_V']:.2f} V",
                          xy=(row["allow_rise_pct"], row["p_mean"]),
                          xytext=(0, -20), textcoords="offset points",
                          ha="center", fontsize=13, fontweight="bold", color=C_FIT)
        ax_c.set_xscale("log")
        ax_c.set_xticks(pvr["allow_rise_pct"])
        ax_c.set_xticklabels([f"{int(x)}" for x in pvr["allow_rise_pct"]])
        ax_c.tick_params(axis="x", which="minor", length=0)
        ax_c.margins(x=0.12)
        ax_c.set_xlabel("Allowed rise above floor (%)", fontweight="bold")
        ax_c.set_ylabel(r"Ensemble exponent $p$", fontweight="bold")
        ax_c.legend(loc="upper right", frameon=True, framealpha=0.9)
        ax_c.text(0.03, 0.06, "labels: mean half-window", transform=ax_c.transAxes,
                  fontsize=14, fontweight="bold", color=C_FIT)
        stats["p_vs_rise"] = pvr[["allow_rise_pct", "p_mean", "p_sem",
                                  "mean_half_V"]].to_numpy(float)
    else:
        ax_c.text(0.5, 0.5, "no p_vs_rise sheet", transform=ax_c.transAxes,
                  ha="center", va="center", fontsize=16)
    style_ax(ax_c)
    panel_label(ax_c, "c", dx=-0.18)

    # (d) drift recheck --------------------------------------------------------
    rc, rn = tables.get("recheck_curve"), tables.get("recheck_notch")
    if rc is not None:
        colors = {1: C_MAIN, 2: C_ALT}
        for i, (p, blk) in enumerate(rc.groupby("w_pass")):
            blk = blk.sort_values("v")
            label = f"pass {int(p)}"
            if rn is not None:
                hit = rn[rn["w_pass"] == p]
                if len(hit):
                    label += f"  ($v_0$ = {float(hit['v_notch'].iloc[0]):.4f} V)"
            ax_d.plot(blk["v"], blk["code_avg"], "o-",
                      color=colors.get(int(p), C_OK), lw=LW_CURVE,
                      ms=MARKERSIZE - 2, mfc="white", mew=1.4, label=label)
        if rn is not None and len(rn) >= 2:
            dv0 = float(rn["v_notch"].iloc[1] - rn["v_notch"].iloc[0])
            se = float(np.hypot(*rn["v_notch_se"].iloc[:2].to_numpy(float)))
            stats["recheck_dv0"] = dv0
            stats["recheck_sigma"] = abs(dv0) / se if se > 0 else float("nan")
            ax_d.text(0.03, 0.06,
                      rf"$\Delta v_0$ = {1e3 * dv0:+.1f} mV "
                      rf"({stats['recheck_sigma']:.1f}$\sigma$) after 31 blocks",
                      transform=ax_d.transAxes, ha="left",
                      fontsize=15, fontweight="bold")
        ax_d.set_xlabel("SL differential sweep $v$ (V)", fontweight="bold")
        ax_d.set_ylabel("TIA code (LSB)", fontweight="bold")
        ax_d.legend(loc="upper right", frameon=True, framealpha=0.9, fontsize=13)
    else:
        ax_d.text(0.5, 0.5, "no recheck sheet", transform=ax_d.transAxes,
                  ha="center", va="center", fontsize=16)
    style_ax(ax_d)
    panel_label(ax_d, "d", dx=-0.18)

    fig.suptitle(title, fontsize=FONT_PANEL, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=DPI, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"[ok] wrote {out_path}")
    return stats


# ---------------------------------------------------------------------------
# Figure 3: four stored weights on their own
# ---------------------------------------------------------------------------
def pick_weights(notch: pd.DataFrame, wanted: list) -> list:
    """Nearest measured weight to each request, in order, without repeats."""
    have = np.sort(notch["w_store"].to_numpy(float))
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


def plot_selected(tables: dict, out_path: Path, title: str,
                  wanted: list) -> dict:
    """The selected stored weights on the absolute sweep axis, code normalised.

    The sweep voltage is kept as measured, so the notch shift with the stored
    weight stays readable. The TIA code is scaled per block onto 0..1 between its
    own notch floor and its own highest measured point, which removes the
    floor-to-floor offset (150 to 282 LSB across the full weight range) and puts
    every notch at 0. The console table keeps the absolute codes.

    Note that the blocks did not all rise equally far above their floor -- the
    auto window overshot on some, so ``rise_pct`` spans 48 to 137 % -- and this
    scaling divides each block by its own swing. A block that only rose 48 % is
    therefore stretched about twice as hard as one that rose 100 %.
    """
    curves, notch = tables["curves"], tables["notch"]
    sel = pick_weights(notch, wanted)
    if not sel:
        print("[warn] no weights selected; skipping figure 3")
        return {}

    cmap = plt.get_cmap(CMAP_W)
    suffix = "r50" if "p_r50" in notch.columns else "full"

    blocks = []
    for w in sel:
        blk = curves[np.isclose(curves["w_store"], w)].sort_values("v")
        row = notch[np.isclose(notch["w_store"], w)]
        if blk.empty or row.empty:
            print(f"[warn] no data for w = {w:+.2f} V; skipping")
            continue
        blocks.append((w, blk, row.iloc[0]))
    if not blocks:
        return {}

    # The ramp is stretched over the selected weights rather than over all 31.
    # Still diverging and still centred on w = 0, so the sign reading is intact;
    # for the default -1.5..+1.5 selection this is the same scale figure 1 uses,
    # but a near-zero selection stays legible instead of fading to white.
    norm = w_norm(np.array([w for w, _, _ in blocks], dtype=float))

    fig, ax = plt.subplots(figsize=(11.5, 7.5))
    stats: dict = {"weights": [w for w, _, _ in blocks], "rows": []}

    for w, blk, row in blocks:
        col = cmap(norm(w))
        code = blk["code_avg"].to_numpy(float)
        lo, hi = float(code.min()), float(code.max())
        swing = hi - lo
        y = (code - lo) / swing if swing > 0 else np.zeros_like(code)
        v0 = float(row[f"v0_{suffix}"])
        y0 = (float(row["code_floor"]) - lo) / swing if swing > 0 else np.nan

        ax.plot(blk["v"], y, "-o", color=col, lw=LW_CURVE,
                ms=MARKERSIZE - 1, mew=0, label=rf"$w$ = {w:+.1f} V")
        ax.plot([v0], [y0], "^", color=col, ms=12, mfc="white",
                mew=1.8, zorder=6)

        stats["rows"].append({
            "w": w, "v0": v0, "v0_se": float(row["v_notch_se"]),
            "kappa": float(row["curvature"]), "p": float(row[f"p_{suffix}"]),
            "p_se": float(row[f"p_se_{suffix}"]), "floor": float(row["code_floor"]),
            "rise": float(row["rise_pct"]), "n": int(row["n_points"]),
            "code_max": hi, "swing": swing,
        })

    ax.set_xlabel("SL differential sweep $v$ (V)", fontweight="bold")
    ax.set_ylabel("Normalised code   (0 = notch floor, 1 = peak)",
                  fontweight="bold")
    ax.set_ylim(-0.06, 1.22)
    style_ax(ax)
    ax.legend(loc="upper center", ncol=len(blocks), frameon=True,
              framealpha=0.9, fontsize=16)
    ax.set_title(title, fontsize=FONT_PANEL, fontweight="bold", pad=12)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=DPI, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"[ok] wrote {out_path}")
    return stats


# ---------------------------------------------------------------------------
# Console summary
# ---------------------------------------------------------------------------
def report(tables: dict, res: dict, mstats: dict,
           sel: Optional[dict] = None) -> None:
    notch, curves = tables["notch"], tables["curves"]
    print("\n--- 4T2C notch response ---")
    print(f"blocks             : {len(notch)} stored weights, "
          f"{len(curves)} sweep points "
          f"({curves.groupby('w_store').size().min()}-"
          f"{curves.groupby('w_store').size().max()} per block)")
    print(f"exponent p         : {res['p_mean']:.3f} +- {res['p_sem']:.3f} "
          f"({res['p_col']}), {abs(res['p_mean'] - 2) / res['p_sem']:.1f} sigma from L2")
    print(f"curvature          : {res['kappa_mean']:.0f} +- {res['kappa_std']:.0f} "
          f"code/V^2 ({100 * res['kappa_std'] / res['kappa_mean']:.1f} % across all w) "
          "-- the shape does not depend on the stored value")
    q_lo, q_hi = res["ratio_q"]
    print(f"p = 2 fidelity     : dcode/(kappa/2)/dv^2 = {res['ratio_median']:.3f} "
          f"(quartiles {q_lo:.2f}-{q_hi:.2f})")
    if "v0_at_zero" in mstats:
        print(f"offset at w = 0    : {1e3 * mstats['v0_at_zero']:+.1f} +- "
              f"{1e3 * mstats['v0_se_at_zero']:.1f} mV")
    if "sym_mean_abs" in mstats:
        print(f"antisymmetry       : mean |v0(+w) + v0(-w)| = "
              f"{1e3 * mstats['sym_mean_abs']:.1f} mV")
    if "alpha_range" in mstats:
        lo, hi = mstats["alpha_range"]
        print(f"local alpha        : {lo:.3f} to {hi:.3f} -- not a constant, so a "
              "single-alpha predictor mis-centres the window")
    if "recheck_dv0" in mstats:
        print(f"drift (31 blocks)  : dv0 = {1e3 * mstats['recheck_dv0']:+.1f} mV "
              f"({mstats['recheck_sigma']:.1f} sigma)")

    rise = notch["rise_pct"].to_numpy(float)
    if np.nanmax(rise) > 60:
        print(f"  [check] rise above floor spans {np.nanmin(rise):.0f}-"
              f"{np.nanmax(rise):.0f} % against a +50 % target: the window "
              "predictor was stale, so blocks are not equally centred")
    if sel and sel.get("rows"):
        print("\nselected weights (figure 3)")
        print(f"  {'w (V)':>7} {'v0 (V)':>10} {'se (mV)':>8} {'kappa':>7} "
              f"{'p':>6} {'floor':>7} {'max':>7} {'swing':>7} {'rise %':>7} "
              f"{'pts':>4}")
        for r in sel["rows"]:
            print(f"  {r['w']:>+7.1f} {r['v0']:>+10.4f} {1e3 * r['v0_se']:>8.1f} "
                  f"{r['kappa']:>7.0f} {r['p']:>6.2f} {r['floor']:>7.0f} "
                  f"{r['code_max']:>7.0f} {r['swing']:>7.0f} {r['rise']:>7.0f} "
                  f"{r['n']:>4d}")
        sw = [r["swing"] for r in sel["rows"]]
        print(f"  figure 3 divides each block by its own swing ({min(sw):.0f} to "
              f"{max(sw):.0f} LSB), so the vertical scaling is not shared")
        rows = sel["rows"]
        if len(rows) > 1:
            steps = [(rows[i + 1]["v0"] - rows[i]["v0"])
                     / (rows[i + 1]["w"] - rows[i]["w"])
                     for i in range(len(rows) - 1)]
            print("  dv0/dw per step  : " + ", ".join(f"{s:+.3f}" for s in steps)
                  + "  -- unequal, so one global alpha does not describe the map")
    print(f"\nnote: 1 code = {CODE_MV} mV; a single block's p carries +-0.1 to 0.2, "
          "so read panel 1(e) as an ensemble, not per w.\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="Plot the 4T2C notch-response dataset.")
    ap.add_argument("--data-dir", type=Path, default=ROOT)
    ap.add_argument("--outdir", type=Path, default=OUTDIR)
    ap.add_argument("--weights", type=float, nargs="+", default=list(SELECTED_W),
                    metavar="W",
                    help="stored weights for the selected-weight figure "
                         f"(default: {' '.join(f'{w:+.1f}' for w in SELECTED_W)})")
    ap.add_argument("--tag", default="",
                    help="suffix for the figure-3 filename, so a second choice of "
                         "--weights does not overwrite the first")
    args = ap.parse_args(argv)

    if not args.data_dir.is_dir():
        print(f"[error] data dir not found: {args.data_dir}", file=sys.stderr)
        return 1
    tables = load_dataset(args.data_dir)
    missing = [k for k in ("curves", "notch") if k not in tables]
    if missing:
        print(f"[error] missing required table(s): {', '.join(missing)}; looked for "
              f"{XLSX_GLOB}, {CURVES_GLOB}, {NOTCH_GLOB} in {args.data_dir}",
              file=sys.stderr)
        return 1

    apply_plot_style()
    res = plot_response(tables, args.outdir / f"{FIG1_STEM}.png",
                        "4T2C notch response (chip6 / 4t2c_a, auto window, 0903)")
    mstats = plot_mapping(tables, args.outdir / f"{FIG2_STEM}.png",
                          "4T2C notch mapping and consistency checks")
    stem = FIG3_STEM + (f"_{args.tag}" if args.tag else "")
    sel = plot_selected(tables, args.outdir / f"{stem}.png",
                        f"4T2C notch at {len(args.weights)} stored weights",
                        args.weights)
    report(tables, res, mstats, sel)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
