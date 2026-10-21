#!/usr/bin/env python3
"""
Publication-quality notch-shift figures from the FeFET chip3 campaign workbook.

    python plot_fefet_notch_shift.py

Reads ``FeFET_chip3_notch_campaign_20260829.xlsx``.

Notation is shared with the 4T2C notch scripts through ``notch_common``: v is the
differential read input, v0 the notch position, w the stored differential value.
On this device w is not programmed as a voltage -- it is the pair's threshold
difference, w = (Vth,A - Vth,B)/2, measured independently of the notch. Panel D
is therefore a check of the two against each other, and its slope of ~1 is the
statement that the notch reports the stored value one-for-one. (The 4T2C cells
read out through a capacitive divider instead, so there v0 = -w/alpha + b with
alpha ~ 0.62; the sign and the slope differ by construction, not by disagreement.)
Y-axis of Figure 1 is per-trace normalised current; Figure 2 Panel A stays in code/ms.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import openpyxl
import pandas as pd
from matplotlib import cm
from matplotlib.colors import Normalize, LinearSegmentedColormap

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_WORKBOOK_NAME = "FeFET_chip3_notch_campaign_20260829.xlsx"
_WORKBOOK_CANDIDATES = (
    Path(__file__).resolve().parent / _WORKBOOK_NAME,
    Path(r"D:\OneDrive\FeFET_meas_res") / _WORKBOOK_NAME,
)
OUTDIR = Path(__file__).resolve().parent / "figures"

MAIN_PICKS = [
    ("chip3_0829_0344", 4),   # lower corner, w = -0.6097 V, |L-R| = 0.001
    ("chip3_0828_2052", 7),   # inner negative,  w = -0.2696 V, |L-R| = 0.008
    ("chip3_0828_2052", 2),   # inner positive,  w = +0.2704 V, |L-R| = 0.016
    ("chip3_0829_1120", 2),   # upper corner,   w = +0.7009 V, |L-R| = 0.103
]
# MAIN_PALETTE (the colours of the four picks) is set in the blue palette
# block below, once the shared names it overrides have been imported.

RANGE_NR3_V = 1.3106
RANGE_NR3_1H_V = 1.1906
UPPER_RELAX_SLOPE_V_PER_DEC = -0.0524

FIT_WINDOW_V = 0.5          # |v − w| window used to refit curvature a
N_FIT = 400

FIG1_SIZE = (8, 6)
FIG2_SIZE = (12, 10)
FIG1_STEM = "fig1_main_three_notches"
FIG2_STEM = "fig2_supp_notches_and_analyses"
FIG2A_STEM = "fig2_panel_a_all_notches"
FIG2D_STEM = "fig2_panel_d_differential_law"
FIG2A_RAW_STEM = "fig2_panel_a_all_notches_raw"

# Style (aligned with plot_fefet_retention.py)
# Notation, palette and style come from notch_common, shared with the 4T2C notch
# scripts so that both device families produce one consistent figure set.
from notch_common import (            # noqa: E402
    DPI, LW_CURVE, GRID_ALPHA, MARKERSIZE,
    FONT_BASE as _SHARED_BASE,
    FONT_AXIS as _SHARED_AXIS,
    FONT_PANEL as _SHARED_PANEL,
    CMAP_NOTCH, C_REF, C_FIT, C_MAIN, C_ALT, C_OK, C_WARN,
    C_DOWN, C_UP, C_LOWER, C_UPPER,
    LBL_V, LBL_W, LBL_V0, LBL_CURRENT, LBL_CURRENT_NORM, MODEL_POWER,
    apply_plot_style, style_ax, panel_label, exponent_cfree,
    strip_text, BARE_SUFFIX,
)

# ---------------------------------------------------------------------------
# Blue palette (local override)
# ---------------------------------------------------------------------------
# Every colour in this figure set is a shade of blue: the colour key is a
# single-hue blue ramp and the categorical series are picked off the same ramp,
# spaced far enough apart in lightness that they stay separable in greyscale.
# The names imported from notch_common are rebound here only, so the other
# notch scripts keep the shared Okabe-Ito palette.
BLUE_RAMP = ["#F7FBFF", "#DEEBF7", "#C6DBEF", "#9ECAE1", "#6BAED6",
             "#4292C6", "#2171B5", "#08519C", "#08306B"]
CMAP_BLUE = LinearSegmentedColormap.from_list("notch_blue", BLUE_RAMP)
try:                                  # so plt.get_cmap("notch_blue") works too
    import matplotlib as _mpl
    _mpl.colormaps.register(CMAP_BLUE, name="notch_blue", force=True)
except (AttributeError, ValueError):  # older matplotlib, or already registered
    pass

# Pale ends of a single-hue ramp vanish on a white page, so the colour key runs
# over the usable middle-to-dark stretch instead of the full 0-1 range.
CMAP_NOTCH = LinearSegmentedColormap.from_list(
    "notch_blue_w", CMAP_BLUE(np.linspace(0.34, 1.0, 256)))

C_REF = "#12263F"       # very dark navy -- ideal / reference lines
C_FIT = "#5C7FA3"       # muted slate    -- fitted guides
C_MAIN = "#2171B5"      # strong blue    -- primary series
C_ALT = "#6BAED6"       # light blue     -- second series
C_OK = "#9ECAE1"        # pale blue      -- the good case
C_WARN = "#08306B"      # deep navy      -- the failure case

# Role aliases, rebound so they follow the blues above rather than the shared
# palette they were imported from.
C_DOWN = C_MAIN         # down sweeps
C_UP = C_ALT            # up sweeps
C_LOWER = "#08519C"     # lower corner
C_UPPER = "#74B3DE"     # upper corner

# The four main-text picks, dark to light along the same ramp.
MAIN_PALETTE = [CMAP_BLUE(x) for x in (1.0, 0.78, 0.58, 0.40)]


# ---------------------------------------------------------------------------
# Font sizes for this script only
# ---------------------------------------------------------------------------
# These start from the shared notch_common values, so the figure set matches by
# default. Change any of them here to tune this figure alone -- editing
# notch_common would move the 4T2C and IGZO scripts with it.
#
# The values below reproduce what this script rendered before they were split
# out, so nothing shifts until one is deliberately changed.
FONT_BASE = _SHARED_BASE            # base text size (rcParams font.size)
FONT_AXIS = _SHARED_AXIS          # axis and colourbar labels
FONT_PANEL = _SHARED_PANEL          # panel letters
FONT_TICK = FONT_BASE -4             # tick labels, main axes and colourbar
FONT_LEGEND = FONT_BASE             # legend entries
FONT_STAT = FONT_BASE               # fitted numbers called out on a panel
FONT_ANNOT = FONT_BASE - 6          # small notes, e.g. the exponent box
FONT_CBAR_LABEL = FONT_AXIS         # colourbar label
FONT_CBAR_TICK = FONT_TICK-2          # colourbar tick numbers
FONT_AXIS_LONG = FONT_AXIS - 4      # axis label too long to sit at FONT_AXIS
FONT_NOTE = FONT_BASE - 4           # notes written inside panels B and C

NR2_RUN = "chip3_0828_2052"
NR3_RUNS = ("chip3_0829_0344", "chip3_0829_1120")



CORNER_LABEL = {
    "아래 코너": "lower corner",
    "위 코너": "upper corner",
    "lower corner": "lower corner",
    "upper corner": "upper corner",
}

TRAVERSE_DROP_RUN = {"run", "주", "행 수", "nan", "None", ""}


# ---------------------------------------------------------------------------
# Style (matched to plot_fefet_retention.py)
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
            "legend.fontsize": FONT_LEGEND,
            "xtick.labelsize": FONT_TICK,
            "ytick.labelsize": FONT_TICK,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "mathtext.default": "regular",
            "mathtext.fontset": "custom",
            "mathtext.rm": "Arial",
            "mathtext.it": "Arial:italic",
            "mathtext.bf": "Arial:bold",
        }
    )


def _style_ax(ax: plt.Axes) -> None:
    """Shared publication style (spines, ticks, bold labels, grid)."""
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


def _panel_label(ax: plt.Axes, letter: str) -> None:
    ax.text(
        0.02, 0.98, letter, transform=ax.transAxes,
        ha="left", va="top", fontsize=FONT_PANEL, fontweight="bold",
    )


def _write(fig: plt.Figure, png: Path) -> None:
    """Write one PNG, falling back to a "_new" name if the file is locked."""
    try:
        fig.savefig(png, dpi=DPI, facecolor="white", bbox_inches="tight")
    except OSError:
        alt = png.with_name(png.stem + "_new" + png.suffix)
        fig.savefig(alt, dpi=DPI, facecolor="white", bbox_inches="tight")
        print(f"could not overwrite {png.name} (file open?); wrote {alt.name}")


def _save(fig: plt.Figure, stem: str) -> None:
    """Write the figure, then a text-free copy beside it.

    Same arrangement as plot_4t2c_notch_campaign.py, sharing strip_text through
    notch_common: the bare copy keeps only the numeric tick labels, so it drops
    into a layout that supplies its own titles, keys and annotations. Both come
    off one figure object and cannot disagree.
    """
    OUTDIR.mkdir(parents=True, exist_ok=True)
    _write(fig, OUTDIR / f"{stem}.png")
    strip_text(fig)
    _write(fig, OUTDIR / f"{stem}{BARE_SUFFIX}.png")
    plt.close(fig)


def parabola(v, w, F, a):
    """Quadratic notch model: a * (v - w)**2 + F."""
    v = np.asarray(v, float)
    return a * (v - w) ** 2 + F


# ---------------------------------------------------------------------------
# Fits
# ---------------------------------------------------------------------------
def _lin_fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    """y = slope * x + intercept. Returns (slope, intercept, R^2)."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    slope, intercept = np.polyfit(x, y, 1)
    yhat = slope * x + intercept
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
    return float(slope), float(intercept), r2


