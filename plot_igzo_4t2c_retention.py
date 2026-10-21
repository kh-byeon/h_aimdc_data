#!/usr/bin/env python3
"""
IGZO 4T2C (complementary 2T1C) retention figures.

    python plot_igzo_4t2c_retention.py                 # both figures
    python plot_igzo_4t2c_retention.py --no-map        # retention only
    python plot_igzo_4t2c_retention.py --data-dir DIR --outdir DIR

The session directory is taken from ``--data-dir``, else $IGZO_4T2C_DIR, else the
first hit from ``data_dir_candidates()`` / ``data_dir_globs()``. Windows paths are
accepted under WSL (``D:\\...`` -> ``/mnt/d/...``).

Inputs (the 0902 igzo_4t2c_retention session):
  * ``4t2c_retention_10h_summary.csv`` -- one row per checkpoint over 10 h.
      v_notch [V]      SL-diff notch position from the parabolic fit (+/- v_notch_se)
      w_est   [V]      stored weight recovered from the notch map (+/- w_se)
      retention_pct    100 * w_est / w_est(t=0)
      dw_mV            1000 * (w_est - w_est(t=0))
      code_min/swing   ADC code at the notch and notch depth (read-path health)
  * ``4t2c_map_*.xlsx`` -- the w_store -> v_notch map measured just before the
      retention run; used for the calibration figure (sheets ``response``/``notch``).

Figure 1 ``igzo_4t2c_retention.png``  (2x2)
  (a) w_est vs time, log-x, with the t = 0 as-written baseline and a
      log10(t)-linear guide
  (b) retention [%] vs time with the 90 % / 50 % criteria
  (c) weight loss dw [mV] vs time
  (d) notch code_min and swing vs time (read-path drift diagnostic)

Figure 1b ``igzo_4t2c_retention_pct.png``
  Panel (b) on its own, without the panel letter, for use as a standalone figure.

Figure 2 ``igzo_4t2c_notch_map.png``  (1x2)
  (a) ADC code vs SL-diff sweep v for each written w_store
  (b) the extracted v_notch(w_store) calibration, with the retention start and
      end points marked on it
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import sys
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")           # save-only; no display needed (WSL, ssh, CI)

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np               # noqa: E402
import pandas as pd              # noqa: E402

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SESSION_DIRNAME = "igzo_4t2c_retention"
ONEDRIVE_DIRNAME = "OneDrive"
# Path from the OneDrive desktop down to the session parent. The desktop folder
# itself is globbed, not spelled out: it is localised (``바탕 화면`` / ``Desktop``).
REL_FROM_DESKTOP = "on going work/Distance is all you need/RAG/This work/measured_data"
DATA_DIR_ENV = "IGZO_4T2C_DIR"

# Drive letters to look at, best guess first. On WSL/POSIX these become /mnt/d,
# /mnt/c, ... -- a Windows ``D:\`` path means nothing to a Linux interpreter.
DRIVE_LETTERS = ("d", "c", "e", "f")

OUTDIR = Path(__file__).resolve().parent / "figures"

SUMMARY_GLOB = "*retention*summary*.csv"
MAP_GLOB = "*4t2c_map*.xlsx"

FIG1_STEM = "igzo_4t2c_retention"
FIG1B_STEM = "igzo_4t2c_retention_pct"    # the retention-% panel on its own
FIG2_STEM = "igzo_4t2c_notch_map"
FIG1_SIZE = (13, 10)
FIG1B_SIZE = (8, 6)
FIG2_SIZE = (13, 5.5)


# Style (aligned with plot_fefet_retention.py / plot_fefet_notch_shift.py)
# Notation, palette and style come from notch_common, shared with the other notch
# scripts in this folder.
from notch_common import (            # noqa: E402
    DPI, FONT_BASE, FONT_AXIS, FONT_PANEL, LW_CURVE, GRID_ALPHA, MARKERSIZE,
    C_MAIN, C_FIT, C_LOSS, C_CODE, C_SWING, C_CRIT,
    LBL_V, LBL_W, LBL_W_EST, LBL_V0, LBL_CODE, LBL_SWING, LBL_DW,
    apply_plot_style, style_ax, panel_label,
)




RETENTION_CRITERIA = (90.0, 50.0)   # % of the as-written weight
T_10YR_H = 10 * 365.25 * 24.0


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def to_local_path(raw) -> Path:
    """Accept a Windows path even when running under WSL: ``D:\\OneDrive\\x`` and
    ``D:/OneDrive/x`` both become ``/mnt/d/OneDrive/x`` on a POSIX interpreter."""
    s = str(raw)
    if os.name == "nt":
        return Path(s)
    m = re.match(r"^([A-Za-z]):[\\/](.*)$", s)
    if m:
        return Path(f"/mnt/{m.group(1).lower()}/{m.group(2)}".replace("\\", "/"))
    return Path(s.replace("\\", "/")) if "\\" in s else Path(s)


def drive_roots() -> list:
    """Filesystem roots for the Windows drives, on Windows and on WSL alike."""
    roots = []
    for letter in DRIVE_LETTERS:
        root = Path(f"{letter.upper()}:/") if os.name == "nt" else Path(f"/mnt/{letter}")
        if root.is_dir():
            roots.append(root)
    return roots


def data_dir_candidates() -> list:
    """Concrete directories to test, in order."""
    return [Path(__file__).resolve().parent / SESSION_DIRNAME]


def data_dir_globs() -> list:
    """(root, pattern) pairs to glob, in order. The last one is a broad sweep."""
    out = []
    for root in drive_roots():
        od = root / ONEDRIVE_DIRNAME
        if not od.is_dir():
            continue
        out.append((od, f"*/{REL_FROM_DESKTOP}/{SESSION_DIRNAME}"))
        out.append((od, f"{REL_FROM_DESKTOP}/{SESSION_DIRNAME}"))
        out.append((od, f"**/measured_data/{SESSION_DIRNAME}"))
    return out


def resolve_data_dir(explicit: Optional[Path]) -> Optional[Path]:
    """Locate the session directory: --data-dir, then $IGZO_4T2C_DIR, then the
    known locations, then a glob under <drive>/OneDrive."""
    if explicit is not None:
        cand = to_local_path(explicit)
        return cand if cand.is_dir() else None

    env = os.environ.get(DATA_DIR_ENV)
    if env:
        cand = to_local_path(env)
        if cand.is_dir():
            return cand
        print(f"[warn] ${DATA_DIR_ENV} is set but not a directory: {cand}")

    for cand in data_dir_candidates():
        if cand.is_dir():
            return cand

    for root, pattern in data_dir_globs():
        try:
            hits = sorted(p for p in root.glob(pattern) if p.is_dir())
        except OSError:
            continue
        if hits:
            return hits[0]
    return None


def find_one(data_dir: Path, pattern: str, what: str) -> Optional[Path]:
    hits = sorted(data_dir.glob(pattern))
    if not hits:
        return None
    if len(hits) > 1:
        print(f"[warn] {len(hits)} {what} files match {pattern!r}; using {hits[-1].name}")
    return hits[-1]


def load_summary(csv_path: Path) -> pd.DataFrame:
    """Read the checkpoint summary; utf-8-sig strips the BOM on the first header."""
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df = df.sort_values("t_h").reset_index(drop=True)
    for col in ("t_h", "v_notch", "v_notch_se", "w_est", "w_se",
                "retention_pct", "dw_mV", "code_min", "swing", "curvature"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df


def load_map(xlsx_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return the (response, notch) sheets of the w_store -> v_notch map workbook."""
    response = pd.read_excel(xlsx_path, sheet_name="response")
    notch = pd.read_excel(xlsx_path, sheet_name="notch")
    # The map ends with a repeat of the first w_store (``seq_recheck``); keep the
    # first visit of each level so the calibration curve stays single-valued.
    notch = notch.drop_duplicates(subset="w_store", keep="first")
    notch = notch.sort_values("w_store").reset_index(drop=True)
    return response, notch


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
def fit_log_linear(t_h: np.ndarray, y: np.ndarray) -> Optional[dict]:
    """Fit y = a + b * log10(t_h) over the positive-time checkpoints."""
    t_h = np.asarray(t_h, float)
    y = np.asarray(y, float)
    m = (t_h > 0) & np.isfinite(t_h) & np.isfinite(y)
    if int(m.sum()) < 2:
        return None
    logt = np.log10(t_h[m])
    b, a = np.polyfit(logt, y[m], 1)
    resid = y[m] - (a + b * logt)
    ss_tot = float(np.sum((y[m] - y[m].mean()) ** 2))
    r2 = 1.0 - float(np.sum(resid ** 2)) / ss_tot if ss_tot > 0 else float("nan")
    return {"a": float(a), "b": float(b), "r2": r2, "n_fit": int(m.sum()),
            "t_min": float(t_h[m].min()), "t_max": float(t_h[m].max())}


