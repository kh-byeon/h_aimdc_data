# -*- coding: utf-8 -*-
"""Single-cell ADC SL?BL shift plots.

Saves the full BL0 overlay and a four-trace subset styled like
``plot_fefet_notch_shift.py`` Figure 1.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

FILE_PATH = Path(__file__).resolve().parent / "single_cell_adc_results.xlsx"
OUTDIR = Path(__file__).resolve().parent

# Four BL0 series (min, inner?, inner+, max), analogous to MAIN_PICKS
MAIN_BL0 = [-1.5, -0.5, 0.5, 1.5]
MAIN_PALETTE = [plt.cm.viridis(x) for x in (0.0, 0.35, 0.65, 0.95)]

DPI = 300
FIG_SIZE = (8, 6)
FONT_BASE = 18
FONT_AXIS = 18
LW_CURVE = 2.0
GRID_ALPHA = 0.5
MARKERSIZE = 5
N_FIT = 100


def apply_plot_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": FONT_BASE,
            "axes.labelsize": FONT_AXIS,
            "axes.titlesize": FONT_AXIS,
            "legend.fontsize": FONT_BASE,
            "xtick.labelsize": FONT_BASE,
            "ytick.labelsize": FONT_BASE,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def _style_ax(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(True)
    ax.spines["right"].set_visible(True)
    ax.tick_params(axis="both", which="major", width=1.5, length=6)
    ax.grid(True, which="major", alpha=GRID_ALPHA, linewidth=0.5)
    ax.set_axisbelow(True)

    def _bold(_event=None) -> None:
        for lab in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
            lab.set_fontweight("bold")

    ax.figure.canvas.mpl_connect("draw_event", _bold)
    _bold()


def _save(fig: plt.Figure, stem: str) -> None:
    png = OUTDIR / f"{stem}.png"
    fig.savefig(png, dpi=DPI, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"Figure saved -> {png}")


def load() -> pd.DataFrame:
    df = pd.read_excel(FILE_PATH)
    df["BL0"] = df["BL0"].round(1)
    df["SL1"] = df["SL1"].round(1)
    return df


def fit_quadratic(sub: pd.DataFrame) -> np.poly1d | None:
    if len(sub) < 3:
        return None
    coef = np.polyfit(sub["SL1"].to_numpy(float), sub["ADCVALUE"].to_numpy(float), deg=2)
    return np.poly1d(coef)


def normalize_series(sub: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Per-trace (y ? F) / (y_peak ? F) using the quadratic floor and peak."""
    sub = sub.sort_values("SL1")
    x = sub["SL1"].to_numpy(float)
    y = sub["ADCVALUE"].to_numpy(float)
    poly = fit_quadratic(sub)
    if poly is None:
        raise ValueError("need ?? 3 points to normalize a series")
    x_line = np.linspace(float(x.min()), float(x.max()), N_FIT)
    y_fit = poly(x_line)
    floor = float(np.min(y_fit))
    peak = float(np.max(y_fit))
    scale = peak - floor
    if scale <= 0:
        raise ValueError("y_peak ? F ?? 0")
    y_pts = (y - floor) / scale
    y_line = (y_fit - floor) / scale
    return x, y_pts, x_line, y_line


def plot_all(df: pd.DataFrame) -> None:
    """All BL0 series: scatter + quadratic fits, jet colorbar."""
    fig, ax = plt.subplots(figsize=(10, 6))
    norm = plt.Normalize(df["BL0"].min(), df["BL0"].max())
    cmap = plt.cm.jet
    for bl0 in np.sort(df["BL0"].unique()):
        sub = df[df["BL0"] == bl0]
        x, y_pts, x_line, y_line = normalize_series(sub)
        ax.scatter(
            x, y_pts, c=[bl0] * len(x), cmap=cmap, norm=norm,
            s=50, alpha=0.7, zorder=3,
        )
        ax.plot(x_line, y_line, color=cmap(norm(bl0)), lw=2, zorder=2)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax)
    cbar.set_label("BL Value", fontsize=14, fontweight="bold")
    ax.set_xlabel("SL", fontsize=14, fontweight="bold")
    ax.set_ylabel("Normalized ADC", fontsize=14, fontweight="bold")
    ax.tick_params(labelsize=12)
    for lab in ax.get_xticklabels() + ax.get_yticklabels():
        lab.set_fontweight("bold")
    ax.grid(True)
    fig.tight_layout()
    _save(fig, "shifted_fitting")


def plot_four(df: pd.DataFrame) -> None:
    """Four selected BL0 traces, styled like notch-shift Figure 1."""
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    for bl0, color in zip(MAIN_BL0, MAIN_PALETTE):
        sub = df[np.isclose(df["BL0"], bl0)]
        if sub.empty:
            raise ValueError(f"no rows for BL0 = {bl0}")
        x, y_pts, x_line, y_line = normalize_series(sub)
        ax.plot(
            x, y_pts,
            ls="none", marker="o", markersize=MARKERSIZE,
            color=color, markerfacecolor=color, markeredgewidth=0, zorder=3,
        )
        ax.plot(x_line, y_line, color=color, lw=LW_CURVE, zorder=2)

    ax.set_xlabel("SL", fontsize=FONT_AXIS, fontweight="bold")
    ax.set_ylabel("Normalized ADC", fontsize=FONT_AXIS, fontweight="bold")
    _style_ax(ax)
    y_top = max(1.0, ax.get_ylim()[1])
    ax.set_ylim(-0.06, y_top + 0.04)
    fig.tight_layout()
    _save(fig, "shifted_fitting_four")


def main() -> None:
    apply_plot_style()
    df = load()
    plot_all(df)
    plot_four(df)


if __name__ == "__main__":
    main()
