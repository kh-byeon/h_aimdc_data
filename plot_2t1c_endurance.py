"""
Plot 2T1C endurance measurements from a single Excel workbook.

Produces two publication-quality figures:
  1. ``1_endurance_vs_cycle`` — normalized ADC code of each probe plate voltage
     versus cycle count (symlog x-axis so the pristine cycle-0 sweep is shown).
  2. ``2_endurance_degradation`` — relative degradation (%) referenced to the
     pristine sweep, with -10% / -20% threshold crossings tabulated.

Edit the CONFIG block below, then run:
    python plot_2t1c_endurance.py
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.transforms as mtransforms
import numpy as np
import pandas as pd

# ==============================================================================
# CONFIG — edit these, nothing else
# ==============================================================================

XLSX_PATH = Path(__file__).parent / "2t1c_endurance" / "endurance_20260724_203233.xlsx"  # workbook path
OUTDIR = Path(__file__).parent / "2t1c_endurance"  # output directory (created if missing)

NORM_MODE = "global"  # "global" | "percycle" | "none"
PROBE_POINTS = None  # None -> read PROBE_POINTS from the config sheet; or e.g. [-2.0, -1.0, 0.0, 1.0, 2.0, 3.0]

DPI = 300  # figure DPI
FMT = "png"  # "png" | "pdf" | "svg"
SHOW = False  # True -> plt.show() in addition to saving

# ==============================================================================

# ------------------------------------------------------------------ style ----
FIGSIZE = (8, 6)  # inches
CMAP_NAME = "viridis"  # sequential map sampled once per probe point
LINEWIDTH = 2.0
MARKERSIZE = 5
MARKER = "o"
LINESTYLE = "-"
GRID_ALPHA = 0.5
GRID_LW = 0.5
FONT_FAMILY = "sans-serif"
FONT_SANS = ["Arial", "Helvetica", "DejaVu Sans"]
FONT_TITLE = 18
FONT_SUBTITLE = 9
FONT_LABEL = 18
FONT_TICK = 18  # x/y tick labels; keep >= 8
FONT_LEGEND = 18
FONT_WEIGHT_LABEL = "bold"
FONT_WEIGHT_TICK = "bold"
TICK_LEN_MAJOR = 6
TICK_LEN_MINOR = 3
TICK_WIDTH_MAJOR = 1.0
TICK_WIDTH_MINOR = 0.7
TICK_DIRECTION = "in"  # "in" | "out" | "inout"
TICKS_ALL_SIDES = True  # mirror ticks on top/right spines
SUBTITLE_COLOR = "0.35"
SUBTITLE_PAD = 10
SUPTITLE_Y = 0.98
REF_LINE_COLOR = "0.6"  # 0 / -10% / -20% guides and the x=1 log-boundary
REF_LINE_LS = "--"
REF_LINE_LW = 0.9
REF_ANNOT_COLOR = "0.4"
SHOW_TITLES = False  # True -> draw suptitle + grey subtitle on the figure
INLINE_LABELS = False  # True -> annotate each series at the last point
X_MAJOR_TICKS = [10.0 ** i for i in range(0, 11)]  # 1, 10, 10^2, ..., 10^10
XLIM_RIGHT_PAD = 1.3  # right limit = max(cycle) * this
# -----------------------------------------------------------------------------

# Schema / data checks (not style)
ENDURANCE_SHEET = "endurance"
CONFIG_SHEET = "config"
REQUIRED_COLUMNS = ("cycle", "v_plate", "code_avg")
REQUIRED_CONFIG_KEYS = (
    "PROBE_POINTS",
    "DEVICE",
    "WRITE_V (V)",
    "BIAS_V (V)",
    "PULSE_WIDTH_US",
    "PULSE_PERIOD_US",
    "cycle_rate (Hz)",
    "N_CYCLES_DONE",
    "READ_INTEG (ms)",
)
EXPECTED_VPLATE_ROWS = 51
PROBE_TOL = 1e-6


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------
def _get(cfg: Dict[str, Any], key: str, cast: Callable[[Any], Any] = float) -> Any:
    """Return ``cfg[key]`` cast with ``cast``; fail loudly if missing/uncastable."""
    if key not in cfg:
        raise KeyError(
            f"Required config key {key!r} not found in config sheet; "
            f"available keys: {sorted(cfg)}"
        )
    raw = cfg[key]
    try:
        return cast(raw)
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"Config key {key!r}={raw!r} could not be cast via {cast}: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def load_workbook(path: Path) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """Read the workbook once and return (endurance DataFrame, config dict)."""
    if not path.is_file():
        raise FileNotFoundError(f"Workbook not found: {path}")

    sheets = pd.read_excel(path, sheet_name=None)

    if ENDURANCE_SHEET not in sheets:
        raise KeyError(
            f"Sheet {ENDURANCE_SHEET!r} missing; found sheets: {list(sheets)}"
        )
    if CONFIG_SHEET not in sheets:
        raise KeyError(
            f"Sheet {CONFIG_SHEET!r} missing; found sheets: {list(sheets)}"
        )

    df = sheets[ENDURANCE_SHEET]
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise KeyError(
            f"endurance sheet missing required column(s) {missing_cols}; "
            f"got {list(df.columns)}"
        )

    cfg = _parse_config(sheets[CONFIG_SHEET])
    missing_keys = [k for k in REQUIRED_CONFIG_KEYS if k not in cfg]
    if missing_keys:
        raise KeyError(
            f"config sheet missing required key(s) {missing_keys}; "
            f"available keys: {sorted(cfg)}"
        )
    return df, cfg


def _parse_config(cfg_df: pd.DataFrame) -> Dict[str, str]:
    """Turn a two-column parameter/value sheet into a ``{param: value}`` dict."""
    cols = {str(c).strip().lower(): c for c in cfg_df.columns}
    param_col = cols.get("parameter")
    value_col = cols.get("value")
    if param_col is None or value_col is None:
        raise ValueError(
            f"config sheet must have 'parameter' and 'value' columns; "
            f"got {list(cfg_df.columns)}"
        )

    cfg: Dict[str, str] = {}
    for _, row in cfg_df.iterrows():
        key = row[param_col]
        if pd.isna(key):
            continue
        cfg[str(key).strip()] = "" if pd.isna(row[value_col]) else str(row[value_col]).strip()
    return cfg


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------
def normalize(df: pd.DataFrame, mode: str) -> Tuple[pd.DataFrame, float, str]:
    """
    Add a ``code_norm`` column and return (df, divisor, divisor_description).

    - ``global``: divide by the global max of ``code_avg`` (default).
    - ``percycle``: divide by each cycle's own max ``code_avg``.
    - ``none``: keep raw ``code_avg`` (divisor 1).
    """
    out = df.copy()
    code = out["code_avg"].to_numpy(dtype=float)

    if mode == "global":
        divisor = float(np.nanmax(code))
        if divisor <= 0 or not np.isfinite(divisor):
            raise ValueError(f"Invalid global max for normalization: {divisor}")
        out["code_norm"] = code / divisor
        return out, divisor, f"normalized by max ADC code = {divisor:.1f}"

    if mode == "percycle":
        per_max = out.groupby("cycle")["code_avg"].transform("max")
        out["code_norm"] = code / per_max.to_numpy(dtype=float)
        return out, float("nan"), "normalized by per-cycle max ADC code"

    if mode == "none":
        out["code_norm"] = code
        return out, 1.0, "no normalization (raw ADC code)"

    raise ValueError(f"Unknown norm mode: {mode!r}")


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------
def probe_series(df: pd.DataFrame, v: float, tol: float = PROBE_TOL) -> pd.DataFrame:
    """Rows whose ``v_plate`` is within ``tol`` of ``v``, sorted by cycle."""
    mask = np.abs(df["v_plate"].to_numpy(dtype=float) - v) < tol
    return df.loc[mask].sort_values("cycle").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
def apply_plot_style() -> None:
    """Apply module-level font / background rcParams."""
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "font.family": FONT_FAMILY,
            "font.sans-serif": FONT_SANS,
            "font.size": FONT_TICK,
            "axes.labelsize": FONT_LABEL,
            "axes.titlesize": FONT_TITLE,
            "legend.fontsize": FONT_LEGEND,
            "xtick.labelsize": FONT_TICK,
            "ytick.labelsize": FONT_TICK,
        }
    )


def _probe_colors(n: int) -> List[tuple]:
    """Evenly spaced colormap samples so voltage order is visually sequential."""
    cmap = plt.get_cmap(CMAP_NAME)
    return [cmap(i / max(n - 1, 1)) for i in range(n)]


def _style_ax(ax: plt.Axes) -> None:
    """Shared publication style: spines, major/minor ticks, decade-only grid."""
    ax.spines["top"].set_visible(True)
    ax.spines["right"].set_visible(True)
    ax.tick_params(
        axis="both",
        which="major",
        length=TICK_LEN_MAJOR,
        width=TICK_WIDTH_MAJOR,
        direction=TICK_DIRECTION,
        labelsize=FONT_TICK,
    )
    ax.tick_params(
        axis="both",
        which="minor",
        length=TICK_LEN_MINOR,
        width=TICK_WIDTH_MINOR,
        direction=TICK_DIRECTION,
    )
    if TICKS_ALL_SIDES:
        ax.tick_params(axis="both", which="both", top=True, right=True)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontweight(FONT_WEIGHT_TICK)
    ax.set_axisbelow(True)
    ax.grid(True, which="major", alpha=GRID_ALPHA, linewidth=GRID_LW)
    ax.grid(False, which="minor")
    # ax.grid(True, which="minor", axis="x", alpha=GRID_ALPHA * 0.4, linewidth=GRID_LW * 0.7)


def _cycle_fmt(x: float, _pos: object) -> str:
    """Render decades as $10^{n}$, including $10^{0}$."""
    if x <= 0:
        return ""
    exp = int(round(np.log10(x)))
    return rf"$\mathbf{{10^{{{exp}}}}}$"


def style_cycle_axis(ax: plt.Axes, x_max: float) -> None:
    """Log x-axis: labeled 10^n majors, unlabeled 2–9 minor ticks per decade."""
    ax.set_xscale("log", base=10)
    ax.set_xlabel("", fontsize=FONT_LABEL, fontweight=FONT_WEIGHT_LABEL)
    ax.set_xlim(left=1, right=float(x_max) * XLIM_RIGHT_PAD)
    ax.xaxis.set_major_locator(mticker.LogLocator(base=10, numticks=12))
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_cycle_fmt))
    # Explicit 2–9 sub-decade ticks; more reliable than LogLocator(subs=...) here.
    d_max = int(np.ceil(np.log10(max(float(x_max), 1.0))))
    minor = [m * 10.0 ** d for d in range(0, d_max + 1) for m in range(2, 10)]
    ax.xaxis.set_minor_locator(mticker.FixedLocator(minor))
    ax.xaxis.set_minor_formatter(mticker.NullFormatter())
    ax.yaxis.set_minor_locator(mticker.AutoMinorLocator(2))
    ax.yaxis.set_minor_formatter(mticker.NullFormatter())
    ax.axvline(
        1.0,
        color=REF_LINE_COLOR,
        linestyle=REF_LINE_LS,
        linewidth=REF_LINE_LW,
        zorder=1,
    )
    _style_ax(ax)


def _build_subtitle(cfg: Dict[str, str], src_name: str, divisor_desc: str) -> str:
    """Provenance line: source + experimental conditions + norm divisor."""
    device = _get(cfg, "DEVICE", cast=str)
    write_v = _get(cfg, "WRITE_V (V)", cast=str)
    pulse_w = _get(cfg, "PULSE_WIDTH_US", cast=str)
    pulse_p = _get(cfg, "PULSE_PERIOD_US", cast=str)
    rate = _get(cfg, "cycle_rate (Hz)", cast=str)
    return (
        f"{src_name}  |  {device}  |  WRITE={write_v} V  |  "
        f"pulse {pulse_w}/{pulse_p} us  |  {rate} Hz  |  {divisor_desc}"
    )


def _finish_layout(fig: plt.Figure, ax: plt.Axes, main_title: str, subtitle: str) -> None:
    """Optional titles, then tight_layout so the axes fill the figure."""
    if SHOW_TITLES:
        fig.suptitle(main_title, fontsize=FONT_TITLE, fontweight="bold", y=SUPTITLE_Y)
        ax.set_title(subtitle, fontsize=FONT_SUBTITLE, color=SUBTITLE_COLOR, pad=SUBTITLE_PAD)
    fig.tight_layout()
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontweight(FONT_WEIGHT_TICK)


def _maybe_inline_label(ax: plt.Axes, x: np.ndarray, y: np.ndarray, text: str, color: object) -> None:
    """Annotate the last point of a series when INLINE_LABELS is True."""
    if not INLINE_LABELS or len(x) == 0:
        return
    ax.annotate(
        text,
        xy=(float(x[-1]), float(y[-1])),
        xytext=(4, 0),
        textcoords="offset points",
        va="center",
        fontsize=FONT_LEGEND,
        color=color,
        clip_on=False,
    )


# ---------------------------------------------------------------------------
# Figure 1
# ---------------------------------------------------------------------------
def plot_retention(
    df: pd.DataFrame,
    cfg: Dict[str, str],
    outdir: Path,
    probe_points: List[float],
    divisor_desc: str,
    norm_mode: str,
    src_name: str,
    dpi: int,
    fmt: str,
    show: bool,
) -> Path:
    """Figure 1: normalized ADC code vs cycle for each probe plate voltage."""
    colors = _probe_colors(len(probe_points))
    fig, ax = plt.subplots(figsize=FIGSIZE, constrained_layout=False)

    x_max = float(df["cycle"].max())
    for v, color in zip(probe_points, colors):
        sub = probe_series(df, v)
        if sub.empty:
            raise ValueError(f"No rows for probe v_plate={v:+.1f} V")
        xs = sub["cycle"].to_numpy(dtype=float)
        ys = sub["code_norm"].to_numpy(dtype=float)
        ax.plot(
            xs,
            ys,
            linestyle=LINESTYLE,
            marker=MARKER,
            markersize=MARKERSIZE,
            linewidth=LINEWIDTH,
            color=color,
            label=f"V_plate = {v:+.1f} V",
        )
        _maybe_inline_label(ax, xs, ys, f"{v:+.1f} V", color)

    style_cycle_axis(ax, x_max)
    ax.set_ylabel("", fontsize=FONT_LABEL, fontweight=FONT_WEIGHT_LABEL)
    _finish_layout(
        fig,
        ax,
        f"2T1C Endurance: retention vs cycle  (norm={norm_mode})",
        _build_subtitle(cfg, src_name, divisor_desc),
    )

    out_path = outdir / f"1_endurance_vs_cycle.{fmt}"
    fig.savefig(out_path, dpi=dpi, facecolor="white", bbox_inches="tight")
    if show:
        plt.show()
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------------
# Figure 2
# ---------------------------------------------------------------------------
def plot_degradation(
    df: pd.DataFrame,
    cfg: Dict[str, str],
    outdir: Path,
    probe_points: List[float],
    src_name: str,
    dpi: int,
    fmt: str,
    show: bool,
) -> Tuple[Path, pd.DataFrame]:
    """
    Figure 2: relative degradation (%) referenced to the pristine (cycle 0) sweep.

    The y-value is 100 * (code_avg(cycle) / code_avg(cycle=0) - 1). This uses the
    RAW code_avg ratio, which is normalization-invariant, so this figure does not
    depend on NORM_MODE.
    """
    colors = _probe_colors(len(probe_points))
    fig, ax = plt.subplots(figsize=FIGSIZE, constrained_layout=False)

    records: List[Dict[str, float]] = []
    x_max = float(df["cycle"].max())

    for v, color in zip(probe_points, colors):
        sub = probe_series(df, v)
        if sub.empty:
            raise ValueError(f"No rows for probe v_plate={v:+.1f} V")

        cycles = sub["cycle"].to_numpy(dtype=float)
        code = sub["code_avg"].to_numpy(dtype=float)

        base_mask = cycles == 0
        if not base_mask.any():
            raise ValueError(f"No pristine (cycle=0) sweep for v_plate={v:+.1f} V")
        base = float(code[base_mask][0])
        if base == 0 or not np.isfinite(base):
            raise ValueError(
                f"Invalid cycle-0 code_avg={base} for v_plate={v:+.1f} V"
            )
        pct = 100.0 * (code / base - 1.0)

        ax.plot(
            cycles,
            pct,
            linestyle=LINESTYLE,
            marker=MARKER,
            markersize=MARKERSIZE,
            linewidth=LINEWIDTH,
            color=color,
            label=f"V_plate = {v:+.1f} V",
        )
        _maybe_inline_label(ax, cycles, pct, f"{v:+.1f} V", color)

        records.append(
            {
                "v_plate": v,
                "cycles_to_10pct": _first_crossing(cycles, pct, -10.0),
                "cycles_to_20pct": _first_crossing(cycles, pct, -20.0),
                "final_pct": float(pct[-1]) if len(pct) else float("nan"),
            }
        )

    # Reference lines behind data, annotated at the right edge of the axes.
    blended = mtransforms.blended_transform_factory(ax.transAxes, ax.transData)
    for level in (0.0, -10.0, -20.0):
        ax.axhline(
            level,
            color=REF_LINE_COLOR,
            linestyle=REF_LINE_LS,
            linewidth=REF_LINE_LW,
            zorder=1,  # keep guides behind the data series
        )
        ax.text(
            0.995,  # axes-fraction x; glued to the right spine
            level,
            f"{level:g}%",
            transform=blended,
            ha="right",
            va="bottom",
            fontsize=FONT_LEGEND,
            color=REF_ANNOT_COLOR,
        )

    style_cycle_axis(ax, x_max)
    ax.set_ylabel("Degradation vs pristine (%)", fontsize=FONT_LABEL, fontweight=FONT_WEIGHT_LABEL)
    _finish_layout(
        fig,
        ax,
        "2T1C Endurance: normalized degradation",
        _build_subtitle(cfg, src_name, "ratio to cycle-0 (norm-invariant)"),
    )

    out_path = outdir / f"2_endurance_degradation.{fmt}"
    fig.savefig(out_path, dpi=dpi, facecolor="white", bbox_inches="tight")
    if show:
        plt.show()
    plt.close(fig)

    summary = pd.DataFrame.from_records(
        records, columns=["v_plate", "cycles_to_10pct", "cycles_to_20pct", "final_pct"]
    )
    csv_path = outdir / "degradation_thresholds.csv"
    summary.to_csv(csv_path, index=False)
    print("\nDegradation threshold summary:")
    print(summary.to_string(index=False, na_rep="NaN"))
    print(f"\nThreshold table written -> {csv_path}")

    return out_path, summary


def _first_crossing(cycles: np.ndarray, pct: np.ndarray, level: float) -> float:
    """First cycle where degradation ``pct`` drops to/below ``level``; NaN if never."""
    for c, p in zip(cycles, pct):
        if np.isfinite(p) and p <= level:
            return float(c)
    return float("nan")


# ---------------------------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------------------------
def check_row_counts(df: pd.DataFrame) -> None:
    """Assert each cycle has exactly EXPECTED_VPLATE_ROWS v_plate rows."""
    counts = df.groupby("cycle").size()
    offending = counts[counts != EXPECTED_VPLATE_ROWS]
    if not offending.empty:
        detail = ", ".join(f"cycle {int(c)}: {int(n)} rows" for c, n in offending.items())
        raise ValueError(
            f"Expected {EXPECTED_VPLATE_ROWS} v_plate rows per cycle; offending: {detail}"
        )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def _resolve_probe_points(cfg: Dict[str, str], override: Optional[List[float]]) -> List[float]:
    """Probe plate voltages from PROBE_POINTS override or the config sheet."""
    if override is not None:
        return [float(v) for v in override]
    raw = _get(cfg, "PROBE_POINTS", cast=str)
    points = ast.literal_eval(raw)
    return [float(p) for p in points]


def main() -> None:
    """Load the workbook, build both figures, and print a run summary."""
    apply_plot_style()

    df, cfg = load_workbook(XLSX_PATH)
    check_row_counts(df)
    probe_points = _resolve_probe_points(cfg, PROBE_POINTS)

    df, divisor, divisor_desc = normalize(df, NORM_MODE)

    OUTDIR.mkdir(parents=True, exist_ok=True)
    src_name = XLSX_PATH.name

    path1 = plot_retention(
        df,
        cfg,
        OUTDIR,
        probe_points,
        divisor_desc,
        NORM_MODE,
        src_name,
        DPI,
        FMT,
        SHOW,
    )
    path2, _summary = plot_degradation(
        df, cfg, OUTDIR, probe_points, src_name, DPI, FMT, SHOW
    )

    cycles = np.sort(df["cycle"].unique())
    vplate_per_cycle = int(df.groupby("cycle").size().iloc[0])
    print("\n=== Run summary ===")
    print(f"  provenance: {_build_subtitle(cfg, src_name, divisor_desc)}")
    print(f"  cycles: {len(cycles)} (range {int(cycles.min())} .. {int(cycles.max())})")
    print(f"  v_plate points per cycle: {vplate_per_cycle}")
    print(f"  probe points: {probe_points}")
    print(f"  norm mode: {NORM_MODE} ({divisor_desc}); divisor={divisor}")
    print(f"  figure 1 -> {path1}")
    print(f"  figure 2 -> {path2}")


if __name__ == "__main__":
    main()