def eval_fit(fit: dict, t_h) -> np.ndarray:
    return fit["a"] + fit["b"] * np.log10(np.asarray(t_h, float))


def solve_fit_time(fit: dict, y_target: float) -> float:
    """Time [h] at which the log-linear guide reaches y_target (nan if flat)."""
    if not np.isfinite(fit["b"]) or abs(fit["b"]) < 1e-15:
        return float("nan")
    return float(10.0 ** ((y_target - fit["a"]) / fit["b"]))


KNEE_MIN_DT_H = 0.5     # ignore the minute-spaced early checkpoints
KNEE_FACTOR = 2.5       # loss rate that counts as "fast" vs the early-time rate


def knee_time(df: pd.DataFrame, factor: float = KNEE_FACTOR) -> Optional[float]:
    """Start of the fast-decay regime: the first interval whose loss rate exceeds
    ``factor`` x the early-time rate.

    The 10 h trace is flat for hours and then falls off, so a single log-linear
    slope hides the interesting number -- when the fast decay starts. Only
    intervals of at least ``KNEE_MIN_DT_H`` are used: the 1-2 min checkpoints at
    the head of the run divide read noise by a tiny dt and would otherwise
    dominate the rate estimate.
    """
    t = df["t_h"].to_numpy(float)
    w = df["w_est"].to_numpy(float)
    dt = np.diff(t)
    rate = np.diff(w) / np.where(dt > 0, dt, np.nan)     # V/h, negative = loss
    ok = np.isfinite(rate) & (dt >= KNEE_MIN_DT_H)
    if int(ok.sum()) < 4:
        return None
    idx = np.flatnonzero(ok)
    loss = -rate[idx]                                   # positive = losing weight
    base = float(np.median(np.abs(loss[: max(loss.size // 2, 2)])))
    if not np.isfinite(base) or base <= 0:
        return None
    hits = idx[loss > factor * base]
    return float(t[hits[0]]) if hits.size else None


def format_hours(t_h: float) -> str:
    if not np.isfinite(t_h):
        return "n/a"
    if t_h >= 8766.0:
        return f"{t_h / 8766.0:.2f} yr"
    if t_h >= 24.0:
        return f"{t_h / 24.0:.1f} d"
    return f"{t_h:.1f} h"


# ---------------------------------------------------------------------------
# Plot style
# ---------------------------------------------------------------------------
def apply_plot_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": FONT_BASE,
            "axes.labelsize": FONT_AXIS,
            "axes.titlesize": FONT_PANEL,
            "legend.fontsize": 15,
            "xtick.labelsize": FONT_BASE,
            "ytick.labelsize": FONT_BASE,
        }
    )


def style_ax(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(True)
    ax.spines["right"].set_visible(True)
    ax.tick_params(axis="both", which="major", width=1.5, length=6)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontweight("bold")
    ax.grid(True, which="major", alpha=GRID_ALPHA, linewidth=0.5)


def panel_label(ax: plt.Axes, text: str) -> None:
    ax.text(-0.14, 1.04, text, transform=ax.transAxes,
            fontsize=FONT_PANEL, fontweight="bold", va="bottom", ha="left")


def log_time_axis(ax: plt.Axes, t_pos: np.ndarray) -> None:
    ax.set_xscale("log")
    ax.set_xlabel("Retention time (h)", fontweight="bold")
    lo = 10.0 ** np.floor(np.log10(t_pos.min()))
    hi = 10.0 ** np.ceil(np.log10(t_pos.max()))
    ax.set_xlim(lo, hi)


# ---------------------------------------------------------------------------
# Figure 1: retention
# ---------------------------------------------------------------------------
def draw_retention_percent(ax: plt.Axes, df: pd.DataFrame, w0: float,
                           panel: Optional[str] = None) -> None:
    """Retention [%] against linear time, including the t = 0 point.

    Shared by the 2x2 overview (as panel b) and the standalone export, which
    carries no panel letter -- it is a figure in its own right, not a panel.
    """
    t_all = df["t_h"].to_numpy(float)          # keeps the t = 0 point
    ax.axhline(100.0, color="k", ls="--", lw=1.4)
    y_lo = float(df["retention_pct"].min())
    for crit in RETENTION_CRITERIA:
        if crit >= y_lo - 15.0:
            ax.axhline(crit, color=C_CRIT, ls="-.", lw=1.4, alpha=0.8)
            ax.text(0.15, crit + 0.8, f"{crit:.0f} %", color=C_CRIT,
                    fontsize=15, fontweight="bold", va="bottom")
    r_err = 100.0 * df["w_se"].to_numpy(float) / w0
    ax.errorbar(t_all, df["retention_pct"], yerr=r_err, fmt="s-", color=C_MAIN,
                lw=LW_CURVE, ms=MARKERSIZE, capsize=3, mfc="white", mew=1.6,
                label="measured (linear time)")
    knee = knee_time(df)
    if knee is not None:
        ax.axvline(knee, color=C_LOSS, ls=":", lw=2.0,
                   label=f"onset of fast decay ~{knee:.0f} h")
    ax.set_xlabel("Retention time (h)", fontweight="bold")
    ax.set_ylabel("Retention (%)", fontweight="bold")
    ax.set_xlim(-0.3, float(t_all.max()) * 1.03)
    style_ax(ax)
    if panel:
        panel_label(ax, panel)
    ax.legend(loc="lower left", frameon=True, framealpha=0.9)


def plot_retention_percent(df: pd.DataFrame, w0: float, out_path: Path) -> None:
    """The retention-vs-time panel on its own, with no panel letter."""
    fig, ax = plt.subplots(figsize=FIG1B_SIZE)
    draw_retention_percent(ax, df, w0)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=DPI, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"[ok] wrote {out_path}")



def plot_retention(df: pd.DataFrame, out_path: Path, title: str) -> dict:
    pos = df[df["t_h"] > 0]
    t = pos["t_h"].to_numpy(float)
    zero = df[df["t_h"] == 0]
    w0 = float(zero["w_est"].iloc[0]) if len(zero) else float(df["w_est"].iloc[0])
    v0 = float(zero["v_notch"].iloc[0]) if len(zero) else float(df["v_notch"].iloc[0])

    fit_w = fit_log_linear(t, pos["w_est"].to_numpy(float))
    fit_r = fit_log_linear(t, pos["retention_pct"].to_numpy(float))
    tt = np.logspace(np.log10(t.min()), np.log10(t.max()), 200)

    fig, axes = plt.subplots(2, 2, figsize=FIG1_SIZE)
    ax_a, ax_b, ax_c, ax_d = axes[0, 0], axes[0, 1], axes[1, 0], axes[1, 1]

    # (a) stored weight -------------------------------------------------------
    ax_a.axhline(w0, color="k", ls="--", lw=1.4,
                 label=f"t = 0 (as written): {w0:.4f} V")
    ax_a.errorbar(t, pos["w_est"], yerr=pos["w_se"], fmt="o-", color=C_MAIN,
                  lw=LW_CURVE, ms=MARKERSIZE, capsize=3, mfc="white", mew=1.6,
                  label=r"$w_{\mathrm{est}}$ $\pm$ 1 s.e.")
    if fit_w is not None:
        ax_a.plot(tt, eval_fit(fit_w, tt), color=C_FIT, ls=":", lw=2.0,
                  label=(rf"$a+b\log_{{10}}t$: {fit_w['b'] * 1e3:.0f} mV/dec"
                         rf" ($R^2$ = {fit_w['r2']:.2f})"))
    ax_a.set_ylabel(LBL_W_EST, fontweight="bold")
    log_time_axis(ax_a, t)
    style_ax(ax_a)
    panel_label(ax_a, "a")
    ax_a.legend(loc="lower left", frameon=True, framealpha=0.9)

    # (b) retention %, linear time so the late-time knee is visible ----------
    draw_retention_percent(ax_b, df, w0, panel="b")

    # (c) weight loss ---------------------------------------------------------
    ax_c.axhline(0.0, color="k", ls="--", lw=1.4)
    ax_c.errorbar(t, pos["dw_mV"], yerr=1e3 * pos["w_se"], fmt="D-", color=C_LOSS,
                  lw=LW_CURVE, ms=MARKERSIZE - 1, capsize=3, mfc="white", mew=1.6,
                  label=r"$\Delta w = w_{\mathrm{est}}(t) - w_{\mathrm{est}}(0)$")
    ax_c.set_ylabel(LBL_DW, fontweight="bold")
    log_time_axis(ax_c, t)
    style_ax(ax_c)
    panel_label(ax_c, "c")
    ax_c.legend(loc="lower left", frameon=True, framealpha=0.9)

    # (d) read-path diagnostics ----------------------------------------------
    ax_d.plot(t, pos["code_min"], "o-", color=C_CODE, lw=LW_CURVE,
              ms=MARKERSIZE - 1, mfc="white", mew=1.6, label=r"code$_{min}$")
    ax_d.set_ylabel(r"Notch floor (LSB)", color=C_CODE, fontweight="bold")
    ax_d.tick_params(axis="y", colors=C_CODE)
    log_time_axis(ax_d, t)
    style_ax(ax_d)
    panel_label(ax_d, "d")

    ax_d2 = ax_d.twinx()
    ax_d2.plot(t, pos["swing"], "^--", color=C_SWING, lw=LW_CURVE,
               ms=MARKERSIZE - 1, mfc="white", mew=1.6, label="swing")
    ax_d2.set_ylabel(LBL_SWING, color=C_SWING, fontweight="bold")
    ax_d2.tick_params(axis="y", colors=C_SWING)
    for label in ax_d2.get_yticklabels():
        label.set_fontweight("bold")
    ax_d2.grid(False)
    lines = ax_d.get_lines() + ax_d2.get_lines()
    ax_d.legend(lines, [ln.get_label() for ln in lines], loc="upper left",
                frameon=True, framealpha=0.9)

    fig.suptitle(title, fontsize=FONT_PANEL, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=DPI, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"[ok] wrote {out_path}")

    return {"w0": w0, "v0": v0, "fit_w": fit_w, "fit_r": fit_r}


# ---------------------------------------------------------------------------
# Figure 2: notch map used to convert v_notch -> w_est
# ---------------------------------------------------------------------------
def plot_map(response: pd.DataFrame, notch: pd.DataFrame, df: pd.DataFrame,
             out_path: Path, title: str) -> None:
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=FIG2_SIZE)

    levels = sorted(response["w_store"].dropna().unique())
    cmap = plt.get_cmap("viridis")
    for i, w in enumerate(levels):
        sub = response[response["w_store"] == w].sort_values("v")
        ax_a.plot(sub["v"], sub["code_avg"], "-", lw=1.8,
                  color=cmap(i / max(len(levels) - 1, 1)),
                  label=f"{w:+.2f} V" if i % 3 == 0 else None)
    ax_a.plot(notch["v_notch"], notch["code_extreme"], "kv", ms=7, mfc="white",
              mew=1.6, label="notch")
    ax_a.set_xlabel(LBL_V, fontweight="bold")
    ax_a.set_ylabel(LBL_CODE, fontweight="bold")
    style_ax(ax_a)
    panel_label(ax_a, "a")
    ax_a.legend(loc="upper right", ncol=2, fontsize=13, frameon=True,
                framealpha=0.9, title=r"$w_{store}$", title_fontsize=13)

    ax_b.plot(notch["w_store"], notch["v_notch"], "o-", color=C_MAIN,
              lw=LW_CURVE, ms=MARKERSIZE, mfc="white", mew=1.6,
              label="map (before retention)")
    zero = df[df["t_h"] == 0]
    last = df.iloc[-1]
    if len(zero):
        w_s, v_s = float(zero["w_est"].iloc[0]), float(zero["v_notch"].iloc[0])
        ax_b.plot(w_s, v_s, "*", color=C_CRIT, ms=18,
                  label=f"retention t = 0 ({w_s:.3f} V)")
        ax_b.annotate("", xy=(last["w_est"], last["v_notch"]), xytext=(w_s, v_s),
                      arrowprops=dict(arrowstyle="->", color=C_LOSS, lw=2.0))
    ax_b.plot(last["w_est"], last["v_notch"], "X", color=C_LOSS, ms=13,
              label=f"retention t = {last['t_label']} ({last['w_est']:.3f} V)")
    ax_b.set_xlabel(LBL_W, fontweight="bold")
    ax_b.set_ylabel(LBL_V0, fontweight="bold")
    style_ax(ax_b)
    panel_label(ax_b, "b")
    ax_b.legend(loc="upper left", fontsize=14, frameon=True, framealpha=0.9)

    fig.suptitle(title, fontsize=FONT_PANEL, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=DPI, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"[ok] wrote {out_path}")


# ---------------------------------------------------------------------------
# Console summary
# ---------------------------------------------------------------------------
def report(df: pd.DataFrame, res: dict) -> None:
    last = df.iloc[-1]
    print("\n--- 4T2C retention summary ---")
    print(f"checkpoints        : {len(df)} over {df['t_h'].max():.1f} h")
    print(f"w_est(0)           : {res['w0']:.4f} V  (v_notch = {res['v0']:.4f} V)")
    print(f"w_est({last['t_label']})".ljust(19)
          + f": {last['w_est']:.4f} V  ->  {last['retention_pct']:.2f} % "
            f"({last['dw_mV']:+.1f} mV)")
    fit_r = res["fit_r"]
    if fit_r is None:
        return
    print(f"log-linear fit     : {fit_r['b']:.2f} %/decade, "
          f"R^2 = {fit_r['r2']:.3f}, n = {fit_r['n_fit']}")
    knee = knee_time(df)
    if knee is not None:
        print(f"fast-decay onset   : ~{knee:.1f} h (loss rate > {KNEE_FACTOR:g}x the early-time rate)")
    t_max = float(df["t_h"].max())
    for crit in RETENTION_CRITERIA:
        below = df[df["retention_pct"] < crit]
        if len(below):
            i = int(below.index[0])
            meas = (f"crossed between {df.iloc[max(i - 1, 0)]['t_label']} "
                    f"and {df.iloc[i]['t_label']}")
        else:
            meas = f"not reached within {t_max:.0f} h"
        t_fit = solve_fit_time(fit_r, crit)
        # A single log10(t) slope does not describe a flat-then-knee decay, so the
        # crossing is quoted only where it stays close to the measured window.
        fit_s = (format_hours(t_fit) if np.isfinite(t_fit) and t_fit <= 10.0 * t_max
                 else "beyond the measured window (log-linear guide not valid)")
        print(f"  {crit:.0f} % criterion   : measured {meas}; fit -> {fit_s}")
    if fit_r["r2"] >= 0.8:
        print(f"  10 yr (log guide): {float(eval_fit(fit_r, T_10YR_H)):.1f} %")
    else:
        print(f"  10 yr extrapolation withheld (R^2 = {fit_r['r2']:.2f} < 0.8): "
              "the decay is flat then accelerating, not log-linear")
    print("note: code_min drifts monotonically while the swing stays flat -- panel (d) "
          "separates read-path drift from true weight loss.\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="Plot IGZO 4T2C retention results.")
    ap.add_argument("--data-dir", type=Path, default=None,
                    help=f"session directory (default: search, or ${DATA_DIR_ENV})")
    ap.add_argument("--outdir", type=Path, default=OUTDIR)
    ap.add_argument("--no-map", action="store_true",
                    help="skip the notch-map calibration figure")
    args = ap.parse_args(argv)

    data_dir = resolve_data_dir(args.data_dir)
    if data_dir is None:
        print("[error] retention session directory not found.", file=sys.stderr)
        if args.data_dir is not None:
            print(f"        --data-dir does not exist: {args.data_dir}", file=sys.stderr)
        else:
            print("        looked in:", file=sys.stderr)
            for cand in data_dir_candidates():
                print(f"          {cand}", file=sys.stderr)
            globs = data_dir_globs()
            for root, pattern in globs:
                print(f"          {root}/{pattern}", file=sys.stderr)
            if not globs:
                roots = drive_roots() or ["<none>"]
                print(f"          (no {ONEDRIVE_DIRNAME} folder under any of: "
                      f"{', '.join(str(r) for r in roots)})", file=sys.stderr)
        print(f'        pass it explicitly:  --data-dir "<path>"  '
              f"(or set ${DATA_DIR_ENV})", file=sys.stderr)
        return 1
    print(f"[dir ] {data_dir}")

    csv_path = find_one(data_dir, SUMMARY_GLOB, "summary")
    if csv_path is None:
        print(f"[error] no file matching {SUMMARY_GLOB} in {data_dir}", file=sys.stderr)
        return 1

    apply_plot_style()
    df = load_summary(csv_path)
    print(f"[in ] {csv_path.name}: {len(df)} checkpoints")

    res = plot_retention(df, args.outdir / f"{FIG1_STEM}.png",
                         "IGZO 4T2C retention (chip6, site 4t2c_a, 10 h @ RT)")
    plot_retention_percent(df, res["w0"], args.outdir / f"{FIG1B_STEM}.png")

    if not args.no_map:
        map_path = find_one(data_dir, MAP_GLOB, "map")
        if map_path is None:
            print(f"[warn] no {MAP_GLOB} found; skipping the calibration figure")
        elif importlib.util.find_spec("openpyxl") is None:
            # pandas.read_excel needs it; fail soft so figure 1 still counts.
            print("[warn] openpyxl is not installed; skipping the calibration figure "
                  "(pip install openpyxl)")
        else:
            print(f"[in ] {map_path.name}")
            response, notch = load_map(map_path)
            plot_map(response, notch, df, args.outdir / f"{FIG2_STEM}.png",
                     r"Notch map used for the $v_{notch}\rightarrow w_{est}$ conversion")

    report(df, res)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