def _log_fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    """y = slope * log10(x) + intercept. Returns (slope, intercept, R^2)."""
    return _lin_fit(np.log10(np.asarray(x, float)), y)


def _origin_fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """y = k x through the origin. Returns (k, R^2 vs mean)."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    k = float(np.dot(x, y) / np.dot(x, x))
    yhat = k * x
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
    return k, r2


def refit_parabola(v: np.ndarray, I: np.ndarray, w: float,
                   window: float = FIT_WINDOW_V) -> tuple[float, float]:
    """Refit I = a·(v − w)² + F on |v − w| ≤ window. Returns (a, F).

    Does not reuse a stored floor or curvature — both are determined by the points.
    """
    v = np.asarray(v, float)
    I = np.asarray(I, float)
    mask = np.abs(v - w) <= window
    if mask.sum() < 3:
        raise ValueError(f"fewer than 3 points in |v-w|≤{window} V around w={w}")
    x = (v[mask] - w) ** 2
    y = I[mask]
    design = np.column_stack([x, np.ones_like(x)])
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    a, F = float(coef[0]), float(coef[1])
    if a <= 0:
        raise ValueError(f"non-positive curvature a={a} at w={w}")
    return a, F


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def run_tag(run: str) -> str:
    s = str(run).strip()
    if s == NR2_RUN or "0828_2052" in s or s.endswith("0828_2052"):
        return "nr2"
    if s in NR3_RUNS or "0829_0344" in s or "0829_1120" in s:
        return "nr3"
    raise ValueError(f"unknown run id {run!r}")


def _strip_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _drop_note_rows(df: pd.DataFrame, col: str = "run") -> pd.DataFrame:
    s = df[col]
    keep = s.notna() & ~s.astype(str).str.strip().isin(TRAVERSE_DROP_RUN)
    return df.loc[keep].copy()


def _read_sheet(path: Path, sheet: str, headers: tuple[int, ...]) -> pd.DataFrame:
    """Try header rows until a 'run' (or 'corner') column appears.

    Campaign sheets have a Korean title, then often a blank row, then the header.
    """
    last = None
    for h in headers:
        df = _strip_cols(pd.read_excel(path, sheet_name=sheet, header=h, engine="openpyxl"))
        last = df
        cols = {c.lower() for c in df.columns}
        if "run" in cols or "corner" in cols:
            return df
    return last if last is not None else pd.DataFrame()


def resolve_workbook() -> Path:
    for p in _WORKBOOK_CANDIDATES:
        if p.is_file():
            return p
    tried = "\n  ".join(str(p) for p in _WORKBOOK_CANDIDATES)
    raise FileNotFoundError(f"{_WORKBOOK_NAME} not found. Tried:\n  {tried}")


def load_traverse(path: Path) -> pd.DataFrame:
    # Prompt says header=1; the file has a blank row so the real header is row 3.
    tr = _read_sheet(path, "traverse", (1, 2))
    tr = _drop_note_rows(tr, "run")
    tr["run"] = tr["run"].astype(str).str.strip()
    tr["step"] = tr["step"].astype(int)
    tr["tag"] = tr["run"].map(run_tag)
    if len(tr) != 25:
        raise ValueError(f"traverse: expected 25 rows, got {len(tr)}")
    return tr.reset_index(drop=True)


def load_dose_law(path: Path) -> pd.DataFrame:
    d = _read_sheet(path, "dose_law", (2, 1))
    d = _drop_note_rows(d, "run")
    d = d[pd.to_numeric(d["log10_dose"], errors="coerce").notna()].copy()
    d["run"] = d["run"].astype(str).str.strip()
    d["direction"] = d["direction"].astype(str).str.strip().str.lower()
    d["tag"] = d["run"].map(run_tag)
    return d.reset_index(drop=True)


def load_relaxation(path: Path) -> pd.DataFrame:
    r = _read_sheet(path, "relaxation", (2, 1))
    r["corner"] = r["corner"].astype(str).str.strip()
    r = r[pd.to_numeric(r["t_min"], errors="coerce").notna()].copy()
    r["run"] = r["run"].astype(str).str.strip()
    r["corner_en"] = r["corner"].map(lambda c: CORNER_LABEL.get(c, c))
    return r.reset_index(drop=True)


def _meta_row_index(labels: list[object], *names: str) -> int:
    wanted = {n.lower() for n in names}
    for i, lab in enumerate(labels):
        if lab is None:
            continue
        key = str(lab).strip().lower()
        if key in wanted:
            return i
    raise KeyError(f"notch_curves: no metadata row matching {names}")


def load_notch_curves(path: Path | str) -> list[dict]:
    """25 side-by-side traces. Trace k occupies openpyxl columns (2k, 2k+1)."""
    path = Path(path)
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb["notch_curves"]
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
    finally:
        wb.close()
    if not rows:
        raise ValueError("notch_curves is empty")

    col0 = [row[0] if row else None for row in rows]
    n_cols = max(len(row) for row in rows)
    i_run = _meta_row_index(col0, "run")
    i_step = _meta_row_index(col0, "step")
    i_phase = _meta_row_index(col0, "phase")
    i_kind = _meta_row_index(col0, "kind")
    i_w = _meta_row_index(col0, "w [v]", "w", "notch_v")
    i_dose = _meta_row_index(col0, "dir_dose [s]", "dir_dose")
    i_floor = _meta_row_index(col0, "floor [code/ms]", "floor")

    i_header = None
    for i, lab in enumerate(col0):
        cell = "" if lab is None else str(lab).strip().lower()
        # header row may label column 1, or only the per-trace v/I headers
        if cell in {"v [v]", "v", "v (v)"}:
            i_header = i
            break
    if i_header is None:
        # fall back to the first row that looks like "v [V]" in a data column
        for i, row in enumerate(rows):
            for cell in row[1:4]:
                if cell is None:
                    continue
                if str(cell).strip().lower() in {"v [v]", "v"}:
                    i_header = i
                    break
            if i_header is not None:
                break
    if i_header is None:
        i_header = 9  # row 10, 0-indexed
    i_data = i_header + 1

    traces: list[dict] = []
    for k in range(1, 26):
        v_col = 2 * k - 1  # 0-indexed; openpyxl column 2k
        i_col = 2 * k      # openpyxl column 2k+1
        if i_col >= n_cols:
            break

        def cell(ri: int, ci: int):
            row = rows[ri] if ri < len(rows) else []
            return row[ci] if ci < len(row) else None

        run = cell(i_run, v_col)
        if run is None or (isinstance(run, str) and not str(run).strip()):
            continue
        v_pts, i_pts = [], []
        for ri in range(i_data, len(rows)):
            vv = cell(ri, v_col)
            if vv is None or (isinstance(vv, float) and np.isnan(vv)):
                break
            ii = cell(ri, i_col)
            if ii is None or (isinstance(ii, float) and np.isnan(ii)):
                break
            v_pts.append(float(vv))
            i_pts.append(float(ii))
        traces.append({
            "run": str(run).strip(),
            "step": int(cell(i_step, v_col)),
            "phase": None if cell(i_phase, v_col) is None else str(cell(i_phase, v_col)).strip(),
            "kind": None if cell(i_kind, v_col) is None else str(cell(i_kind, v_col)).strip(),
            "w": float(cell(i_w, v_col)),
            "dir_dose_s": float(cell(i_dose, v_col)),
            "floor_per_ms": float(cell(i_floor, v_col)),
            "v": np.asarray(v_pts, float),
            "I": np.asarray(i_pts, float),
        })

    if len(traces) != 25:
        raise ValueError(f"notch_curves: expected 25 traces, got {len(traces)}")
    return traces


def load(path: Path) -> tuple[pd.DataFrame, list[dict], pd.DataFrame, pd.DataFrame]:
    traverse = load_traverse(path)
    curves = load_notch_curves(path)
    dose = load_dose_law(path)
    relax = load_relaxation(path)
    return traverse, curves, dose, relax


def pick_main_traces(curves: list[dict]) -> tuple[tuple[str, int], tuple[str, int], tuple[str, int]]:
    w = np.array([t["w"] for t in curves], float)
    i_a = int(np.argmin(w))
    i_b = int(np.argmax(w))
    mid = 0.5 * (w[i_a] + w[i_b])
    i_c = int(np.argmin(np.abs(w - mid)))
    out = []
    for i in (i_a, i_b, i_c):
        out.append((curves[i]["run"], int(curves[i]["step"])))
    return tuple(out)  # type: ignore[return-value]


def find_trace(curves: list[dict], run: str, step: int) -> dict:
    hits = [t for t in curves if t["run"] == run and int(t["step"]) == int(step)]
    if len(hits) != 1:
        raise KeyError(f"trace (run={run!r}, step={step}) count={len(hits)}")
    return hits[0]


# ---------------------------------------------------------------------------
# Figure 1
# ---------------------------------------------------------------------------
def plot_fig1(curves: list[dict], picks: tuple[tuple[str, int], ...]) -> None:
    fig, ax = plt.subplots(figsize=FIG1_SIZE)

    fitted = []
    for pick, color in zip(picks, MAIN_PALETTE):
        tr = find_trace(curves, pick[0], pick[1])
        v, I = tr["v"], tr["I"]
        w = float(tr["w"])
        a, F = refit_parabola(v, I, w)
        v_line = np.linspace(
            max(float(v.min()), -1.0),
            min(float(v.max()), 1.0),
            N_FIT,
        )
        I_fit = parabola(v_line, w, F, a)
        I_peak = float(np.max(I_fit))
        scale = I_peak - F
        if scale <= 0:
            raise ValueError(f"I_peak − F ≤ 0 for w={w}")
        I_pts = (I - F) / scale
        I_line = (I_fit - F) / scale
        fitted.append((w, color))
        ax.plot(
            v, I_pts,
            ls="none", marker="o", markersize=MARKERSIZE,
            color=color, markerfacecolor=color, markeredgewidth=0, zorder=3,
        )
        ax.plot(v_line, I_line, color=color, lw=LW_CURVE, zorder=2)

    ax.set_xlabel("", fontsize=FONT_AXIS, fontweight="bold")
    ax.set_ylabel(
        "",
        fontsize=FONT_AXIS, fontweight="bold",
    )
    _style_ax(ax)
    ax.set_xlim(-1.0, 1.0)
    ax.set_xticks(np.arange(-1.0, 1.01, 0.5))
    ax.tick_params(axis="x", which="minor", length=0)

    y_top = max(1.0, ax.get_ylim()[1])
    ax.set_ylim(-0.06, y_top + 0.04)
    y0, _y1 = ax.get_ylim()
    for w, color in fitted:
        ax.plot([w, w], [y0, 0.0], ls=(0, (3, 1.8)), lw=1.2, color=color, zorder=1)
        ax.plot(w, 0.0, marker="|", markersize=8, color=color, zorder=4)

    fig.tight_layout()
    _save(fig, FIG1_STEM)


# ---------------------------------------------------------------------------
# Figure 2
# ---------------------------------------------------------------------------
SWING_Z_MAX = 3.5           # robust z above which a trace is treated as an outlier

# Minimum separation between the notches drawn on the all-notch panel. The
# traverse revisited nearly the same stored value several times -- four pairs sit
# within 1 to 7 mV of each other -- and those curves land on top of one another.
# The gaps then jump straight to 25 mV, so 20 mV cuts exactly the degenerate
# pairs and keeps every distinct stored value. Set to 0 to draw all of them.
MIN_NOTCH_SEP_V = 0.020

# The all-notch panels are written twice: the default render lets the data set
# the vertical axis, and the "_fixed" render ends the normalised current at
# exactly 1 for placing beside another panel. Same data either way.
FIXED_SUFFIX = "_fixed"


def drop_swing_outliers(curves: list[dict], z_max: float = SWING_Z_MAX):
    """Split traces on the size of their excursion above the floor.

    One trace of this campaign swings more than twice as far as any other, which
    on a shared axis compresses the remaining 24 into the lower third of the
    plot. The cut is on a median/MAD z-score rather than a fixed threshold, so it
    adapts to the run and flags nothing when every trace is comparable.

    Returns (kept, dropped); dropped carries a "swing_z" key for reporting.
    """
    if len(curves) < 4:
        return list(curves), []
    swing = np.array([float(t["I"].max() - t["I"].min()) for t in curves])
    med = float(np.median(swing))
    mad = float(np.median(np.abs(swing - med)))
    if mad <= 0:
        return list(curves), []
    z = 0.6745 * (swing - med) / mad
    kept, dropped = [], []
    for t, zz in zip(curves, z):
        if abs(zz) > z_max:
            t = dict(t, swing_z=float(zz))
            dropped.append(t)
        else:
            kept.append(t)
    return kept, dropped


def thin_by_notch_spacing(curves: list[dict], min_sep: float = MIN_NOTCH_SEP_V):
    """Drop traces whose notch sits on top of one already kept.

    Up and down passes are pooled first, so a value revisited from either
    direction counts as the same point. Walking in ascending w and keeping the
    first of each cluster is arbitrary but deterministic; the dropped curves are
    duplicates of a kept one to within a few mV, so which of the pair survives
    does not change what the panel shows.

    Returns (kept, dropped); each dropped trace carries ``near_w``, the notch it
    collided with.
    """
    if not min_sep or min_sep <= 0:
        return list(curves), []
    kept, dropped, last = [], [], None
    for t in sorted(curves, key=lambda t: float(t["w"])):
        w = float(t["w"])
        if last is not None and w - last < min_sep:
            dropped.append(dict(t, near_w=last))
            continue
        kept.append(t)
        last = w
    return kept, dropped


def _draw_all_notches(
    ax: plt.Axes,
    fig: plt.Figure,
    curves: list[dict],
    *,
    letter: str | None = "A",
    normalise: bool = True,
    fixed_window: bool = False,
) -> None:
    n_all = len(curves)
    curves, dropped = drop_swing_outliers(curves)
    for t in dropped:
        print(f"[skip] {t['run']} step {t['step']} (w = {t['w']:+.3f} V): swing "
              f"{t['I'].max() - t['I'].min():.0f} code/ms, robust z = "
              f"{t['swing_z']:+.1f} -- excluded from the all-notch panel")
    curves, crowded = thin_by_notch_spacing(curves)
    for t in crowded:
        print(f"[skip] {t['run']} step {t['step']} (w = {t['w']:+.3f} V): within "
              f"{1e3 * (float(t['w']) - t['near_w']):.0f} mV of w = "
              f"{t['near_w']:+.3f} V -- would overplot it")
    if crowded:
        print(f"[note] all-notch panel: {len(curves)} of {n_all} traces drawn "
              f"(min notch separation {1e3 * MIN_NOTCH_SEP_V:.0f} mV)")
    ws = np.array([t["w"] for t in curves], float)
    norm = Normalize(vmin=float(ws.min()), vmax=float(ws.max()))
    cmap = plt.get_cmap(CMAP_NOTCH)
    order = np.argsort(ws)
    for t in (curves[i] for i in order):
        if normalise:
            # Each trace scaled onto 0..1 between its own floor and its own peak.
            # The floors sit within 131-153 code/ms and the kept swings within
            # 43-69, so this mostly removes the floor offset rather than
            # reshaping anything.
            lo = float(t["I"].min())
            span = float(t["I"].max()) - lo
            if span <= 0:
                continue
            y = (t["I"] - lo) / span
        else:
            y = t["I"]
        ax.plot(
            t["v"], y,
            color=cmap(norm(float(t["w"]))),
            lw=1.5, alpha=0.75, solid_capstyle="round",
        )
    # Shape of the notch, reported the way plot_4t2c_notch_campaign.py does it:
    # the C-free symmetrised exponent, which needs neither the floor nor the
    # amplitude and so is not biased by the narrow window the way a log-log fit
    # is. Its per-curve scatter is what makes it an ensemble statistic.
    ps = np.array([exponent_cfree(t["v"], t["I"], float(t["w"]))
                   for t in curves], float)
    ps = ps[np.isfinite(ps)]
    if ps.size:
        p_mean = float(ps.mean())
        p_sem = float(ps.std(ddof=1) / np.sqrt(ps.size)) if ps.size > 1 else float("nan")
        # Inside the headroom on the default render; above the frame on the
        # cropped one, where the curve peaks reach the top edge.
        ax.text(0.5, 1.02 if fixed_window else 0.975,
                MODEL_POWER.replace("code", "I") + ",   "
                + rf"$p$ = {p_mean:.2f} $\pm$ {p_sem:.2f}"
                + f"  ($n$ = {ps.size}, C-free)",
                transform=ax.transAxes, ha="center",
                va="bottom" if fixed_window else "top",
                fontsize=FONT_ANNOT, fontweight="bold", color=C_REF,
                bbox=dict(boxstyle="round,pad=0.32", facecolor="white",
                          edgecolor=C_REF, alpha=0.92, linewidth=0.9))
        # Curvature too, but only to the console: the sheet's curv_per_ms is the
        # quadratic coefficient a of I = a(v-v0)^2 + F, while the 4T2C scripts
        # write kappa for d2I/dv2 = 2a. Printing both keeps the factor of two
        # from turning into a silent disagreement between the two figure sets.
        a_fit = []
        for t in curves:
            try:
                a_fit.append(refit_parabola(t["v"], t["I"], float(t["w"]))[0])
            except ValueError:
                continue
        print(f"[note] all-notch panel: exponent p = {p_mean:.3f} +- "
              f"{p_sem:.3f} (SEM), per-curve SD {ps.std(ddof=1):.3f}, range "
              f"{ps.min():.2f}-{ps.max():.2f}, n = {ps.size}")
        if a_fit:
            a_fit = np.asarray(a_fit, float)
            print(f"[note] curvature a = {a_fit.mean():.1f} code/ms/V^2 "
                  f"(CV {100 * a_fit.std(ddof=1) / a_fit.mean():.1f} %); "
                  f"as d2I/dv2 that is kappa = {2 * a_fit.mean():.1f}, which is "
                  "the convention the 4T2C scripts print")
    ax.set_xlabel(LBL_V, fontsize=FONT_AXIS, fontweight="bold")
    if normalise:
        ax.set_ylabel(LBL_CURRENT_NORM, fontsize=FONT_AXIS,
                      fontweight="bold")
        # Exactly 0 to 1 on the cropped render: the floor is 0 and the peak is
        # 1 by construction, so the frame is the normalisation itself.
        ax.set_ylim(0.0 if fixed_window else -0.05,
                    1.0 if fixed_window else 1.18)
    else:
        ax.set_ylabel(LBL_CURRENT, fontsize=FONT_AXIS,
                      fontweight="bold")
        if not fixed_window:
            ylo, yhi = ax.get_ylim()
            ax.set_ylim(ylo, yhi + 0.16 * (yhi - ylo))
    _style_ax(ax)
    if letter is not None:
        _panel_label(ax, letter)
    sm = cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, pad=0.02, fraction=0.046)
    cbar.set_label(LBL_V0, fontsize=FONT_CBAR_LABEL, fontweight="bold")
    cbar.ax.tick_params(labelsize=FONT_CBAR_TICK, width=1.5, length=6)
    for lab in cbar.ax.get_yticklabels():
        lab.set_fontweight("bold")
    cbar.outline.set_linewidth(1.0)


def plot_fig2_a(curves: list[dict]) -> None:
    for fixed in (False, True):
        fig, ax = plt.subplots(figsize=FIG1_SIZE)
        _draw_all_notches(ax, fig, curves, letter=None, fixed_window=fixed)
        fig.tight_layout()
        _save(fig, FIG2A_STEM + (FIXED_SUFFIX if fixed else ""))


def _draw_diff_law(
    ax: plt.Axes, traverse: pd.DataFrame, *, letter: str | None = "D",
) -> dict:
    for direction, color, marker in (("down", C_DOWN, "o"), ("up", C_UP, "s")):
        sub = traverse.loc[traverse["direction"].astype(str).str.lower() == direction]
        ax.scatter(
            sub["differential"], sub["notch_v"],
            s=50, color=color, marker=marker, edgecolors="none",
            zorder=3, label=direction,
        )
    x = traverse["differential"].to_numpy(float)
    y = traverse["notch_v"].to_numpy(float)
    k, r2_origin = _origin_fit(x, y)
    m_free, b_free, r2_free = _lin_fit(x, y)
    pad = 0.05 * (float(x.max()) - float(x.min()) or 1.0)
    span = np.array([float(x.min()) - pad, float(x.max()) + pad])
    ax.plot(span, k * span, color=C_REF, lw=LW_CURVE, zorder=2)
    ax.plot(span, span, color="#8FA9C2", ls=(0, (3, 2)), lw=1.2, zorder=1)
    ax.text(
        0.05, 0.95,
        f"slope = {k:.3f}\nR² = {r2_origin:.4f}",
        transform=ax.transAxes, ha="left", va="top",
        fontsize=FONT_STAT, fontweight="bold",
    )
    # The longest label on the panel; it overruns the axis at FONT_AXIS.
    ax.set_xlabel(LBL_W, fontsize=FONT_AXIS_LONG, fontweight="bold")
    ax.set_ylabel(LBL_V0, fontsize=FONT_AXIS, fontweight="bold")
    _style_ax(ax)
    if letter is not None:
        _panel_label(ax, letter)
    leg = ax.legend(
        loc="lower right", framealpha=0.92, handletextpad=0.3, borderaxespad=0.2,
        prop={"size": FONT_BASE, "weight": "bold"},
    )
    return {
        "diff_origin": (k, r2_origin),
        "diff_free": (m_free, b_free, r2_free),
    }


def plot_fig2_a_raw(curves: list[dict]) -> None:
    """Panel A standalone on the measured current axis, not normalised."""
    for fixed in (False, True):
        fig, ax = plt.subplots(figsize=FIG1_SIZE)
        _draw_all_notches(ax, fig, curves, letter=None, normalise=False,
                          fixed_window=fixed)
        fig.tight_layout()
        _save(fig, FIG2A_RAW_STEM + (FIXED_SUFFIX if fixed else ""))


def plot_fig2_d(traverse: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=FIG1_SIZE)
    _draw_diff_law(ax, traverse, letter=None)
    fig.tight_layout()
    _save(fig, FIG2D_STEM)



def plot_fig2(
    traverse: pd.DataFrame,
    curves: list[dict],
    dose: pd.DataFrame,
    relax: pd.DataFrame,
) -> dict:
    stats: dict = {}
    fig, axes = plt.subplots(2, 2, figsize=FIG2_SIZE)
    axA, axB, axC, axD = axes.ravel()

    # -- A: all 25 curves, colour by w --------------------------------------
    _draw_all_notches(axA, fig, curves, letter="A")

    # -- B: dose law, split by (run family, direction) ----------------------
    series_spec = (
        ("nr2", "down", "o", C_DOWN, "nr2 down"),
        ("nr2", "up", "o", C_UP, "nr2 up"),
        ("nr3", "down", "s", C_DOWN, "nr3 down"),
        ("nr3", "up", "s", C_UP, "nr3 up"),
    )
    for tag, direction, marker, color, label in series_spec:
        sub = dose.loc[(dose["tag"] == tag) & (dose["direction"] == direction)].sort_values("log10_dose")
        if sub.empty:
            continue
        axB.plot(
            sub["log10_dose"], sub["notch_v"],
            color=color, lw=LW_CURVE, zorder=2,
        )
        axB.scatter(
            sub["log10_dose"], sub["notch_v"],
            s=50, color=color, marker=marker, edgecolors="none",
            zorder=3, label=label,
        )

    nr2_up = dose.loc[(dose["tag"] == "nr2") & (dose["direction"] == "up")].sort_values("log10_dose")
    slope_b, intercept_b, r2_b = _lin_fit(
        nr2_up["log10_dose"].to_numpy(float), nr2_up["notch_v"].to_numpy(float),
    )
    stats["nr2_up_dose"] = (slope_b, intercept_b, r2_b)
    xs = np.linspace(float(nr2_up["log10_dose"].min()), float(nr2_up["log10_dose"].max()), 50)
    axB.plot(xs, slope_b * xs + intercept_b, color=C_UP, lw=LW_CURVE, zorder=2)
    axB.text(
        0.04, 0.96,
        f"nr2 up: dw/dlog10(dose) = {slope_b:+.3f} V/dec",
        transform=axB.transAxes, ha="left", va="top", fontsize=FONT_NOTE,
        fontweight="bold",
    )

    nr3_up = dose.loc[(dose["tag"] == "nr3") & (dose["direction"] == "up")].sort_values("log10_dose")
    if not nr3_up.empty:
        dabs = nr3_up["abs_d_notch_mV"].to_numpy(float) if "abs_d_notch_mV" in nr3_up.columns else np.abs(nr3_up["d_notch_mV"].to_numpy(float))
        i_sat = int(np.argmin(np.abs(dabs - 1.4)))
        sat = nr3_up.iloc[i_sat]
        axB.annotate(
            "saturation",
            xy=(float(sat["log10_dose"]), float(sat["notch_v"])),
            xytext=(8, 10),
            textcoords="offset points",
            arrowprops=dict(arrowstyle="->", lw=0.7, color="0.2"),
            fontsize=FONT_NOTE, color="0.2", fontweight="bold",
        )

    axB.set_xlabel("log10 (directional dose  [s])", fontsize=FONT_AXIS, fontweight="bold")
    axB.set_ylabel(LBL_V0, fontsize=FONT_AXIS, fontweight="bold")
    _style_ax(axB)
    _panel_label(axB, "B")
    axB.legend(loc="lower right", framealpha=0.92, handletextpad=0.3, borderaxespad=0.2, markerscale=0.9)

    # -- C: corner relaxation -----------------------------------------------
    axC.axhline(0.0, color="0.7", linewidth=0.9, linestyle="--", zorder=1)
    for corner_en, color, marker in (
        ("lower corner", C_LOWER, "o"),
        ("upper corner", C_UPPER, "s"),
    ):
        sub = relax.loc[relax["corner_en"] == corner_en].sort_values("t_min")
        if sub.empty:
            continue
        axC.plot(sub["t_min"], sub["delta_mV"], color=color, lw=LW_CURVE, zorder=2)
        axC.scatter(
            sub["t_min"], sub["delta_mV"],
            s=50, color=color, marker=marker, edgecolors="none",
            zorder=3, label=corner_en,
        )

    upper = relax.loc[
        (relax["corner_en"] == "upper corner") & (relax["t_min"] >= 0.5)
    ]
    slope_c, intercept_c, r2_c = _log_fit(
        upper["t_min"].to_numpy(float), upper["delta_mV"].to_numpy(float),
    )
    stats["upper_relax"] = (slope_c, intercept_c, r2_c)
    t_line = np.logspace(np.log10(float(upper["t_min"].min())), np.log10(float(upper["t_min"].max())), 50)
    axC.plot(t_line, slope_c * np.log10(t_line) + intercept_c, color=C_UPPER, lw=LW_CURVE, zorder=2)
    axC.text(
        0.04, 0.12,
        f"upper: {slope_c:+.1f} mV/dec",
        transform=axC.transAxes, ha="left", va="bottom", fontsize=FONT_NOTE,
        fontweight="bold",
    )
    axC.set_xscale("log")
    axC.set_xlabel("hold time  t  (min)", fontsize=FONT_AXIS, fontweight="bold")
    axC.set_ylabel(r"$\Delta v_0$  (mV)", fontsize=FONT_AXIS, fontweight="bold")
    _style_ax(axC)
    _panel_label(axC, "C")
    axC.legend(loc="best", framealpha=0.92, handletextpad=0.3, borderaxespad=0.2)

    # -- D: differential law ------------------------------------------------
    stats.update(_draw_diff_law(axD, traverse, letter="D"))

    fig.tight_layout()
    _save(fig, FIG2_STEM)
    return stats


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def print_summary(
    traverse: pd.DataFrame,
    picks: tuple[tuple[str, int], ...],
    stats: dict,
) -> None:
    marked = {(r, int(s)) for r, s in picks}
    cols = [
        "run", "step", "phase", "direction", "dir_dose_s",
        "notch_v", "floor_per_ms", "curv_per_ms",
    ]
    print()
    hdr = (
        f"{'':1} {'run':<22} {'step':>4}  {'phase':<14} {'dir':<5} "
        f"{'dose_s':>8} {'w':>8} {'floor':>10} {'curv':>10}"
    )
    print(hdr)
    print("-" * len(hdr))
    for _, row in traverse.sort_values("notch_v").iterrows():
        star = "*" if (row["run"], int(row["step"])) in marked else " "
        print(
            f"{star} {str(row['run']):<22} {int(row['step']):4d}  "
            f"{str(row['phase']):<14} {str(row['direction']):<5} "
            f"{float(row['dir_dose_s']):8.1f} {float(row['notch_v']):+8.4f} "
            f"{float(row['floor_per_ms']):10.4f} {float(row['curv_per_ms']):10.4f}"
        )
    print("-" * len(hdr))
    print("* = Figure 1  MAIN_PICKS =", picks)
    print()
    sl, ic, r2 = stats["nr2_up_dose"]
    print(f"nr2/up dose law:  w = {sl:.3f}·log10(dose) {ic:+.3f}   R^2 = {r2:.3f}")
    slc, _ic, r2c = stats["upper_relax"]
    print(
        f"upper-corner relaxation:  {slc:+.2f} mV/dec  "
        f"({slc/1000:+.4f} V/dec, sheet quote {UPPER_RELAX_SLOPE_V_PER_DEC:+.4f} V/dec)  "
        f"R^2 = {r2c:.3f}"
    )
    k, r2o = stats["diff_origin"]
    m, b, r2f = stats["diff_free"]
    print(f"differential law through origin:  k = {k:.3f},  R^2 = {r2o:.4f}")
    print(f"differential law free intercept:  m = {m:.3f},  b = {b:+.4f},  R^2 = {r2f:.4f}")
    print(f"nr3 range (instantaneous) = {RANGE_NR3_V:.4f} V;  after 1 h = {RANGE_NR3_1H_V:.4f} V")
    print(f"each figure also has a {BARE_SUFFIX} copy with the text removed; "
          f"the all-notch panels also have a {FIXED_SUFFIX} copy cropped to a "
          "normalised current of 1")
    print(f"wrote {OUTDIR / (FIG1_STEM + '.png')}")
    print(f"wrote {OUTDIR / (FIG2_STEM + '.png')}")
    print(f"wrote {OUTDIR / (FIG2A_STEM + '.png')}")
    print(f"wrote {OUTDIR / (FIG2A_RAW_STEM + '.png')}")
    print(f"wrote {OUTDIR / (FIG2D_STEM + '.png')}")


def main() -> None:
    apply_plot_style()
    workbook = resolve_workbook()
    print(f"workbook = {workbook}")
    traverse, curves, dose, relax = load(workbook)
    auto = pick_main_traces(curves)
    picks = MAIN_PICKS if MAIN_PICKS is not None else auto
    if MAIN_PICKS is not None and tuple(MAIN_PICKS) != auto:
        print(f"MAIN_PICKS override {MAIN_PICKS}  (auto would be {auto})")
    else:
        wa, wb, wc = (find_trace(curves, *p)["w"] for p in picks)
        print(f"MAIN_PICKS = {picks}")
        print(f"  w = {wa:+.4f}, {wb:+.4f}, {wc:+.4f} V  (auto: min, max, midpoint)")
    plot_fig1(curves, picks)
    plot_fig2_a(curves)
    plot_fig2_a_raw(curves)
    plot_fig2_d(traverse)
    stats = plot_fig2(traverse, curves, dose, relax)
    sl, ic, r2 = stats["nr2_up_dose"]
    print(f"nr2 up fit: slope = {sl:.3f} V/dec, intercept = {ic:.3f}, R^2 = {r2:.3f}")
    slc, _, r2c = stats["upper_relax"]
    print(f"upper-corner relaxation slope = {slc:+.2f} mV/dec  (R^2 = {r2c:.3f})")
    k, r2o = stats["diff_origin"]
    m, b, r2f = stats["diff_free"]
    print(f"differential through-origin k = {k:.3f}  R^2 = {r2o:.4f}")
    print(f"differential free-intercept m = {m:.3f}  b = {b:+.4f}  R^2 = {r2f:.4f}")
    print_summary(traverse, picks, stats)


if __name__ == "__main__":
    main()
