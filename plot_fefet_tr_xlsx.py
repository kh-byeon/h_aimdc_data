"""
Batch-plot FeFET transfer (Id-Vg) double-sweep curves from Keithley 4200 (Clarius)
.xlsx exports, e.g. FeFET_TR/260611.

Each workbook has a single "Data" sheet containing several runs side by side
(7 columns per run: Time, DrainI, DrainV, SourceI, SourceV, GateI, GateV).
Row 2 holds the run name, row 4 the column headers. Each run is a double sweep
VG: -5 V -> VG,max -> -5 V, with VG,max stepped +1 ... +5 V across runs.

Outputs (written to the same folder as the data):
  <file>_TR.png          log|ID|, all sweeps overlaid
  TR_overview_<folder>.png   every device in one grid (log|ID|)

Usage:
  python plot_fefet_tr_xlsx.py                      # default folder FeFET_TR/260611
  python plot_fefet_tr_xlsx.py FeFET_TR/260611      # or any other folder
  python plot_fefet_tr_xlsx.py --vgmax 3 5          # other VG,max selection
  python plot_fefet_tr_xlsx.py --all                # every sweep

Only sweeps with VG,max in VG_MAX_SELECT (default +5 V) are plotted.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

# Shared figure style, one source of truth with the read-disturb figures.
from read_disturb_plots import _apply_style   # noqa: E402

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DEFAULT_FOLDER = ROOT / "FeFET_TR" / "260611"

Y_LIM_LOG = (1e-15, 1e-4)
DPI = 300
BLOCK_WIDTH = 7  # columns per run

# Which sweeps to plot, by VG,max (V). None -> plot every sweep.
VG_MAX_SELECT: tuple[float, ...] | None = (5.0,)

# Filenames whose spaces were lost -> (W, L, overlap, device id)
FILENAME_OVERRIDES: dict[str, tuple[int, int, int, str]] = {
    "5104_3-13": (5, 10, 4, "3-13"),
}


# ---------------------------------------------------------------------------
# Filename parsing: "W L OV_DEV"  e.g. "10 5 2_1-2" -> W=10, L=5, OV=2, dev 1-2
# ---------------------------------------------------------------------------
def parse_filename(stem: str) -> tuple[int, int, int, str] | None:
    if stem in FILENAME_OVERRIDES:
        return FILENAME_OVERRIDES[stem]
    m = re.match(r"^\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)_(.+?)\s*$", stem)
    if m:
        return int(m[1]), int(m[2]), int(m[3]), m[4]
    return None


def build_title(stem: str) -> str:
    parsed = parse_filename(stem)
    if parsed is None:
        print(f"  NOTE: could not parse W/L/overlap from {stem!r}; using filename as title")
        return stem
    w, l, ov, dev = parsed
    return f"W/L/Overlap = {w}/{l}/{ov} µm   (device {dev})"


# ---------------------------------------------------------------------------
# Keithley 4200 xlsx parsing
# ---------------------------------------------------------------------------
def read_runs(xlsx_path: Path) -> list[dict]:
    """Return a list of runs: {name, VG, ID, IG, VD, vg_max}."""
    raw = pd.read_excel(xlsx_path, sheet_name=0, header=None)
    names = raw.iloc[1]
    headers = raw.iloc[3]

    runs = []
    for c in range(raw.shape[1]):
        if not isinstance(names.iloc[c], str):
            continue
        block = raw.iloc[4:, c : c + BLOCK_WIDTH].copy()
        block.columns = [str(h).strip() for h in headers.iloc[c : c + BLOCK_WIDTH]]
        block = block.apply(pd.to_numeric, errors="coerce").dropna(subset=["GateV", "DrainI"])
        if block.empty:
            continue
        vg = block["GateV"].to_numpy()
        runs.append(
            {
                "name": names.iloc[c].strip(),
                "VG": vg,
                "ID": block["DrainI"].to_numpy(),
                "IG": block["GateI"].to_numpy() if "GateI" in block else None,
                "VD": float(np.median(block["DrainV"])) if "DrainV" in block else float("nan"),
                "vg_max": float(np.max(vg)),
                "i_turn": int(np.argmax(vg)),
            }
        )
    if not runs:
        raise ValueError("no runs found (expected run names in row 2, headers in row 4)")
    runs.sort(key=lambda r: r["vg_max"])
    return runs


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------
# Tick labels: two points up from the 10 this script used, and bold. This is a
# deliberate override of the shared style, which ticks at 9 -- these panels are
# read one device at a time and carry four decades of current, so the numbers
# have to survive being shrunk into a figure.
TICK_SIZE = 16
TICK_WEIGHT = "bold"

# Axis labels a little above the shared 9 for the same reason.
LABEL_SIZE = 12


def apply_plot_style() -> None:
    """The read-disturb style, with this script's tick and label sizes on top.

    Taking _apply_style from read_disturb_plots rather than restating it means
    the grid, spines, font family, dpi and layout engine stay identical across
    the two figure sets; only the two sizes below diverge, and they say why.
    """
    _apply_style()
    plt.rcParams.update({
        "axes.labelsize": LABEL_SIZE,
        "axes.labelweight": "bold",
        "xtick.labelsize": TICK_SIZE,
        "ytick.labelsize": TICK_SIZE,
        # Closed box. The shared style drops the top and right spines, which
        # suits a panel whose curves end inside it; these traces run to the
        # top-right corner and need a frame to end against.
        "axes.spines.top": True,
        "axes.spines.right": True,
    })


def bold_ticks(ax) -> None:
    """Tick labels in TICK_WEIGHT, now and after every draw.

    matplotlib has no rcParam for tick-label weight, and the label objects are
    rebuilt whenever the locator runs -- which a log axis does on every
    autoscale -- so setting it once is not enough.
    """
    def _apply(_event=None) -> None:
        for lab in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
            lab.set_fontweight(TICK_WEIGHT)
            lab.set_fontsize(TICK_SIZE)

    _apply()
    if ax.figure is not None:
        ax.figure.canvas.mpl_connect("draw_event", _apply)


def sweep_colors(n: int) -> list:
    """Sequential single hue (light -> dark) because VG,max is a magnitude."""
    cmap = plt.get_cmap("Blues")
    if n == 1:  # a lone sweep gets the dark end, not the pale start
        return [cmap(0.85)]
    return [cmap(x) for x in np.linspace(0.40, 0.95, n)]


def draw_runs(ax, runs: list[dict], log: bool, show_ig: bool = False) -> None:
    colors = sweep_colors(len(runs))
    floor = Y_LIM_LOG[0] * 0.5
    for run, col in zip(runs, colors):
        vg, i_d, k = run["VG"], run["ID"], run["i_turn"]
        y = np.clip(np.abs(i_d), floor, None) if log else i_d * 1e6  # linear in µA
        ax.plot(vg[: k + 1], y[: k + 1], color=col, lw=1.5, ls="-")
        ax.plot(vg[k:], y[k:], color=col, lw=1.5, ls="--")
        if log and show_ig and run["IG"] is not None:
            ax.plot(vg, np.clip(np.abs(run["IG"]), floor, None), color=col, lw=0.6, alpha=0.35)
    if log:
        ax.set_yscale("log")
        ax.set_ylim(Y_LIM_LOG)


def sweep_legend_handles(runs: list[dict]) -> list:
    colors = sweep_colors(len(runs))
    handles = [
        Line2D([], [], color=c, lw=2, label=f"$V_{{G,max}}$ = +{r['vg_max']:g} V")
        for r, c in zip(runs, colors)
    ]
    handles += [
        Line2D([], [], color="0.3", lw=1.5, ls="-", label="forward"),
        Line2D([], [], color="0.3", lw=1.5, ls="--", label="reverse"),
    ]
    return handles


def select_runs(runs: list[dict], vg_max: tuple[float, ...] | None) -> list[dict]:
    """Keep only runs whose VG,max matches one of ``vg_max`` (within 10 mV)."""
    if vg_max is None:
        return runs
    return [r for r in runs if any(abs(r["vg_max"] - v) < 0.01 for v in vg_max)]


def plot_file(xlsx_path: Path, runs: list[dict], out_path: Path) -> None:
    """One log panel per file. The linear companion panel is no longer drawn.

    ``draw_runs(log=False)`` is kept -- it is what the linear panel used -- so
    restoring it is a matter of adding the axes back, not rewriting the drawing.
    """
    vd = runs[0]["VD"]
    fig, ax_log = plt.subplots(figsize=(5.8, 4.4), layout="constrained")

    draw_runs(ax_log, runs, log=True, show_ig=True)
    ax_log.set_ylabel(r"$|I_D|$ (A)")
    ax_log.set_xlabel(r"$V_G$ (V)")
    bold_ticks(ax_log)

    # No legend and no title. The device, V_D and the source file are printed
    # by main() for every figure it writes, and the sweep colours run light to
    # dark with V_G,max -- both belong in the caption now.
    print(f"    {out_path.name}: {build_title(xlsx_path.stem)}, "
          f"V_D = {vd:.2g} V, V_G,max = "
          + ", ".join(f"+{r['vg_max']:g}" for r in runs) + " V (light to dark)")
    fig.savefig(out_path, dpi=DPI, facecolor="white")
    plt.close(fig)


def plot_overview(all_runs: list[tuple[Path, list[dict]]], out_path: Path) -> None:
    n = len(all_runs)
    ncols = min(4, n)
    nrows = math.ceil(n / ncols)
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(3.6 * ncols, 3.1 * nrows + 0.6),
        sharex=True, sharey=True, layout="constrained", squeeze=False,
    )
    for ax, (path, runs) in zip(axes.flat, all_runs):
        draw_runs(ax, runs, log=True)
        bold_ticks(ax)
        parsed = parse_filename(path.stem)
        ax.set_title(
            f"{parsed[0]}/{parsed[1]}/{parsed[2]} µm, dev {parsed[3]}" if parsed else path.stem,
            fontsize=10,
        )
    for ax in axes.flat[n:]:
        ax.set_visible(False)
    for ax in axes[-1, :]:
        ax.set_xlabel(r"$V_G$ (V)")
    for ax in axes[:, 0]:
        ax.set_ylabel(r"$|I_D|$ (A)")
    # The per-panel W/L/Overlap titles stay: without them a grid of a dozen
    # look-alike panels cannot be told apart. The figure-level title and the
    # legend go, like on the single-device figures.
    fig.savefig(out_path, dpi=DPI, facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", nargs="?", default=str(DEFAULT_FOLDER))
    ap.add_argument(
        "--vgmax", type=float, nargs="+", default=None,
        help="VG,max values (V) to plot, e.g. --vgmax 5 or --vgmax 3 5 "
             f"(default: {VG_MAX_SELECT})",
    )
    ap.add_argument("--all", action="store_true", help="plot every sweep")
    args = ap.parse_args()
    vg_select = None if args.all else (tuple(args.vgmax) if args.vgmax else VG_MAX_SELECT)

    folder = Path(args.folder)
    if not folder.is_absolute():
        folder = (ROOT / folder).resolve()
    files = sorted(p for p in folder.glob("*.xlsx") if not p.name.startswith("~$"))
    if not files:
        sys.exit(f"No .xlsx files found in {folder}")

    apply_plot_style()
    sel_txt = "all" if vg_select is None else ", ".join(f"+{v:g}" for v in vg_select)
    print(f"Processing {len(files)} file(s) in {folder}  (VG,max = {sel_txt} V)")
    all_runs = []
    for path in files:
        try:
            runs = select_runs(read_runs(path), vg_select)
            if not runs:
                print(f"  SKIP: {path.name} has no sweep with VG,max = {sel_txt} V")
                continue
            out = folder / f"{path.stem}_TR.png"
            plot_file(path, runs, out)
            all_runs.append((path, runs))
            vmax = ", ".join(f"+{r['vg_max']:g}" for r in runs)
            print(f"  {path.name}: {len(runs)} sweeps (VG,max = {vmax} V) -> {out.name}")
        except Exception as exc:  # keep going on bad files
            print(f"  WARNING: {path.name} failed: {exc}")

    if all_runs:
        ov = folder / f"TR_overview_{folder.name}.png"
        plot_overview(all_runs, ov)
        print(f"  overview -> {ov.name}")
    print(f"Done: {len(all_runs)}/{len(files)} files plotted.")


if __name__ == "__main__":
    main()
