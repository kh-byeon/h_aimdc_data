"""
Parse and plot FeFET retention measurements (DAC retention v2 Excel exports).

Each file in ``FeFET_retention/`` is processed independently. Measurements mix
``probe`` (sparse Vgs) and ``sweep`` (dense Id–Vg) checkpoints. The figure
plots normalized ADC (code / 4095) versus retention time (log x, linear y)
with one series per probe Vgs: probe rows plus sweep rows at those Vgs for
the 1 s / 10 hr endpoints.
The plot shows a log10(t)-linear fit over measured points with t ≤ 10800 s
(the 3 h / ~10^4 s checkpoint), extrapolated to 10 years; later measured
points are not plotted.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent / "FeFET_retention"
PROBE_VGS = [-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0]
VGS_TOL = 1e-6
ADC_FULL_SCALE = 4095

ADC_COLUMN_CANDIDATES = (
    "adc",
    "adc_code",
    "code",
    "adc_raw",
    "dac_readback",
    "n_adc",
)

FIG_SIZE = (8, 6)
DPI = 300

# Style (aligned with vth_comp/write_disturb/plot_write_disturb.py)
FONT_BASE = 18
FONT_AXIS = 18
FONT_PANEL = 18
LW_CURVE = 2.0
GRID_ALPHA = 0.5

FIT_TIME_MAX_S = 1.08e4       # include 3 h = 10800 s (~10^4 s) in the fit
T_10YR_S = 10 * 365.25 * 24 * 3600  # ~3.156e8 s, extrapolation target


# ---------------------------------------------------------------------------
# Parsing (dac_retention_v2 xlsx)
# ---------------------------------------------------------------------------
def _probe_vgs_from_config(xlsx_path: Path) -> List[float]:
    """Read PROBE_VGS from the config sheet when present; else use default."""
    try:
        cfg = pd.read_excel(xlsx_path, sheet_name="config")
    except Exception:
        return list(PROBE_VGS)

    key_col = next((c for c in cfg.columns if str(c).lower() in ("key", "name", "param")), None)
    val_col = next((c for c in cfg.columns if str(c).lower() in ("value", "val")), None)
    if key_col is None or val_col is None:
        return list(PROBE_VGS)

    for _, row in cfg.iterrows():
        if str(row[key_col]).strip().upper() != "PROBE_VGS":
            continue
        raw = str(row[val_col]).strip()
        # e.g. "[-3, -2, -1, 0, 1, 2, 3]"
        nums = [
            float(tok)
            for tok in raw.replace("[", "").replace("]", "").split(",")
            if tok.strip()
        ]
        if nums:
            return nums
    return list(PROBE_VGS)


def _find_adc_column(df: pd.DataFrame) -> str:
    """
    Locate the ADC column in a sweeps sheet by case-insensitive name match.

    Tries exact matches against ``ADC_COLUMN_CANDIDATES`` first, then columns
    whose lower-cased name contains a candidate (preferring ``*avg*`` when
    several ``code*`` columns exist).
    """
    cols = [str(c) for c in df.columns]
    lower_map = {c.lower(): c for c in cols}

    for cand in ADC_COLUMN_CANDIDATES:
        if cand in lower_map:
            return lower_map[cand]

    for cand in ADC_COLUMN_CANDIDATES:
        matches = [c for c in cols if cand in c.lower()]
        if not matches:
            continue
        matches.sort(key=lambda c: (0 if "avg" in c.lower() else 1, c.lower()))
        return matches[0]

    raise ValueError(
        f"No ADC column found (tried {list(ADC_COLUMN_CANDIDATES)}); "
        f"available columns: {cols}"
    )


def _is_probe_vgs(v: float, probe_vgs: Sequence[float]) -> bool:
    return any(abs(v - p) <= VGS_TOL for p in probe_vgs)


def _match_vgs(v: float, probe_vgs: Sequence[float]) -> Optional[float]:
    """Return the canonical probe Vgs matching ``v``, or None."""
    for p in probe_vgs:
        if abs(v - p) <= VGS_TOL:
            return float(p)
    return None


def parse_probe_retention(
    xlsx_path: Path,
) -> Tuple[List[float], List[str], List[Tuple[np.ndarray, np.ndarray]]]:
    """
    Build probe-grid curves for every checkpoint using normalized ADC.

    - ``kind == "probe"``: use all rows.
    - ``kind == "sweep"``: keep only rows whose ``v_gate`` is in the probe grid
      (covers 1 s and 10 hr endpoints).

    Returns (t_target_s list, checkpoint labels, list of (Vg, norm_adc) arrays),
    ordered by increasing ``t_target_s``. Normalized ADC is ``raw / ADC_FULL_SCALE``.
    """
    probe_vgs = _probe_vgs_from_config(xlsx_path)
    df = pd.read_excel(xlsx_path, sheet_name="sweeps")

    required = {"checkpoint", "kind", "t_target_s", "v_gate"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{xlsx_path.name}: sweeps sheet missing columns {sorted(missing)}")

    adc_col = _find_adc_column(df)

    probe_mask = df["kind"].astype(str).str.lower() == "probe"
    sweep_at_probe = (df["kind"].astype(str).str.lower() == "sweep") & df["v_gate"].map(
        lambda v: _is_probe_vgs(float(v), probe_vgs)
    )
    sel = df.loc[probe_mask | sweep_at_probe].copy()
    if sel.empty:
        raise ValueError(f"{xlsx_path.name}: no probe / probe-Vgs sweep rows found")

    raw_adc = pd.to_numeric(sel[adc_col], errors="coerce")
    n_oob = int(((raw_adc < 0) | (raw_adc > ADC_FULL_SCALE)).sum())
    if n_oob > 0:
        print(
            f"  WARNING: {xlsx_path.name}: {n_oob} raw ADC value(s) outside "
            f"[0, {ADC_FULL_SCALE}] (column {adc_col!r})"
        )

    # One curve per checkpoint, ordered by target time
    order = (
        sel.groupby("checkpoint", sort=False)["t_target_s"]
        .first()
        .sort_values()
    )
    time_points: List[float] = []
    labels: List[str] = []
    curves: List[Tuple[np.ndarray, np.ndarray]] = []

    for cp, t_s in order.items():
        block = sel.loc[sel["checkpoint"] == cp].sort_values("v_gate")
        vg = block["v_gate"].to_numpy(dtype=float)
        norm_adc = pd.to_numeric(block[adc_col], errors="coerce").to_numpy(dtype=float) / ADC_FULL_SCALE
        time_points.append(float(t_s))
        labels.append(str(cp))
        curves.append((vg, norm_adc))

    return time_points, labels, curves


def pivot_by_vgs(
    time_points: List[float],
    labels: List[str],
    curves: List[Tuple[np.ndarray, np.ndarray]],
    probe_vgs: Sequence[float],
) -> Dict[float, Tuple[np.ndarray, np.ndarray]]:
    """
    Convert per-checkpoint (Vg, norm_adc) curves into per-Vgs time series.

    Returns an ordered mapping ``{vgs: (t_array, norm_adc_array)}`` over
    ``probe_vgs``. Checkpoints where a given Vgs is missing are skipped.
    """
    buckets: Dict[float, List[Tuple[float, float]]] = {float(v): [] for v in probe_vgs}
    n = min(len(time_points), len(labels), len(curves))

    for i in range(n):
        t_s = float(time_points[i])
        vg_arr, adc_arr = curves[i]
        for vg, norm_adc in zip(vg_arr, adc_arr):
            key = _match_vgs(float(vg), probe_vgs)
            if key is None:
                continue
            if not np.isfinite(norm_adc):
                continue
            buckets[key].append((t_s, float(norm_adc)))

    series: Dict[float, Tuple[np.ndarray, np.ndarray]] = {}
    for vgs in probe_vgs:
        pts = buckets[float(vgs)]
        if not pts:
            continue
        pts_sorted = sorted(pts, key=lambda p: p[0])
        t_arr = np.array([p[0] for p in pts_sorted], dtype=float)
        adc_out = np.array([p[1] for p in pts_sorted], dtype=float)
        series[float(vgs)] = (t_arr, adc_out)
    return series


def drop_nonpositive_times(
    time_points: List[float],
    labels: List[str],
    curves: List[Tuple[np.ndarray, np.ndarray]],
    file_name: str,
) -> Tuple[List[float], List[str], List[Tuple[np.ndarray, np.ndarray]]]:
    """Drop checkpoints with ``t_target_s <= 0`` (log axis cannot show them)."""
    kept_t: List[float] = []
    kept_lab: List[str] = []
    kept_curves: List[Tuple[np.ndarray, np.ndarray]] = []
    dropped: List[str] = []

    n = min(len(time_points), len(labels), len(curves))
    for i in range(n):
        if time_points[i] <= 0:
            dropped.append(f"{labels[i]} (t={time_points[i]:g} s)")
            continue
        kept_t.append(time_points[i])
        kept_lab.append(labels[i])
        kept_curves.append(curves[i])

    if dropped:
        print(
            f"  WARNING: {file_name}: dropped non-positive time checkpoint(s) "
            f"for log x-axis: {', '.join(dropped)}"
        )
    return kept_t, kept_lab, kept_curves


def fit_log_linear(
    t_arr: np.ndarray,
    y_arr: np.ndarray,
    t_max: float = FIT_TIME_MAX_S,
) -> Optional[dict]:
    """Fit y = a + b * log10(t) on 1 <= t <= t_max. Returns None if n < 2."""
    t_arr = np.asarray(t_arr, float)
    y_arr = np.asarray(y_arr, float)
    mask = (t_arr >= 1.0) & (t_arr <= t_max) & np.isfinite(y_arr) & np.isfinite(t_arr)
    t_fit = t_arr[mask]
    y_fit = y_arr[mask]
    n = int(t_fit.size)
    if n < 2:
        return None
    logt = np.log10(t_fit)
    b, a = np.polyfit(logt, y_fit, 1)
    yhat = a + b * logt
    ss_res = float(np.sum((y_fit - yhat) ** 2))
    ss_tot = float(np.sum((y_fit - y_fit.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return {
        "a": float(a),
        "b": float(b),
        "r2": r2,
        "n_fit": n,
        "t_fit_min": float(t_fit.min()),
        "t_fit_max": float(t_fit.max()),
    }


def _y_at(fit: dict, t: float) -> float:
    return float(fit["a"] + fit["b"] * np.log10(t))


# ---------------------------------------------------------------------------
# Plotting
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
            "legend.fontsize": FONT_BASE,
            "xtick.labelsize": FONT_BASE,
            "ytick.labelsize": FONT_BASE,
        }
    )


def _style_ax(ax: plt.Axes) -> None:
    """Apply the shared publication style (spines, ticks, bold labels, grid)."""
    ax.spines["top"].set_visible(True)
    ax.spines["right"].set_visible(True)
    ax.tick_params(axis="both", which="major", width=1.5, length=6)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontweight("bold")
    ax.grid(True, which="major", alpha=GRID_ALPHA, linewidth=0.5)


def plot_retention_vs_time(
    series: Dict[float, Tuple[np.ndarray, np.ndarray]],
    fits: Dict[float, Optional[dict]],
    out_path: Path,
    title: str,
) -> None:
    if not series:
        raise ValueError("No Vgs time series to plot")

    vgs_list = list(series.keys())
    n = len(vgs_list)
    cmap = plt.get_cmap("viridis")
    colors = [cmap(i / max(n - 1, 1)) for i in range(n)]

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    ax.set_xscale("log")
    ax.axvspan(1.0, FIT_TIME_MAX_S, color="0.85", alpha=0.35, zorder=0, lw=0)
    ax.axvline(86400.0, color="0.45", ls=":", lw=0.9, zorder=1)
    ax.axvline(T_10YR_S, color="0.45", ls=":", lw=0.9, zorder=1)
    ax.text(
        86400.0, 0.97, "1 day",
        transform=ax.get_xaxis_transform(),
        ha="center", va="top", fontsize=14, fontweight="bold", color="0.35",
    )
    ax.text(
        T_10YR_S, 0.97, "10 yr",
        transform=ax.get_xaxis_transform(),
        ha="right", va="top", fontsize=14, fontweight="bold", color="0.35",
        clip_on=True,
    )

    t_fit_line = np.logspace(np.log10(1.0), np.log10(FIT_TIME_MAX_S), 80)
    t_extrap_line = np.logspace(np.log10(FIT_TIME_MAX_S), np.log10(T_10YR_S), 80)

    for i, vgs in enumerate(vgs_list):
        t_arr, norm_adc = series[vgs]
        color = colors[i]
        in_fit = (t_arr <= FIT_TIME_MAX_S) & np.isfinite(norm_adc)
        ax.plot(
            t_arr[in_fit], norm_adc[in_fit],
            ls="none", marker="o", markersize=5,
            color=color, zorder=3, label=f"{vgs:.1f} V",
        )
        fit = fits.get(vgs)
        if fit is None:
            continue
        y_fit = fit["a"] + fit["b"] * np.log10(t_fit_line)
        y_ex = fit["a"] + fit["b"] * np.log10(t_extrap_line)
        ax.plot(t_fit_line, y_fit, color=color, lw=LW_CURVE, ls="-", zorder=2)
        ax.plot(t_extrap_line, y_ex, color=color, lw=LW_CURVE, ls="--", zorder=2)

    #ax.set_xlabel("Retention time (s)", fontsize=FONT_AXIS, fontweight="bold")
    ax.set_ylabel(
        f"",
        fontsize=FONT_AXIS,
        fontweight="bold",
    )
    ax.set_xlim(1.0, T_10YR_S)
    ax.set_ylim(-0.02, 1.02)
    ax.axhline(1.0, color="0.7", linewidth=0.9, linestyle="--", zorder=1)
    ax.set_title(title, fontsize=FONT_PANEL, fontweight="bold")
    _style_ax(ax)
    #ax.legend(loc="best", framealpha=0.92, ncol=2, title=r"$V_G$ (V)")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=DPI, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"Figure saved -> {out_path}")


# ---------------------------------------------------------------------------
# Batch driver
# ---------------------------------------------------------------------------
def process_file(xlsx_path: Path) -> None:
    time_points, labels, curves = parse_probe_retention(xlsx_path)
    time_points, labels, curves = drop_nonpositive_times(
        time_points, labels, curves, xlsx_path.name
    )
    probe_vgs = _probe_vgs_from_config(xlsx_path)
    series = pivot_by_vgs(time_points, labels, curves, probe_vgs)
    fits: Dict[float, Optional[dict]] = {
        vgs: fit_log_linear(t_arr, y_arr) for vgs, (t_arr, y_arr) in series.items()
    }

    print(f"File: {xlsx_path.name}")
    print(f"  Vgs series: {len(series)}")
    for vgs, (t_arr, adc_arr) in series.items():
        t_min = float(t_arr.min()) if len(t_arr) else float("nan")
        t_max = float(t_arr.max()) if len(t_arr) else float("nan")
        a_min = float(adc_arr.min()) if len(adc_arr) else float("nan")
        a_max = float(adc_arr.max()) if len(adc_arr) else float("nan")
        print(
            f"    Vg={vgs:+.1f} V  n={len(t_arr)}  "
            f"t=[{t_min:g}, {t_max:g}] s  "
            f"norm_adc=[{a_min:.4f}, {a_max:.4f}]"
        )

    print()
    print(f"  log10(t)-linear fit  (1 s ≤ t ≤ {FIT_TIME_MAX_S:g} s)  →  10 yr")
    print(f"  {'Vg':>7}  {'n_fit':>5}  {'slope/dec':>10}  {'a (t=1s)':>10}  {'R^2':>7}  {'y(10 yr)':>10}")
    print("  " + "-" * 60)
    for vgs in series:
        fit = fits.get(vgs)
        if fit is None:
            print(f"  {vgs:+7.1f}      —         —           —        —           —")
            continue
        y10 = _y_at(fit, T_10YR_S)
        print(
            f"  {vgs:+7.1f}  {fit['n_fit']:5d}  {fit['b']:+10.5f}  "
            f"{fit['a']:10.4f}  {fit['r2']:7.3f}  {y10:10.4f}"
        )

    print()
    print("  Adjacent-state gap retention (from fits)")
    print(f"  {'pair':<16}  {'gap@1s':>8}  {'gap@10yr':>9}  {'retained':>8}")
    print("  " + "-" * 48)
    vg_order = [float(v) for v in probe_vgs]
    for v0, v1 in zip(vg_order[:-1], vg_order[1:]):
        f0, f1 = fits.get(v0), fits.get(v1)
        if f0 is None or f1 is None:
            print(f"  {v0:+.1f} → {v1:+.1f}         —          —         —")
            continue
        gap_1s = abs(_y_at(f0, 1.0) - _y_at(f1, 1.0))
        gap_10 = abs(_y_at(f0, T_10YR_S) - _y_at(f1, T_10YR_S))
        retained = 100.0 * gap_10 / gap_1s if gap_1s > 0 else float("nan")
        print(
            f"  {v0:+.1f} → {v1:+.1f}     {gap_1s:8.4f}  {gap_10:9.4f}  {retained:7.1f}%"
        )

    title = f""
    out_path = DATA_DIR / f"{xlsx_path.stem}_adc_retention_vs_time.png"
    plot_retention_vs_time(series, fits, out_path, title)


def main() -> int:
    if not DATA_DIR.is_dir():
        print(f"ERROR: data folder not found: {DATA_DIR}", file=sys.stderr)
        return 1

    files = sorted(DATA_DIR.glob("*_dac_retention_v2_*.xlsx"))
    if not files:
        files = sorted(DATA_DIR.glob("*.xlsx"))
    if not files:
        print(f"ERROR: no .xlsx files in {DATA_DIR}", file=sys.stderr)
        return 1

    apply_plot_style()
    ok, failed = 0, 0
    for path in files:
        try:
            process_file(path)
            ok += 1
        except Exception as exc:
            failed += 1
            print(f"WARNING: failed to process {path.name}: {exc}")

    print(f"Done: {ok} succeeded, {failed} failed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
