#!/usr/bin/env python3
"""FeFET complementary-pair read-disturb analysis and figures.

    python read_disturb_plots.py [workbook.xlsx]

Reads the supplementary workbook, reconstructs read-disturb blocks from raw
probe data, computes an additivity (pedestal vs Vth-shift) metric, and writes
two figures plus ``out/blocks_derived.csv``.
"""
from __future__ import annotations

import re
import sys
import traceback
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_XLSX = Path(__file__).resolve().parent / (
    "FeFET_read_disturb_supplementary_20260901.xlsx"
)
OUTDIR = Path(__file__).resolve().parent / "out"

CHIP3_RUN = "chip3_0828_1751"
EXEMPLAR_RUN = "chip6_0831_1337"
EXEMPLAR_PHASE = "rung1_C-0.75"
WRITE_PULSE_RUN = "chip6_0831_1150"
REPRO_MV = 9.5
N_GRID = 25
RMS_FLAG = 10.0

# ---------------------------------------------------------------------------
# Extended single-target runs, measured out to 10^9 read cycles
# ---------------------------------------------------------------------------
# The supplementary workbook stops at 10^3 cycles and only covers stored values
# within about +-0.3 V of zero, so every statement past 10^3 had to come from a
# decade extrapolation. The 2026-09-11 campaign replaces that: five isolated
# single-target runs, each closed-loop moved to its own notch and then stressed
# in place to 10^9 read cycles, spanning -1.95 V to +0.45 V of stored value.
# Nothing beyond 10^3 is extrapolated any more.
#
# Only the clean runs are read. The overnight sequential run (chip6_0910_2311)
# is deliberately left out: its targets were not reached (0.0 V and +0.5 V
# saturate), so the BASE positions differ, and the cell carries the accumulated
# history of the earlier targets, which inflates |dw| by 3-9x. It is a trend
# observation, not a quantitative comparison, and mixing it in would be wrong.
EXTENDED_XLSX = Path(__file__).resolve().parent / (
    "FeFET_read_disturb_1e9_20260911.xlsx"
)
EXT_SUMMARY_SHEET = "클린런_요약"
EXT_CURVES_SHEET = "raw_클린곡선"
EXT_HEADER_ROW = 2              # two title rows sit above the header
EXT_COL_BASE = "착지 w = BASE (V)"     # summary: the notch the move landed on
EXT_COL_DW = "Δw@10^9 (mV)"            # summary: drift at the last checkpoint
EXT_ROUNDING_MV = 0.25          # notch_v is stored to 0.1 mV; see load_extended
EXT_EXCLUDED_RUN = "chip6_0910_2311"
EXT_MAX_CYCLES = 1e9
# A run only enters the figures if its checkpoints start at the first cycle.
# chip6_0910_1541 (target -1.0 V) was resumed at 10^6 with its BASE taken at
# 10^5, so its first eight decades were never measured: its drift-per-decade
# rests on four points and the missing span cannot be read off the trace.
# Everything it recorded stays in out/extended_1e9_checkpoints.csv, flagged.
EXT_FIRST_CYCLE = 1.0
C_EXT = "#117733"               # the 10^9 single-target series

# The stored-value ladder a read disturbance has to be judged against. Fill
# LADDER_NOTCHES_V with the 25 fitted notch positions of the programmed-state
# ladder (Supplementary Fig. S3); the spacing is not uniform, so the margin is
# set by the smallest gap and cannot be recovered from a span and a count.
LADDER_NOTCHES_V: list[float] | None = None

# Nominal design pitch, used only as a faint secondary reference (context);
# the primary decision boundary is now the calibrated-simulation tolerance below.
NOMINAL_LADDER_SPAN_V = 1.31
NOMINAL_N_STATES = 25
LEVEL_SPACING_MV = NOMINAL_LADDER_SPAN_V / (NOMINAL_N_STATES - 1) * 1000.0

# ---------------------------------------------------------------------------
# System-level tolerance from the calibrated retrieval simulation.
#
# A stored-value drift matters only if it changes what the RAG retriever
# returns. The FeFET array holds the IVF centroids (static tier); a per-cell
# systematic V_W offset was swept in the calibrated simulator (1000 HotpotQA
# queries, nprobe 32, full-scale 1.31 V) and every retrieval metric was tracked
# vs the ideal (unperturbed) output. The offset at which each metric first loses
# 1 % relative to its zero-drift baseline:
#
#     Kendall tau (rank self-consistency, strictest)   ~ 23 mV   <- primary
#     top-5 set Jaccard                                 ~ 43 mV
#     recall@5 / nDCG@10 / full-support@5 (gold)        ~ 105-120 mV
#
# Two bounds are drawn:
#   STRICT  = Kendall tau -1%  (~23 mV): the returned ranking starts to deviate
#             from the ideal, before any gold-relevance metric moves.
#   LENIENT = recall@5 -1%    (~110 mV): the answer the pipeline actually returns
#             (which gold passages reach the top-5) starts to change.
# A read disturbance below STRICT changes nothing; below LENIENT the delivered
# retrieval result is unchanged even if the internal ordering wobbles.
#
# UNRECONCILED, 2026-09-20. The two numbers above were checked against the
# analysis repo and neither could be traced to an artefact there:
#
#   source                                        Kendall tau   top-5 Jaccard
#   this header                                      ~23 mV         ~43 mV
#   figures/fig2/fig2_precision_bits.csv              3.22 mV       16.48 mV
#     (static tier, exact, per-cell Gaussian sigma on V_W, FS 1.3106 V)
#   sweep_exports/tol_run/out/tol_sweep_fs1p31...     no tau         ~2 mV
#     (cell_sigma axis; the offset axis gives ~3 mV)
#
# The full scale is the same 1.3106 V in all three, so this is not the Fig. 2c
# full-scale error -- it is a different, unexplained discrepancy. What does
# check out is the lenient bound: fig2 puts recall@5 -1% at 107.6 mV, inside
# the 105-120 mV quoted above. tol_crossings_fs1p31_vml1p4.json carries no
# Kendall tau at all and reports NaN for almost every -1% crossing, so it
# cannot be the source of the 23 mV either.
#
# The constants are LEFT AS THEY WERE on purpose. Moving STRICT from 23 mV to
# ~3 mV would redraw the strict bound on every read-disturb figure and could
# flip measured blocks from pass to fail, which is not a change to make from a
# provenance gap. Either the sweep behind the 23 mV has to be found, or the
# bound has to be restated from fig2_precision_bits.csv deliberately.
TOLERANCE_MV_STRICT = 23.0
TOLERANCE_MV_LENIENT = 110.0
# The gutter labels on the tolerance lines were sized to sit inside a crowded
# panel next to a second (strict) line. With that line gone they are the only
# annotation on the axis and were too small to read at print size, so every
# one of them is raised by this much. One knob, because they have to stay
# legible together.
TOL_LABEL_BUMP = 3.0
# No longer drawn on any panel -- the strict bound was removed from the
# figures. Kept so that restoring the line does not mean re-deriving its
# label, and because the console still reports measured drift as a
# percentage of it.
TOLERANCE_STRICT_LABEL = r"Kendall $\tau$ $-$1% (sim)"
TOLERANCE_LENIENT_LABEL = r"recall@5 $-$1% (sim)"

# Blocks whose relaxation is separated from the read stress: the paired blocks
# and the no-write control. Everything else shares the two effects.
RELAX_COL = "완화 분리"
RELAX_SEP_VALUES = ("짝 블록", "무쓰기 대조")

CHIP_COLOR = {
    "chip3": "#0072B2",
    "chip4": "#E69F00",
    "chip5": "#009E73",
    "chip6": "#CC79A7",
}
ORDER_MARKER = {1: "o", 2: "s", 3: "^"}
C_FLOOR = "#0072B2"
C_NOTCH = "#D55E00"
KIND_VRANGE = ("BASE", "BASE2", "CYC")
C_ZERO_BADGE = "#D55E00"
V_PAD = 0.05


# Tick labels: weight and size, applied to the panel axes and to the colourbar
# through _bold_ticks. matplotlib has no rcParam for tick-label weight, so it
# has to be set on the label objects themselves.
TICK_WEIGHT = "bold"
TICK_SIZE = 9


def _apply_style() -> None:
    plt.rcParams.update({
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "legend.fontsize": 8,
        "xtick.labelsize": TICK_SIZE,
        "ytick.labelsize": TICK_SIZE,
        "savefig.dpi": 300,
        "figure.constrained_layout.use": True,
        "axes.grid": True,
        "grid.linestyle": "--",
        "grid.alpha": 0.35,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "axes.unicode_minus": True,
    })


# Reference-line labels used to sit in empty space. With the 10^9 runs the
# traces cross the whole panel, so the labels ride on a translucent patch
# instead of being pushed somewhere they no longer describe.
LABEL_BBOX = dict(facecolor="white", alpha=0.72, edgecolor="none",
                  boxstyle="square,pad=0.15")



def _save_colorbar(norm, cmap, label: str, stem: Path, *,
                   size=(2.8, 0.95)) -> None:
    """Write the colour key on its own, so the panel keeps its whole area.

    Inside the figure the bar has to borrow either width or height from the
    axes, which makes the panel proportions depend on whether a key is drawn.
    On its own it can be placed and scaled in the layout instead.
    """
    # layout="none": the bar is placed by hand with add_axes, and the shared
    # constrained-layout setting has no gridspec to work with here.
    fig = plt.figure(figsize=size)
    fig.set_layout_engine("none")
    # The ticks and the label both sit under a horizontal bar, so the bar is
    # placed high and the space below it is left for them.
    cax = fig.add_axes([0.04, 0.60, 0.92, 0.22])
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cbar = fig.colorbar(sm, cax=cax, orientation="horizontal")
    cbar.set_label(label, fontsize=10, fontweight="bold")
    cbar.ax.tick_params(labelsize=TICK_SIZE - 1, length=2, pad=1)
    cbar.ax.grid(False)        # axes.grid is on globally; not on a colour ramp
    _bold_ticks(cbar.ax)
    for ext in (".png", ".svg"):
        out = stem.with_name(stem.name + ext)
        _savefig(fig, out, dpi=300) if ext == ".png" else _savefig(fig, out)
        print(f"  wrote {out}")
    plt.close(fig)


def _savefig(fig: plt.Figure, path: Path, **kwargs) -> Path:
    """Write a figure, and do not lose the run if the target is locked.

    Writing to a path under /mnt/c from WSL fails with EINVAL (errno 22), not
    EACCES, when the file is already open in a Windows process -- an image
    viewer or an editor preview is enough. That used to abort the whole run
    several figures in. The fallback writes "<stem>_new" beside it and says so,
    so the figure still gets made and the stale one is obvious.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fig.savefig(path, **kwargs)
        return path
    except OSError as exc:
        alt = path.with_name(f"{path.stem}_new{path.suffix}")
        fig.savefig(alt, **kwargs)
        print(f"  [warn] could not write {path.name} ({exc.strerror}); "
              f"wrote {alt.name} instead -- close whatever has the file open")
        return alt


def _bold_ticks(ax: plt.Axes) -> None:
    """Set the tick-label weight and size on one axes, now and after each draw.

    Tick label objects are rebuilt whenever the locator runs, so setting the
    weight once is not enough on an axes that autoscales or is rescaled later --
    hence the draw-time callback as well as the immediate pass.
    """
    def _apply(_event=None) -> None:
        for lab in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
            lab.set_fontweight(TICK_WEIGHT)
            lab.set_fontsize(TICK_SIZE)

    _apply()
    if ax.figure is not None:
        ax.figure.canvas.mpl_connect("draw_event", _apply)


def _bold_decade_ticks(ax: plt.Axes, ticks, labels) -> None:
    r"""Set x ticks whose labels are all bold, mixed plain/exponent included.

    ``fontweight="bold"`` styles plain tick strings but never mathtext, so a
    list like ["1", "10", "$10^3$"] renders the first two bold and the rest
    regular. Wrapping every label in \mathbf puts them all through mathtext,
    which is the only way they come out in one weight.
    """
    ax.set_xticks(ticks)
    ax.set_xticklabels([r"$\mathbf{%s}$" % s for s in labels])
    ax.minorticks_off()


def _hide_top_right(ax: plt.Axes, *, keep_right: bool = False) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(keep_right)
    _bold_ticks(ax)


def _block_order_from_phase(phase: str, fallback: int) -> int:
    m = re.search(r"_b(\d+)_", str(phase))
    return int(m.group(1)) if m else int(fallback)


def _split_cyc_blocks(cyc: pd.DataFrame) -> list[pd.DataFrame]:
    """Split CYC rows (already sorted by seq) wherever cyc_total decreases."""
    blocks: list[list] = []
    cur: list = []
    prev = None
    for _, row in cyc.iterrows():
        if prev is not None and row["cyc_total"] < prev:
            blocks.append(cur)
            cur = []
        cur.append(row)
        prev = row["cyc_total"]
    if cur:
        blocks.append(cur)
    return [pd.DataFrame(b) for b in blocks]


def _common_grid(v0, y0, v1, y1, n: int = N_GRID):
    v0 = np.asarray(v0, float)
    y0 = np.asarray(y0, float)
    v1 = np.asarray(v1, float)
    y1 = np.asarray(y1, float)
    o0 = np.argsort(v0)
    o1 = np.argsort(v1)
    v0, y0 = v0[o0], y0[o0]
    v1, y1 = v1[o1], y1[o1]
    lo = max(float(v0.min()), float(v1.min()))
    hi = min(float(v0.max()), float(v1.max()))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        raise AssertionError(f"no overlapping v range: [{lo}, {hi}]")
    vv = np.linspace(lo, hi, n)
    return vv, np.interp(vv, v0, y0), np.interp(vv, v1, y1)


def _ols_dc_on_y0(y0: np.ndarray, dc: np.ndarray) -> tuple[float, float]:
    A = np.column_stack([np.ones_like(y0), y0])
    coef, *_ = np.linalg.lstsq(A, dc, rcond=None)
    return float(coef[0]), float(coef[1])


def _pearson(x, y) -> float:
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    if len(x) < 2 or np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def _sanitize_phase(phase: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", str(phase))


def _block_stem(block) -> str:
    return f"{block['run']}__{_sanitize_phase(block['phase'])}__blk{int(block['block_order'])}"


def _r2(x, y) -> float:
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 3:
        return float("nan")
    xx, yy = x[m], y[m]
    ss_tot = float(np.sum((yy - yy.mean()) ** 2))
    if ss_tot <= 0:
        return float("nan")
    slope, intercept = np.polyfit(xx, yy, 1)
    pred = intercept + slope * xx
    ss_res = float(np.sum((yy - pred) ** 2))
    return 1.0 - ss_res / ss_tot


def _refit_quadratic(v, y) -> tuple[float, float]:
    v = np.asarray(v, float)
    y = np.asarray(y, float)
    m = np.isfinite(v) & np.isfinite(y)
    if m.sum() < 5:
        return float("nan"), float("nan")
    a, b, c = np.polyfit(v[m], y[m], 2)
    if not np.isfinite(a) or a == 0:
        return float("nan"), float("nan")
    notch = -b / (2.0 * a)
    floor = c - b * b / (4.0 * a)
    return float(notch), float(floor)


def _curve(curves: pd.DataFrame, run: str, seq: int) -> pd.DataFrame:
    g = curves[(curves["런"] == run) & (curves["seq"] == seq)].copy()
    if g.empty:
        raise AssertionError(f"no curve points for run={run!r} seq={seq}")
    return g.sort_values("v")


# ---------------------------------------------------------------------------
# Load / reconstruct / additivity
# ---------------------------------------------------------------------------
def load(path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not path.is_file():
        raise FileNotFoundError(path)
    probe = pd.read_excel(path, sheet_name="프로브원본")
    curves = pd.read_excel(path, sheet_name="곡선원본")
    summary = pd.read_excel(path, sheet_name="블록전체").iloc[:28].copy()
    summary = summary[summary["런"].notna()].copy()
    if RELAX_COL not in summary.columns:
        raise AssertionError(
            f"블록전체 has no {RELAX_COL!r} column; columns are "
            f"{list(summary.columns)}"
        )
    drop = [c for c in ("vth_a", "vth_b", "common_mode", "differential", "a_S", "b_S")
            if c in probe.columns]
    if drop:
        probe = probe.drop(columns=drop)
    return probe, curves, summary


def build_blocks(probe: pd.DataFrame, summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    grouped = probe[probe["kind"].isin(["BASE2", "CYC"])].groupby(["런", "phase"], sort=False)
    for (run, phase), g in grouped:
        g = g.sort_values("seq")
        cyc = g[g["kind"] == "CYC"]
        base2 = g[g["kind"] == "BASE2"].reset_index(drop=True)
        cyc_blocks = _split_cyc_blocks(cyc)
        chip = g["칩"].iloc[0]
        for i, blk in enumerate(cyc_blocks):
            last = blk.iloc[-1]
            if len(base2):
                base = base2.iloc[min(i, len(base2) - 1)]
                has_base2 = True
            else:
                bg = probe[
                    (probe["런"] == run) & (probe["phase"] == phase) & (probe["kind"] == "BASE")
                ].sort_values("seq")
                if bg.empty:
                    raise AssertionError(
                        f"{run} / {phase}: no BASE2 and no BASE to pair with CYC block {i + 1}"
                    )
                base = bg.iloc[min(i, len(bg) - 1)]
                has_base2 = False
            F0 = float(base["floor_per_ms"])
            F1 = float(last["floor_per_ms"])
            a0 = float(base["curv_per_ms"])
            a1 = float(last["curv_per_ms"])
            w0 = float(base["notch_v"])
            w1 = float(last["notch_v"])
            rms_vals = np.concatenate([
                np.asarray(blk["fit_rms"], float),
                [float(base["fit_rms"])],
            ])
            rows.append(dict(
                chip=chip,
                run=run,
                phase=phase,
                block_order=_block_order_from_phase(phase, i + 1),
                C=float(base["center_v"]),
                w0=w0,
                w1=w1,
                dw_mV=(w1 - w0) * 1000.0,
                F0=F0,
                F1=F1,
                dF_pct=(F1 / F0 - 1.0) * 100.0 if F0 else np.nan,
                da_pct=(a1 / a0 - 1.0) * 100.0 if a0 else np.nan,
                n_cycles=int(last["cyc_total"]),
                seq_base=int(base["seq"]),
                seq_last=int(last["seq"]),
                rms_max=float(np.nanmax(rms_vals)),
                has_base2=has_base2,
                integ_ms_base=float(base["integ_ms"]),
                integ_ms_last=float(last["integ_ms"]),
            ))
    blocks = pd.DataFrame(rows)
    if len(blocks) != 28:
        raise AssertionError(f"expected 28 reconstructed blocks, got {len(blocks)}")

    dw_col, df_col = "Δw [mV]", "ΔF [%]"
    blocks["relax_sep"] = False
    used: set[int] = set()
    chip3_notes = []
    for _, srow in summary.iterrows():
        run = srow["런"]
        cand_idx = [
            j for j, r in blocks.iterrows()
            if r.run == run
            and np.isclose(r.C, float(srow["C [V]"]))
            and int(r.n_cycles) == int(srow["사이클"])
            and j not in used
        ]
        if not cand_idx:
            raise AssertionError(
                f"no reconstructed block for sheet row run={run} "
                f"C={srow['C [V]']} n={srow['사이클']}"
            )
        sub = blocks.loc[cand_idx]
        j = int((sub.w1 - float(srow["w1 [V]"])).abs().idxmin())
        used.add(j)
        blocks.at[j, "relax_sep"] = str(srow.get(RELAX_COL, "")).strip() in \
            RELAX_SEP_VALUES
        rec = blocks.loc[j]
        dw_err = abs(rec.dw_mV - float(srow[dw_col]))
        df_err = abs(rec.dF_pct - float(srow[df_col]))
        if run == CHIP3_RUN:
            chip3_notes.append(
                f"  {rec.phase}: reconstructed dw={rec.dw_mV:.1f} mV  dF={rec.dF_pct:.3f}%  "
                f"vs sheet {float(srow[dw_col]):.1f} mV / {float(srow[df_col]):.3f}%  "
                f"(Δdw={dw_err:.1f} mV, ΔdF={df_err:.3f}%)"
            )
            continue
        if dw_err > 0.1 or df_err > 0.01:
            raise AssertionError(
                f"{run} / {rec.phase}: reconstruction disagrees with 블록전체 "
                f"(dw {rec.dw_mV:.3f} vs {float(srow[dw_col]):.3f} mV, "
                f"dF {rec.dF_pct:.4f} vs {float(srow[df_col]):.4f} %)"
            )

    print("Reconstruction: 28 blocks.")
    print(
        f"chip3 ({CHIP3_RUN}) has no BASE2; baseline is the BASE probe, "
        "not the cyc_total=10 surrogate used in 블록전체. Discrepancies:"
    )
    for line in chip3_notes:
        print(line)

    blocks["flag_chip5"] = (blocks["chip"] == "chip5") & (blocks["rms_max"] > RMS_FLAG)
    blocks["flag_write"] = blocks["run"] == WRITE_PULSE_RUN
    blocks["flagged"] = blocks["flag_chip5"] | blocks["flag_write"]
    return blocks


def additivity(blocks: pd.DataFrame, curves: pd.DataFrame) -> pd.DataFrame:
    records = []
    integ_notes = []
    for _, rec in blocks.iterrows():
        c0 = _curve(curves, rec.run, rec.seq_base)
        c1 = _curve(curves, rec.run, rec.seq_last)
        integ0 = float(c0["integ_ms"].iloc[0])
        integ1 = float(c1["integ_ms"].iloc[0])
        y_raw0 = c0["code"].to_numpy(float)
        y_raw1 = c1["code"].to_numpy(float)
        if not np.isclose(integ0, integ1):
            y_raw0 = y_raw0 / integ0
            y_raw1 = y_raw1 / integ1
            integ_notes.append(
                f"  {rec.run} / {rec.phase}: integ_ms {integ0:g} vs {integ1:g} "
                "— divided code by integ_ms before Δcode"
            )
        vv, y0, y1 = _common_grid(c0["v"], y_raw0, c1["v"], y_raw1)
        dc = y1 - y0
        a, b = _ols_dc_on_y0(y0, dc)
        # Signed multiplicative null: dc ≈ k y0 with k = mean(dc)/mean(y0).
        # (The leading minus in the task note would flip the expected sign.)
        b_mult = float(dc.mean() / y0.mean()) if y0.mean() else np.nan
        ratio = float(b / b_mult) if b_mult else np.nan
        records.append(dict(
            dc_mean=float(dc.mean()),
            dc_std=float(dc.std(ddof=0)),
            a=a,
            b=b,
            b_mult=b_mult,
            ratio=ratio,
            y0_mean=float(y0.mean()),
            y0_span_frac=float((y0.max() - y0.min()) / y0.mean()) if y0.mean() else np.nan,
        ))
    out = pd.concat([blocks.reset_index(drop=True), pd.DataFrame(records)], axis=1)
    if integ_notes:
        print("integ_ms mismatch (normalized to code/ms):")
        for line in integ_notes:
            print(line)
    return out


# ---------------------------------------------------------------------------
# Extended runs: load / reconstruct
# ---------------------------------------------------------------------------
def load_extended(path: Path = EXTENDED_XLSX) -> pd.DataFrame | None:
    """Checkpoint-level drift for the clean 10^9-cycle single-target runs.

    One row per read-cycle checkpoint, with the run tag, the target the notch
    was moved to, ``w0`` (the BASE notch it actually landed on), the cycle
    count, the notch drift in mV and the common-mode floor. ``dw_mV`` is
    recomputed from the notch positions rather than taken from the sheet, and
    checked against the sheet's own column, so a reordered or edited workbook
    cannot slip through.

    Returns None when the workbook is not next to the script; the figures then
    fall back to the decade extrapolation they used before the campaign.
    """
    if not path.is_file():
        print(f"\n*** NOTE: {path.name} is not next to the script. The 10^9 "
              "single-target runs are not plotted and the drift past 10^3 "
              "cycles is extrapolated, as before.")
        return None

    raw = pd.read_excel(path, sheet_name=EXT_CURVES_SHEET, header=EXT_HEADER_ROW)
    raw = raw[raw["run_tag"].notna()].copy()
    if (raw["run_tag"] == EXT_EXCLUDED_RUN).any():
        raise AssertionError(
            f"{EXT_CURVES_SHEET} contains the sequential run {EXT_EXCLUDED_RUN}; "
            "its targets were missed and its history is cumulative, so it is not "
            "quantitatively comparable and must not enter the figures"
        )

    rows = []
    for (run, target), g in raw.groupby(["run_tag", "target_v"], sort=False):
        g = g.sort_values("cyc_total")
        base = g[g["kind"] == "BASE"]
        if len(base) != 1:
            raise AssertionError(
                f"{run} / target {target}: expected exactly one BASE row, "
                f"found {len(base)}"
            )
        base = base.iloc[0]
        w0 = float(base["notch_v"])
        F0 = float(base["floor_code"])
        cyc_rows = g[g["kind"] == "CYC"]
        if cyc_rows.empty:
            raise AssertionError(f"{run} / target {target}: no CYC checkpoints")
        for _, r in cyc_rows.iterrows():
            dw = (float(r["notch_v"]) - w0) * 1000.0
            sheet_dw = float(r["d_notch_mV"])
            # notch_v is stored rounded to 0.1 mV, so the recomputed difference
            # can sit up to 0.2 mV off the sheet's full-precision column. A
            # larger gap means the two columns are not the same measurement.
            if abs(dw - sheet_dw) > EXT_ROUNDING_MV:
                raise AssertionError(
                    f"{run} @ {int(r['cyc_total'])} cycles: recomputed "
                    f"dw = {dw:.3f} mV disagrees with the sheet's "
                    f"{sheet_dw:.3f} mV"
                )
            rows.append(dict(
                run=run,
                target_v=float(target),
                w0=w0,
                cyc=float(r["cyc_total"]),
                dwell_s=float(r["dwell_total_s"]),
                notch_v=float(r["notch_v"]),
                dw_mV=dw,
                floor_code=float(r["floor_code"]),
                F0=F0,
                dF_pct=(float(r["floor_code"]) / F0 - 1.0) * 100.0 if F0 else np.nan,
                curvature=float(r["curvature"]),
            ))
    ext = pd.DataFrame(rows)

    # Cross-check the endpoint of every run against the summary sheet.
    summ = pd.read_excel(path, sheet_name=EXT_SUMMARY_SHEET, header=EXT_HEADER_ROW)
    # The sheet carries a trailing footnote row in the run_tag column.
    summ = summ[summ["run_tag"].astype(str).str.match(r"^chip\d", na=False)]
    if summ.empty:
        raise AssertionError(f"{EXT_SUMMARY_SHEET} has no run rows")
    col_base, col_dw = EXT_COL_BASE, EXT_COL_DW
    for c in (col_base, col_dw, "cyc_max"):
        if c not in summ.columns:
            raise AssertionError(
                f"{EXT_SUMMARY_SHEET} has no {c!r} column; columns are "
                f"{list(summ.columns)}"
            )
    for _, s in summ.iterrows():
        tag = str(s["run_tag"])
        g = ext[ext["run"] == tag]
        if g.empty:
            raise AssertionError(f"summary run {tag} has no raw curve rows")
        last = g.sort_values("cyc").iloc[-1]
        w0_sheet = float(s[col_base])
        dw_sheet = float(s[col_dw])
        if abs(float(last["w0"]) - w0_sheet) > 1e-4:
            raise AssertionError(
                f"{tag}: BASE notch {float(last['w0']):.4f} V disagrees with "
                f"the summary sheet's {w0_sheet:.4f} V"
            )
        if abs(float(last["dw_mV"]) - dw_sheet) > EXT_ROUNDING_MV:
            raise AssertionError(
                f"{tag}: final dw {float(last['dw_mV']):.1f} mV disagrees with "
                f"the summary sheet's {dw_sheet:.1f} mV"
            )
        if float(last["cyc"]) != float(s["cyc_max"]):
            raise AssertionError(
                f"{tag}: last checkpoint {float(last['cyc']):g} != "
                f"cyc_max {float(s['cyc_max']):g}"
            )

    n_runs = ext["run"].nunique()
    print(f"\nExtended runs: {n_runs} clean single-target runs, "
          f"{len(ext)} checkpoints, stored value "
          f"{ext['w0'].min():+.3f} .. {ext['w0'].max():+.3f} V, "
          f"cycles up to {ext['cyc'].max():.0g}.")
    print(f"  sequential run {EXT_EXCLUDED_RUN} excluded by design "
          "(targets missed, cumulative history).")
    return ext


def extended_tracks(ext: pd.DataFrame) -> list[dict]:
    """One track per clean run, ordered by stored value.

    ``slope`` is the drift per decade of read cycles over the measured range --
    a real fit now, not an extrapolation.

    A run whose checkpoints do not start at the first cycle is left out
    entirely (see EXT_FIRST_CYCLE): the decades it skipped are missing data,
    and a trace drawn across them would invent a shape for that span.
    """
    tracks = []
    dropped = []
    for run, g in ext.groupby("run", sort=False):
        g = g.sort_values("cyc")
        if float(g["cyc"].min()) > EXT_FIRST_CYCLE:
            dropped.append((run, float(g["cyc"].min()), float(g["w0"].iloc[0])))
            continue
        cyc = g["cyc"].to_numpy(float)
        dw = g["dw_mV"].to_numpy(float)
        m = np.isfinite(dw) & (cyc >= 1)
        slope = np.nan
        if m.sum() >= 2:
            slope = float(np.polyfit(np.log10(cyc[m]), dw[m], 1)[0])
        tracks.append(dict(
            run=run,
            target_v=float(g["target_v"].iloc[0]),
            w0=float(g["w0"].iloc[0]),
            cyc=cyc,
            x=cyc,
            dw=dw,
            dF=g["dF_pct"].to_numpy(float),
            dw_final=float(dw[-1]),
            dF_final=float(g["dF_pct"].to_numpy(float)[-1]),
            cyc_final=float(cyc[-1]),
            slope=slope,
        ))
    for run, first, w0 in dropped:
        print(f"  {run} (V_W = {w0:+.3f} V) left out of the figures: "
              f"checkpoints start at {first:g} cycles, not {EXT_FIRST_CYCLE:g}")
    if not tracks:
        raise AssertionError(
            "every extended run was dropped for starting past "
            f"{EXT_FIRST_CYCLE:g} cycles"
        )
    return sorted(tracks, key=lambda t: t["w0"])


def _print_extended(tracks: list[dict]) -> None:
    """The headline the wide-range campaign actually supports."""
    if not tracks:
        return
    print("\nRead disturb at 10^9 cycles, by stored value:")
    for t in tracks:
        frac = 100.0 * abs(t["dw_final"]) / TOLERANCE_MV_LENIENT
        print(f"  V_W = {t['w0']:+.3f} V (target {t['target_v']:+.1f}):  "
              f"dw@1e9 = {t['dw_final']:+7.1f} mV  "
              f"({frac:3.0f} % of the lenient bound, "
              f"{100.0 * abs(t['dw_final']) / TOLERANCE_MV_STRICT:4.0f} % of strict)  "
              f"slope {t['slope']:+.1f} mV/decade")
    deep = [t for t in tracks if t["w0"] <= -0.4]
    if deep:
        worst = max(abs(t["dw_final"]) for t in deep)
        print(f"  deep states (V_W <= -0.4 V): |dw@1e9| <= {worst:.0f} mV, "
              f"inside the strict bound ({TOLERANCE_MV_STRICT:.0f} mV)."
              if worst <= TOLERANCE_MV_STRICT else
              f"  deep states (V_W <= -0.4 V): |dw@1e9| <= {worst:.0f} mV.")
    over = [t for t in tracks if abs(t["dw_final"]) > TOLERANCE_MV_LENIENT]
    for t in over:
        print(f"  *** V_W = {t['w0']:+.3f} V exceeds the lenient bound at 10^9 "
              f"({t['dw_final']:+.0f} mV vs {TOLERANCE_MV_LENIENT:.0f} mV). The "
              "read-disturb claim holds for the deep half of the range, not the "
              "whole ladder -- say so in the caption.")


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------
V_LABEL = r"Differential offset  $v = (V_A - V_B)/2$  [V]"
V_NOTE = r"$V_A = C + v,\ \ V_B = C - v$"


def shared_v_xlim(probes: pd.DataFrame, curves: pd.DataFrame) -> tuple[float, float]:
    """Union of v over BASE / BASE2 / CYC sweeps only, padded by 0.05 V."""
    kinds = probes[["런", "seq", "kind"]].drop_duplicates()
    merged = curves.merge(kinds, on=["런", "seq"], how="left")
    sub = merged[merged["kind"].isin(KIND_VRANGE)]
    if sub.empty:
        raise AssertionError("no BASE/BASE2/CYC curves to set the shared v axis")
    vmin = float(np.nanmin(sub["v"]))
    vmax = float(np.nanmax(sub["v"]))
    return vmin - V_PAD, vmax + V_PAD


def _code_at_notch(sweep: dict, w0: float) -> float:
    v = np.asarray(sweep["v"], float)
    y = np.asarray(sweep["y"], float)
    m = np.isfinite(v) & np.isfinite(y)
    if m.sum() >= 2:
        order = np.argsort(v[m])
        val = float(np.interp(w0, v[m][order], y[m][order]))
        if np.isfinite(val) and val != 0:
            return val
    fy = sweep.get("floor_y", np.nan)
    return float(fy) if np.isfinite(fy) and fy != 0 else float("nan")


def _draw_shared_v_refs(ax, w0: float, all_w0, *, rug: bool) -> None:
    ax.axvline(0.0, color="0.45", ls=":", lw=1.0, zorder=1)
    ax.axvline(w0, color="0.15", ls="--", lw=1.0, zorder=1)
    ax.annotate(
        f"$w_0$ = {w0:+.3f} V",
        xy=(w0, 1.0), xycoords=("data", "axes fraction"),
        xytext=(4, -4), textcoords="offset points",
        ha="left", va="top", fontsize=7, color="0.15",
    )
    if not rug:
        return
    ylo, yhi = ax.get_ylim()
    h = 0.045 * (yhi - ylo)
    w0s = np.asarray(all_w0, float)
    w0s = w0s[np.isfinite(w0s)]
    ax.vlines(w0s, ylo, ylo + h, colors="0.72", lw=0.8, zorder=5, clip_on=False)
    if np.isfinite(w0):
        ax.vlines([w0], ylo, ylo + 1.6 * h, colors="k", lw=1.6, zorder=6, clip_on=False)
    ax.set_ylim(ylo, yhi)


def _mark_c0_figure(fig, ax_a) -> None:
    fig.patch.set_edgecolor(C_ZERO_BADGE)
    fig.patch.set_linewidth(3.0)
    ax_a.text(
        0.98, 0.97, "C = 0",
        transform=ax_a.transAxes, ha="right", va="top",
        fontsize=9, fontweight="bold", color="white",
        bbox=dict(boxstyle="round,pad=0.28", facecolor=C_ZERO_BADGE, edgecolor="none"),
        zorder=10,
    )


def _collect_block_sweeps(block, probes: pd.DataFrame, curves: pd.DataFrame):
    """Return list of sweep dicts sorted by seq, plus notes."""
    run, phase = block["run"], block["phase"]
    seq0, seq1 = int(block["seq_base"]), int(block["seq_last"])
    kinds = ["BASE2", "CYC"] if bool(block["has_base2"]) else ["BASE", "CYC"]
    pr = probes[
        (probes["런"] == run)
        & (probes["phase"] == phase)
        & (probes["kind"].isin(kinds))
        & (probes["seq"] >= seq0)
        & (probes["seq"] <= seq1)
    ].sort_values("seq")

    phase_curves = curves[(curves["런"] == run) & (curves["phase"] == phase)]
    probe_seqs_phase = set(
        probes[(probes["런"] == run) & (probes["phase"] == phase)]["seq"].astype(int)
    )
    last_pr_seq = int(pr["seq"].max()) if len(pr) else seq1
    orphans = sorted(
        s for s in set(phase_curves["seq"].astype(int)) - probe_seqs_phase
        if s >= seq0 and (s <= seq1 or s > last_pr_seq)
    )
    notes = []
    sweeps = []

    for _, row in pr.iterrows():
        seq = int(row["seq"])
        try:
            g = _curve(curves, run, seq)
        except AssertionError:
            notes.append(f"seq {seq}: probe row but no curve — skipped")
            continue
        sweeps.append(dict(
            seq=seq,
            cyc=int(row["cyc_total"]),
            v=g["v"].to_numpy(float),
            code=g["code"].to_numpy(float),
            integ=float(g["integ_ms"].iloc[0]),
            notch=float(row["notch_v"]) if pd.notna(row["notch_v"]) else np.nan,
            floor_code=float(row["floor_code"]) if pd.notna(row["floor_code"]) else np.nan,
            floor_per_ms=float(row["floor_per_ms"]) if pd.notna(row["floor_per_ms"]) else np.nan,
            curv_per_ms=float(row["curv_per_ms"]) if pd.notna(row.get("curv_per_ms")) else np.nan,
            fit_rms=float(row["fit_rms"]) if pd.notna(row["fit_rms"]) else np.nan,
            source="probe",
        ))

    for seq in orphans:
        g = phase_curves[phase_curves["seq"] == seq].sort_values("v")
        if g.empty:
            continue
        v = g["v"].to_numpy(float)
        code = g["code"].to_numpy(float)
        integ = float(g["integ_ms"].iloc[0])
        notch, floor = _refit_quadratic(v, code)
        cyc = int(g["cyc_total"].iloc[0])
        notes.append(
            f"seq {seq}: curve with no 프로브원본 row — refit quadratic "
            f"(notch={notch:.4f} V, floor={floor:.1f})"
        )
        sweeps.append(dict(
            seq=seq,
            cyc=cyc,
            v=v,
            code=code,
            integ=integ,
            notch=notch,
            floor_code=floor,
            floor_per_ms=floor / integ if integ else np.nan,
            curv_per_ms=np.nan,      # refit orphans carry no probe curvature
            fit_rms=0.0,
            source="refit",
        ))

    sweeps.sort(key=lambda s: (s["cyc"], s["seq"]))
    return sweeps, notes


def fig_block(block, probes, curves, outdir, *, xlim, all_w0,
              normalize: bool = False) -> Path | None:
    sweeps, notes = _collect_block_sweeps(block, probes, curves)
    tag = f"{block['run']} / {block['phase']}"
    for line in notes:
        print(f"  [{tag}] {line}")

    if len(sweeps) < 1:
        print(f"  [{tag}] skip: no usable sweeps")
        return None

    integs = np.array([s["integ"] for s in sweeps], float)
    per_ms = not np.allclose(integs, integs[0])
    if per_ms:
        print(f"  [{tag}] integ_ms varies {sorted(set(np.round(integs, 4)))} "
              "— plotting code/ms")
        for s in sweeps:
            s["y"] = s["code"] / s["integ"]
            s["floor_y"] = s["floor_per_ms"]
    else:
        for s in sweeps:
            s["y"] = s["code"]
            s["floor_y"] = s["floor_code"]

    y_label_extra = ""
    if normalize:
        scale = _code_at_notch(sweeps[0], float(block["w0"]))
        src = "BASE2" if bool(block["has_base2"]) else "BASE"
        if not np.isfinite(scale) or scale == 0:
            print(f"  [{tag}] skip normalize: no code at notch")
            return None
        for s in sweeps:
            s["y"] = s["y"] / scale
            s["floor_y"] = (
                s["floor_y"] / scale if np.isfinite(s["floor_y"]) else np.nan
            )
        y_label_extra = f"  /  code at notch ({src})"
        flags_norm = f"normalized to {src} notch = 1"
    else:
        flags_norm = None

    cycles = np.array([s["cyc"] for s in sweeps], float)
    cmap = plt.cm.viridis
    logc = np.log10(cycles + 1.0)
    lo, hi = float(np.nanmin(logc)), float(np.nanmax(logc))
    span = hi - lo if hi > lo else 1.0
    colors = []
    for cyc, lc in zip(cycles, logc):
        if cyc == 0:
            colors.append("black")
        else:
            colors.append(cmap((lc - lo) / span))

    flags = []
    if not bool(block["has_base2"]):
        flags.append("baseline: BASE (no BASE2)")
    if per_ms:
        flags.append("integ_ms varies; y = code/ms")
    if flags_norm:
        flags.append(flags_norm)
    n_ok = len(sweeps)
    skip_add = n_ok < 3
    if skip_add:
        flags.append("insufficient checkpoints for additivity")

    title1 = (f"{block['run']}  |  {block['phase']}  |  block {int(block['block_order'])}")
    title2 = (
        f"C = {block['C']:+.2f} V   w0 = {block['w0']:+.4f} V   "
        f"ΔF = {block['dF_pct']:+.2f} %   Δw = {block['dw_mV']:+.1f} mV   "
        f"{int(block['n_cycles'])} cycles"
    )
    if flags:
        title2 = title2 + "   " + " · ".join(flags)

    n_panels = 2 if skip_add else 3
    fig, axes = plt.subplots(n_panels, 1, figsize=(7, 10 if n_panels == 3 else 7.2),
                             sharex=False)
    if n_panels == 2:
        axes = list(axes)
        ax_a, ax_c = axes[0], axes[1]
        ax_b = None
    else:
        axes = list(axes)
        ax_a, ax_b, ax_c = axes
        ax_a.sharex(ax_b)

    ax = ax_a
    for s, color in zip(sweeps, colors):
        m = np.isfinite(s["v"]) & np.isfinite(s["y"])
        lw = 1.8 if s["cyc"] == 0 else 1.1
        ax.plot(s["v"][m], s["y"][m], color=color, lw=lw,
                zorder=3 if s["cyc"] == 0 else 2)
        rms = s["fit_rms"]
        nv, fy = s["notch"], s["floor_y"]
        if np.isfinite(rms) and np.isfinite(nv) and np.isfinite(fy):
            ax.plot(nv, fy, "o", ms=5, mfc="none", mec=color, mew=1.1, zorder=4)
    ax.set_ylabel(
        ("ADC code / ms" if per_ms else f"ADC code ({integs[0]:g} ms integration)")
        + y_label_extra
    )
    ax.set_title("(a)  Raw sweeps")
    ax.text(0.03, 0.04, V_NOTE, transform=ax.transAxes, va="bottom", fontsize=8,
            color="0.25")
    handles = [
        Line2D([0], [0], color=c, lw=1.8 if cy == 0 else 1.1, label=str(int(cy)))
        for cy, c in zip(cycles, colors)
    ]
    ax.legend(handles=handles, title="cycles", ncol=4, frameon=False, loc="upper right")
    ax.set_xlim(*xlim)
    _draw_shared_v_refs(ax, float(block["w0"]), all_w0, rug=True)
    if ax_b is not None:
        ax.tick_params(labelbottom=False)
        ax.set_xlabel("")
    else:
        ax.set_xlabel(V_LABEL)
    _hide_top_right(ax)

    last_cyc = int(sweeps[-1]["cyc"])
    if ax_b is not None:
        ax = ax_b
        base = sweeps[0]
        for s, color in zip(sweeps[1:], colors[1:]):
            try:
                grid, y0, y1 = _common_grid(base["v"], base["y"], s["v"], s["y"])
            except AssertionError as exc:
                print(f"  [{tag}] seq {s['seq']} Δcurve skipped: {exc}")
                continue
            ax.plot(grid, y1 - y0, color=color, lw=1.1, label=str(int(s["cyc"])))
        grid, y0, y1 = _common_grid(base["v"], base["y"], sweeps[-1]["v"], sweeps[-1]["y"])
        dc = y1 - y0
        a_fit, b_fit = _ols_dc_on_y0(y0, dc)
        b_mult = float(dc.mean() / y0.mean()) if y0.mean() else np.nan
        ratio = float(b_fit / b_mult) if b_mult else np.nan
        ax.plot(grid, b_mult * y0, color="0.45", ls="--", lw=1.4,
                label=f"multiplicative (Vth) model, {last_cyc} cyc", zorder=3)
        ax.axhline(0.0, color="0.5", lw=0.6)
        ax.set_xlabel(V_LABEL)
        ax.set_ylabel(
            ("ΔADC code / ms" if per_ms else "ΔADC code")
            + ("  (normalized)" if normalize else "")
        )
        ax.set_title("(b)  Difference from baseline")
        ax.text(
            0.03, 0.08,
            f"$b$ = {b_fit:.4f}\n$b_\\mathrm{{mult}}$ = {b_mult:.3f}\n"
            f"ratio = {ratio:.2f}  (at {last_cyc} cyc)",
            transform=ax.transAxes, va="bottom", ha="left",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      edgecolor="0.8", alpha=0.9),
        )
        ax.legend(frameon=False, loc="lower right", ncol=2)
        ax.set_xlim(*xlim)
        _draw_shared_v_refs(ax, float(block["w0"]), all_w0, rug=False)
        _hide_top_right(ax)
    else:
        ax_a.text(
            0.03, 0.18, "insufficient checkpoints for additivity",
            transform=ax_a.transAxes, va="bottom", fontsize=8, color="0.3",
        )

    ax = ax_c
    F = np.array([s["floor_per_ms"] for s in sweeps], float)
    w = np.array([s["notch"] for s in sweeps], float)
    w0 = float(block["w0"])
    x = np.where(cycles == 0, 0.5, cycles)
    finite_x = x[np.isfinite(x) & (x > 0)]
    ax.set_xscale("log")
    ax.set_zorder(2)
    ax.patch.set_alpha(0)
    ax.plot(x, F, "-o", color=C_FLOOR, lw=1.4, ms=5, label="F (notch floor)", zorder=3)
    ax.set_ylabel("F  [code / ms]", color=C_FLOOR)
    ax.tick_params(axis="y", colors=C_FLOOR)
    ax2 = ax.twinx()
    ax2.set_zorder(1)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(True)
    if len(finite_x):
        x0, x1 = float(np.min(finite_x)) * 0.8, float(np.max(finite_x)) * 1.2
    else:
        x0, x1 = 0.4, 2.0
    ax2.fill_between(
        [x0, x1], -REPRO_MV, REPRO_MV,
        color=C_NOTCH, alpha=0.15, zorder=0,
        label="block reproducibility (right axis)",
    )
    ax2.axhline(0.0, color=C_NOTCH, lw=0.6, alpha=0.5, zorder=1)
    dw = (w - w0) * 1000.0
    dw = np.where(np.isfinite(dw), dw, np.nan)
    ax2.plot(x, dw, "-s", color=C_NOTCH, lw=1.4, ms=5, label="w − w0", zorder=3)
    ax2.set_ylabel("w − w0  [mV]", color=C_NOTCH)
    ax2.tick_params(axis="y", colors=C_NOTCH)
    ax2.grid(False)
    uniq = []
    for cyc, xx in zip(cycles, x):
        if not np.isfinite(xx):
            continue
        key = int(cyc)
        if key not in {u[0] for u in uniq}:
            uniq.append((key, xx))
    uniq.sort(key=lambda t: t[1])
    ax.set_xticks([t[1] for t in uniq])
    ax.set_xticklabels([str(t[0]) for t in uniq])
    ax.set_xlabel("Stress cycles")
    ax.set_title("(c)  Floor and notch vs cycles")
    ax.set_xlim(x0, x1)
    r2_lin = _r2(cycles, F)
    r2_log = _r2(np.log10(cycles + 1.0), F)
    r2_txt = []
    if np.isfinite(r2_lin):
        r2_txt.append(rf"$R^2(F,\ \mathrm{{cyc}})$ = {r2_lin:.2f}")
    if np.isfinite(r2_log):
        r2_txt.append(rf"$R^2(F,\ \log_{{10}}(\mathrm{{cyc}}+1))$ = {r2_log:.2f}")
    if r2_txt:
        ax.text(0.03, 0.04, "\n".join(r2_txt), transform=ax.transAxes,
                va="bottom", fontsize=8,
                bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
                          edgecolor="0.85", alpha=0.85))
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, frameon=False, loc="center right")
    _hide_top_right(ax, keep_right=False)
    ax.spines["right"].set_visible(False)

    fig.suptitle(title1 + "\n" + title2, fontsize=9)
    out = Path(outdir) / f"{_block_stem(block)}.png"
    save_kw: dict = dict(dpi=300)
    if np.isclose(float(block["C"]), 0.0):
        _mark_c0_figure(fig, ax_a)
        save_kw.update(facecolor="white", edgecolor=C_ZERO_BADGE)
    _savefig(fig, out, **save_kw)
    plt.close(fig)
    return out


def _scatter_stat(ax, df: pd.DataFrame, xcol: str, ycol: str) -> None:
    for _, r in df.iterrows():
        color = CHIP_COLOR[r.chip]
        marker = ORDER_MARKER.get(int(r.block_order), "o")
        if r.flagged:
            ax.scatter(
                r[xcol], r[ycol], s=48, marker=marker,
                facecolors="none", edgecolors=color, linewidths=1.5, zorder=4,
            )
        else:
            ax.scatter(
                r[xcol], r[ycol], s=42, marker=marker,
                c=[color], edgecolors="0.2", linewidths=0.4, zorder=3,
            )


def _stat_legend(fig, df: pd.DataFrame) -> None:
    chip_h = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=CHIP_COLOR[c],
               markeredgecolor="0.2", markersize=7, label=c)
        for c in ("chip3", "chip4", "chip5", "chip6")
        if c in set(df.chip)
    ]
    order_h = [
        Line2D([0], [0], marker=ORDER_MARKER[k], color="0.3",
               markerfacecolor="0.3", linestyle="none", markersize=7,
               label=f"block {k}")
        for k in (1, 2, 3) if (df.block_order == k).any()
    ]
    flag_h = []
    if df.flag_chip5.any():
        flag_h.append(Line2D(
            [0], [0], marker="o", color="#009E73", markerfacecolor="none",
            markeredgewidth=1.5, linestyle="none", markersize=7,
            label="chip5, fit rms > 10 (degraded)",
        ))
    if df.flag_write.any():
        flag_h.append(Line2D(
            [0], [0], marker="o", color="#CC79A7", markerfacecolor="none",
            markeredgewidth=1.5, linestyle="none", markersize=7,
            label="chip6_0831_1150 (write before block)",
        ))
    handles = chip_h + order_h + flag_h
    fig.legend(handles=handles, loc="lower center", ncol=4, frameon=False,
               bbox_to_anchor=(0.5, -0.04))
    engine = fig.get_layout_engine()
    if engine is not None and hasattr(engine, "set"):
        engine.set(rect=(0, 0.10, 1, 1))


def fig_statistics(stat: pd.DataFrame, outdir: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    axa, axb, axc, axd = axes.ravel()

    _scatter_stat(axa, stat, "w0", "dF_pct")
    med = float(stat.dF_pct.median())
    axa.axhline(med, color="0.35", lw=1.0, ls="--")
    r_wd = _pearson(stat.w0, stat.dF_pct)
    axa.set_xlabel("w0  [V]")
    axa.set_ylabel("ΔF  [%]")
    axa.set_title("(a)  ΔF vs stored value")
    axa.text(0.04, 0.96, f"corr(w0, ΔF) = {r_wd:.3f}",
             transform=axa.transAxes, va="top")
    _hide_top_right(axa)

    x = np.log10(stat.F0.to_numpy(float))
    y = stat.dF_pct.to_numpy(float)
    tmp = stat.copy()
    tmp["logF0"] = np.log10(tmp.F0)
    _scatter_stat(axb, tmp, "logF0", "dF_pct")
    slope, intercept = np.polyfit(x, y, 1)
    xx = np.linspace(x.min(), x.max(), 50)
    axb.plot(xx, slope * xx + intercept, color="0.25", lw=1.0)
    r_fd = _pearson(x, y)
    axb.set_xlabel(r"log$_{10}$ F0  [code/ms]")
    axb.set_ylabel("ΔF  [%]")
    axb.set_title("(b)  ΔF vs common-mode floor")
    axb.text(0.04, 0.96, f"Pearson r = {r_fd:.3f}",
             transform=axb.transAxes, va="top")
    _hide_top_right(axb)

    _scatter_stat(axc, stat, "w0", "dw_mV")
    axc.axhline(0.0, color="0.4", lw=0.8)
    axc.axhspan(-REPRO_MV, REPRO_MV, color="0.5", alpha=0.15, zorder=0)
    axc.set_xlabel("w0  [V]")
    axc.set_ylabel("Δw  [mV]")
    axc.set_title("(c)  Notch shift vs stored value")
    axc.text(0.04, 0.96, "shaded: ±9.5 mV block reproducibility",
             transform=axc.transAxes, va="top")
    _hide_top_right(axc)

    _scatter_stat(axd, stat, "w0", "ratio")
    axd.axhline(0.0, color="0.35", lw=1.0)
    axd.axhline(1.0, color="0.35", lw=1.0, ls="--")
    med_r = float(stat.ratio.median())
    axd.axhline(med_r, color="k", lw=0.9, ls=":")
    axd.set_xlabel("w0  [V]")
    axd.set_ylabel("additivity ratio  $b$ / $b_\\mathrm{mult}$")
    axd.set_title("(d)  Pedestal vs Vth-shift")
    axd.text(0.98, 0.08, "additive offset (pedestal)", ha="right", va="bottom",
             transform=axd.transAxes, color="0.3")
    axd.text(0.98, 0.92, "multiplicative (Vth shift)", ha="right", va="top",
             transform=axd.transAxes, color="0.3")
    axd.text(0.04, 0.55, f"median ratio = {med_r:.2f}",
             transform=axd.transAxes, va="center")
    _hide_top_right(axd)

    _stat_legend(fig, stat)
    _savefig(fig, outdir / "fig2_statistics.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Console + main
# ---------------------------------------------------------------------------
def _print_stats(stat: pd.DataFrame) -> None:
    print(f"\nstat_set: n = {len(stat)}  (C = −0.75 V, 1000 cycles, real BASE2)")
    if len(stat) != 20:
        raise AssertionError(f"stat_set must have 20 blocks, got {len(stat)}")
    print("  by chip:", ", ".join(
        f"{c}={int((stat.chip == c).sum())}" for c in ("chip3", "chip4", "chip5", "chip6")
        if (stat.chip == c).any()
    ))
    flagged = stat[stat.flagged]
    if not flagged.empty:
        print("  flagged (kept):")
        for _, r in flagged.iterrows():
            why = []
            if r.flag_chip5:
                why.append(f"rms_max={r.rms_max:.1f}")
            if r.flag_write:
                why.append("write pulse before block")
            print(f"    {r.run} / {r.phase}  ({'; '.join(why)})")

    dF = stat.dF_pct.to_numpy(float)
    q25, q75 = np.percentile(dF, [25, 75])
    print(f"\nΔF [%]:  median={np.median(dF):.3f}  IQR=[{q25:.3f}, {q75:.3f}]  "
          f"min={dF.min():.3f}  max={dF.max():.3f}  "
          f"n_negative={(dF < 0).sum()}/{len(dF)}")

    dw = stat.dw_mV.to_numpy(float)
    n_out = int((np.abs(dw) > REPRO_MV).sum())
    print(f"Δw [mV]: median={np.median(dw):.2f}  "
          f"outside ±{REPRO_MV:g} mV: {n_out}/{len(dw)}")

    r_w = _pearson(stat.w0, stat.dF_pct)
    logF = np.log10(stat.F0.to_numpy(float))
    r_f = _pearson(logF, stat.dF_pct)
    slope, intercept = np.polyfit(logF, stat.dF_pct.to_numpy(float), 1)
    resid = stat.dF_pct.to_numpy(float) - (intercept + slope * logF)
    r_res = _pearson(stat.w0, resid)
    print(f"corr(w0, ΔF) = {r_w:.3f}")
    print(f"corr(log10 F0, ΔF) = {r_f:.3f}")
    print(
        f"corr(w0, residual ΔF | log10 F0) = {r_res:.3f}   "
        f"(n = {len(stat)}; not significant at this n)"
    )

    print(f"\nAdditivity ratio:  median={stat.ratio.median():.3f}")
    for c in ("chip3", "chip4", "chip5", "chip6"):
        sub = stat[stat.chip == c]
        if sub.empty:
            continue
        print(f"  {c} median ratio = {sub.ratio.median():.3f}  (n={len(sub)})")

    ex = stat[(stat.run == EXEMPLAR_RUN) & (stat.phase == EXEMPLAR_PHASE)]
    if len(ex) != 1:
        raise AssertionError(f"exemplar {EXEMPLAR_RUN}/{EXEMPLAR_PHASE} not in stat_set")
    e = ex.iloc[0]
    checks = {
        "dc_mean": (e.dc_mean, -119.3, 2.0),
        "dc_std": (e.dc_std, 3.9, 0.5),
        "a": (e.a, -114.5, 2.0),
        "b": (e.b, -0.0027, 0.001),
        "b_mult": (e.b_mult, -0.067, 0.01),
        "ratio": (e.ratio, 0.04, 0.03),
    }
    failed = []
    for name, (got, exp, tol) in checks.items():
        ok = abs(got - exp) <= tol
        if not ok:
            failed.append(f"{name} got {got:.4g} expected ~{exp}")
        print(f"  {EXEMPLAR_RUN} {name}={got:.4g}  (expected ~{exp})  "
              f"{'PASS' if ok else 'FAIL'}")
    print("Exemplar additivity regression check: "
          + ("PASS" if not failed else "FAIL  " + "; ".join(failed)))

    m1 = float(stat.loc[stat.block_order == 1, "dF_pct"].median())
    later = stat[stat.block_order > 1]
    m2 = float(later.dF_pct.median()) if len(later) else float("nan")
    print(f"\nBlock-order effect (stat_set):  "
          f"median ΔF  order=1 → {m1:.2f}%   order>1 → {m2:.2f}%")
    c6 = stat[stat.chip == "chip6"]
    if not c6.empty:
        m1c = float(c6.loc[c6.block_order == 1, "dF_pct"].median())
        later6 = c6[c6.block_order > 1]
        m2c = float(later6.dF_pct.median()) if len(later6) else float("nan")
        print(f"  within chip6:  order=1 → {m1c:.2f}%   order>1 → {m2c:.2f}%")


def fig3_notch_positions(blocks: pd.DataFrame, xlim: tuple[float, float],
                         outdir: Path) -> None:
    df = blocks.sort_values(["w0", "run", "phase"]).reset_index(drop=True)
    n = len(df)
    fig, ax = plt.subplots(figsize=(8.2, max(6.0, 0.30 * n + 1.6)))
    y_top = n - 1
    half = REPRO_MV / 1000.0
    for i, r in df.iterrows():
        y = y_top - i
        color = CHIP_COLOR.get(r.chip, "0.3")
        w0, w1 = float(r.w0), float(r.w1)
        ax.fill_betweenx(
            [y - 0.38, y + 0.38], w0 - half, w0 + half,
            color="0.78", alpha=0.55, zorder=0, linewidth=0,
        )
        ax.plot(w0, y, "o", color=color, ms=6.5, zorder=3,
                markeredgecolor="0.15", markeredgewidth=0.4)
        if np.isfinite(w1) and w1 != w0:
            ax.annotate(
                "", xy=(w1, y), xytext=(w0, y),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.3,
                                mutation_scale=9),
                zorder=2,
            )
        else:
            ax.plot(w1, y, "s", color=color, ms=4, zorder=3)
        is_c0 = np.isclose(float(r.C), 0.0)
        if is_c0:
            ax.plot(w0, y, "o", ms=10, mfc="none", mec=C_ZERO_BADGE, mew=1.4, zorder=4)
        ax.text(
            1.01, y, f"{float(r.dw_mV):+.1f} mV",
            transform=ax.get_yaxis_transform(),
            ha="left", va="center", fontsize=7, color=color, clip_on=False,
        )
    ax.axvline(0.0, color="0.45", ls=":", lw=1.0, zorder=1)
    ax.set_xlim(*xlim)
    ax.set_ylim(-0.7, n - 0.3)
    ax.set_xlabel(V_LABEL)
    ax.set_yticks([y_top - i for i in range(n)])
    labels = []
    for _, r in df.iterrows():
        lab = f"{r.chip}  {r.phase}"
        if np.isclose(float(r.C), 0.0):
            lab += "  [C=0]"
        labels.append(lab)
    ax.set_yticklabels(labels, fontsize=6.5)
    ax.set_title("Notch motion across all 28 blocks  (marker = $w_0$, arrow → $w_1$)")
    chip_h = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=CHIP_COLOR[c],
               markeredgecolor="0.15", markersize=7, label=c)
        for c in ("chip3", "chip4", "chip5", "chip6")
        if c in set(df.chip)
    ]
    extra = [
        Line2D([0], [0], color="0.7", lw=8, alpha=0.55,
               label="±9.5 mV reproducibility"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor="none",
               markeredgecolor=C_ZERO_BADGE, markeredgewidth=1.4, markersize=8,
               label="C = 0"),
    ]
    ax.legend(handles=chip_h + extra, loc="lower right", frameon=False, fontsize=8)
    engine = fig.get_layout_engine()
    if engine is not None and hasattr(engine, "set"):
        engine.set(rect=(0, 0, 0.88, 1))
    out = Path(outdir) / "fig3_notch_positions.png"
    _savefig(fig, out, dpi=300)
    plt.close(fig)
    print(f"wrote {out}")


def _assert_unique_stems(blocks: pd.DataFrame) -> list[str]:
    stems = [_block_stem(r) for _, r in blocks.iterrows()]
    seen: dict[str, tuple] = {}
    for stem, (_, r) in zip(stems, blocks.iterrows()):
        key = (r["run"], r["phase"], int(r["block_order"]))
        if stem in seen:
            raise AssertionError(
                f"filename collision {stem!r}: {seen[stem]} vs {key}"
            )
        seen[stem] = key
    return stems


def _purge_pdfs(outdir: Path) -> None:
    for p in outdir.rglob("*.pdf"):
        p.unlink()
        print(f"removed leftover PDF {p}")


def fig_all_blocks(blocks: pd.DataFrame, probes, curves, outdir: Path) -> None:
    xlim = shared_v_xlim(probes, curves)
    print(f"shared v axis: {xlim[0]:+.3f} … {xlim[1]:+.3f} V")
    all_w0 = blocks["w0"].to_numpy(float)
    _assert_unique_stems(blocks)

    def _run(dest: Path, normalize: bool) -> None:
        dest.mkdir(parents=True, exist_ok=True)
        written, skipped = [], []
        for _, rec in blocks.iterrows():
            tag = f"{rec['run']} / {rec['phase']} / blk{int(rec['block_order'])}"
            try:
                path = fig_block(
                    rec, probes, curves, dest,
                    xlim=xlim, all_w0=all_w0, normalize=normalize,
                )
            except Exception:
                print(f"FAILED {tag}")
                traceback.print_exc()
                skipped.append((tag, "exception"))
                plt.close("all")
                continue
            if path is None:
                skipped.append((tag, "no usable sweeps"))
                continue
            print(f"wrote {path}")
            written.append(str(path))
        kind = "normalized" if normalize else "raw"
        print(f"\nBlock figures ({kind}): {len(written)} written, {len(skipped)} skipped")
        for tag, why in skipped:
            print(f"  skipped {tag}: {why}")

    _run(Path(outdir) / "blocks", normalize=False)
    _run(Path(outdir) / "blocks_normalized", normalize=True)
    fig3_notch_positions(blocks, xlim, outdir)




# ---------------------------------------------------------------------------
# Publication summary figure
# ---------------------------------------------------------------------------
def _norm_sweeps(block, probes, curves):
    """Sweeps for one block with ``y`` filled in the way fig_block does.

    Same rules: code/ms when the integration time varies across checkpoints,
    raw code otherwise, then divided by the baseline code at w0 so the cycle-0
    notch sits at 1. Returns (sweeps, ok); ok is False when the block cannot be
    normalised, which is the only condition fig_block also refuses.
    """
    sweeps, _notes = _collect_block_sweeps(block, probes, curves)
    if not sweeps:
        return [], False
    integs = np.array([s["integ"] for s in sweeps], float)
    per_ms = not np.allclose(integs, integs[0])
    for s in sweeps:
        if per_ms:
            s["y"] = s["code"] / s["integ"]
            s["floor_y"] = s["floor_per_ms"]
        else:
            s["y"] = s["code"]
            s["floor_y"] = s["floor_code"]
    scale = _code_at_notch(sweeps[0], float(block["w0"]))
    if not np.isfinite(scale) or scale == 0:
        return sweeps, False
    for s in sweeps:
        s["y"] = s["y"] / scale
        s["floor_y"] = s["floor_y"] / scale if np.isfinite(s["floor_y"]) else np.nan
    return sweeps, True


def _cycle_colors(cycles: np.ndarray) -> list:
    """Viridis by log cycle, cycle 0 black -- the fig_block convention."""
    cmap = plt.cm.viridis
    logc = np.log10(np.asarray(cycles, float) + 1.0)
    lo, hi = float(np.nanmin(logc)), float(np.nanmax(logc))
    span = hi - lo if hi > lo else 1.0
    return [
        "black" if cyc == 0 else cmap((lc - lo) / span)
        for cyc, lc in zip(cycles, logc)
    ]


def _block_track(block, probes, curves):
    """Per-checkpoint cycles, notch drift [mV] and curvature change [%]."""
    sweeps, _notes = _collect_block_sweeps(block, probes, curves)
    if not sweeps:
        return None
    cyc = np.array([s["cyc"] for s in sweeps], float)
    notch = np.array([s["notch"] for s in sweeps], float)
    curv = np.array([s.get("curv_per_ms", np.nan) for s in sweeps], float)
    dw = (notch - float(block["w0"])) * 1000.0
    a0 = curv[0] if len(curv) and np.isfinite(curv[0]) and curv[0] != 0 else np.nan
    da = (curv / a0 - 1.0) * 100.0 if np.isfinite(a0) else np.full_like(curv, np.nan)
    return dict(cyc=cyc, x=np.where(cyc == 0, 0.5, cyc), dw=dw, da=da)


def fig_main_read_disturb(blocks: pd.DataFrame, stat: pd.DataFrame,
                          probes: pd.DataFrame, curves: pd.DataFrame,
                          outdir: Path, ext: pd.DataFrame | None = None) -> Path:
    """One-row summary: what a read-cycle budget costs the stored value.

    Three panels, sized to drop into a larger multi-device figure as a single
    row. (a) the no-write control's sweeps at every checkpoint, normalised, so
    the notch staying put while the floor falls is visible directly. (b) that
    same drift against cycles for every relaxation-separated block, extended by
    the single-target runs measured to 10^9, against the block-to-block
    reproducibility and the calibrated tolerances. (c) the drift across the
    stored-value range -- at 10^3 cycles near zero from the supplementary
    blocks, and at 10^9 cycles across the full -1.95 .. +0.45 V from the new
    runs -- with the common-mode pedestal underneath it.

    With the 10^9 workbook in place nothing past 10^3 is extrapolated; the
    hatched window only appears when that workbook is missing.
    """
    relax = blocks[blocks["relax_sep"]].copy()
    if len(relax) < 5:
        raise AssertionError(
            f"expected at least 5 relaxation-separated blocks, found {len(relax)}; "
            "check the '완화 분리' column mapping in load()/build_blocks()"
        )

    exemplar = blocks[(blocks["run"] == EXEMPLAR_RUN)
                      & (blocks["phase"] == EXEMPLAR_PHASE)]
    if exemplar.empty:
        raise AssertionError(f"no block for exemplar {EXEMPLAR_RUN}/{EXEMPLAR_PHASE}")
    exemplar = exemplar.sort_values("n_cycles").iloc[-1]

    ext_tracks = extended_tracks(ext) if ext is not None else []
    # Five traces crossing one small panel are unreadable in a single colour,
    # and V_W is what separates them, so panels b and c share the stored-value
    # colour map the single-panel figure uses.
    ext_norm = ext_cmap = None
    if ext_tracks:
        w0s = np.array([t["w0"] for t in ext_tracks], float)
        ext_norm = Normalize(vmin=float(w0s.min()), vmax=float(w0s.max()))
        ext_cmap = plt.cm.cividis

    print("\nMain read-disturb figure")
    print(f"  relaxation-separated blocks: {len(relax)} "
          f"({', '.join(sorted(set(relax['chip'])))})")

    fig = plt.figure(figsize=(7.2, 2.4), constrained_layout=True)
    gs = fig.add_gridspec(1, 3, width_ratios=(1.0, 1.0, 1.0))
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    gs_c = gs[0, 2].subgridspec(2, 1, height_ratios=(2, 1), hspace=0.08)
    ax_c = fig.add_subplot(gs_c[0, 0])
    ax_cf = fig.add_subplot(gs_c[1, 0], sharex=ax_c)

    # -- (a) the exemplar's sweeps ------------------------------------------
    sweeps, ok = _norm_sweeps(exemplar, probes, curves)
    if not ok:
        raise AssertionError("exemplar block cannot be normalised")
    w0_ex = float(exemplar["w0"])
    cycles = np.array([s["cyc"] for s in sweeps], float)
    colors = _cycle_colors(cycles)
    for s, color in zip(sweeps, colors):
        m = np.isfinite(s["v"]) & np.isfinite(s["y"])
        ax_a.plot(s["v"][m], s["y"][m], color=color,
                  lw=1.6 if s["cyc"] == 0 else 0.9,
                  zorder=3 if s["cyc"] == 0 else 2)
        if np.isfinite(s["notch"]) and np.isfinite(s["floor_y"]):
            ax_a.plot(s["notch"], s["floor_y"], "o", ms=3.2, mfc="none",
                      mec=color, mew=0.9, zorder=4)
    ax_a.axvline(w0_ex, color="0.15", ls="--", lw=0.9, zorder=1)
    lo, hi = shared_v_xlim(probes, curves)
    ax_a.set_xlim(max(lo, w0_ex - 0.35), min(hi, w0_ex + 0.35))
    ax_a.set_xlabel("Differential offset  $v$  (V)")
    ax_a.set_ylabel("Normalised current")
    handles = [
        Line2D([0], [0], color=c, lw=1.6 if cy == 0 else 0.9, label=str(int(cy)))
        for cy, c in zip(cycles, colors)
    ]
    ax_a.legend(handles=handles, title="cycles", ncol=4, frameon=False,
                loc="upper center", fontsize=5.5, title_fontsize=6,
                handlelength=1.0, columnspacing=0.7, handletextpad=0.4,
                borderpad=0.2, labelspacing=0.25)
    ax_a.text(0.03, 0.06, "notch fixed, floor drops", transform=ax_a.transAxes,
              va="bottom", ha="left", fontsize=6.5, color="0.25")

    # -- (b) drift vs cycles -------------------------------------------------
    ax_b.set_xscale("log")
    # Once the 10^9 runs are in, the axis carries |dw|: a state is misread
    # whichever way it drifts, so the band and the bounds are one-sided.
    ax_b.axhspan(0.0 if ext_tracks else -REPRO_MV, REPRO_MV,
                 color="0.5", alpha=0.15, zorder=0)
    # The curvature inset is built from the supplementary sweeps. The 10^9
    # workbook stores fitted notch/floor/curvature but no sweeps of its own, so
    # the inset goes with the blocks it came from.
    ax_ins = None if ext_tracks else ax_b.inset_axes([0.19, 0.60, 0.30, 0.33])

    ex_key = (exemplar["run"], exemplar["phase"])
    ex_track = None
    for _, blk in relax.iterrows():
        tr = _block_track(blk, probes, curves)
        if tr is None:
            continue
        is_ex = (blk["run"], blk["phase"]) == ex_key
        if is_ex:
            ex_track = tr
        if ext_tracks:
            # These stop at 10^3 because the run was stopped there, not because
            # the drift was. Drawn beside traces that carry on to 10^9 they
            # would read as a flat ending the measurement never established.
            continue
        style = dict(color="black", lw=1.4, ms=3.0, zorder=4) if is_ex else \
            dict(color="0.62", lw=0.8, ms=2.2, zorder=3)
        ax_b.plot(tr["x"], tr["dw"], "-o", **style)
        if np.isfinite(tr["da"]).any():
            ax_ins.plot(tr["x"], tr["da"], "-o", **style)

    if ex_track is None:
        raise AssertionError("exemplar block missing from the relax_sep set")

    if ext_tracks:
        # Measured, so the decade fit and its hatched window are gone.
        for tr in ext_tracks:
            ax_b.plot(tr["x"], np.abs(tr["dw"]), "-D",
                      color=ext_cmap(ext_norm(tr["w0"])), lw=1.0, ms=2.4,
                      mec="black", mew=0.4, zorder=5)
        ax_b.legend(handles=[
            Line2D([0], [0], marker="D", ms=2.4, mec="black", mew=0.4, lw=1.0,
                   color=ext_cmap(ext_norm(tr["w0"])),
                   label=f"{tr['w0']:+.2f}") for tr in ext_tracks
        ], title=r"$V_W$ (V)", ncol=2, frameon=False, loc="upper left",
            fontsize=5.0, title_fontsize=5.5, handlelength=1.6,
            columnspacing=0.8, handletextpad=0.4, borderpad=0.2,
            labelspacing=0.25)
        print(f"  panel b: {len(ext_tracks)} single-target runs measured to "
              f"1e9 cycles; worst |dw@1e9| = "
              f"{max(abs(t['dw_final']) for t in ext_tracks):.0f} mV")
    else:
        fit_m = (ex_track["cyc"] >= 1) & np.isfinite(ex_track["dw"])
        slope = intercept = np.nan
        if fit_m.sum() >= 2:
            lx = np.log10(ex_track["cyc"][fit_m] + 1.0)
            slope, intercept = np.polyfit(lx, ex_track["dw"][fit_m], 1)
            xx = np.logspace(3, 7, 200)
            ax_b.plot(xx, slope * np.log10(xx + 1.0) + intercept, ls=":",
                      color="black", lw=1.1, zorder=5)
            dw_1e7 = slope * np.log10(1e7 + 1.0) + intercept
            print(f"  exemplar notch drift: {slope:+.2f} mV/decade "
                  f"(cycles >= 1, n = {int(fit_m.sum())})")
            print(f"  extrapolated to 1e7 cycles: {dw_1e7:+.1f} mV "
                  f"(strict {TOLERANCE_MV_STRICT:.0f} mV / lenient "
                  f"{TOLERANCE_MV_LENIENT:.0f} mV; nominal spacing "
                  f"{LEVEL_SPACING_MV:.1f} mV)")
        ax_b.axvspan(1e3, 1e7, facecolor="0.92", edgecolor="0.75", hatch="///",
                     lw=0.0, zorder=0)
        ax_b.text(3e4, 0.04, "extrapolated",
                  transform=ax_b.get_xaxis_transform(),
                  ha="center", va="bottom", fontsize=6, color="0.35")
    # Lenient tolerance only. It bounds |dw|, which is what the axis shows in
    # the measured variant, so one line. The strict (Kendall tau) bound is no
    # longer drawn -- see the note at TOLERANCE_MV_STRICT.
    ax_b.axhline(TOLERANCE_MV_LENIENT, color="#1f4e79", ls="-.", lw=0.9, zorder=2)
    if ext_tracks:
        # Short label in the gutter past the last checkpoint.
        ax_b.text(0.985, TOLERANCE_MV_LENIENT, "lenient ",
                  transform=ax_b.get_yaxis_transform(), ha="right",
                  va="bottom", fontsize=5.5 + TOL_LABEL_BUMP, color="#1f4e79",
                  bbox=LABEL_BBOX, zorder=7)
    else:
        ax_b.text(0.985, TOLERANCE_MV_LENIENT, TOLERANCE_LENIENT_LABEL + " ",
                  transform=ax_b.get_yaxis_transform(), ha="right",
                  va="bottom", fontsize=5.5 + TOL_LABEL_BUMP, color="#1f4e79")
        # Nominal adjacent-state spacing, faint context.
        ax_b.axhline(LEVEL_SPACING_MV, color="0.6", ls=":", lw=0.8, zorder=2)
        ax_b.text(0.985, LEVEL_SPACING_MV, "nominal spacing ",
                  transform=ax_b.get_yaxis_transform(),
                  ha="right", va="top", fontsize=5.0, color="0.6")
        ax_b.text(0.55, -REPRO_MV, f" block reproducibility ±{REPRO_MV:g} mV",
                  transform=ax_b.get_yaxis_transform(), ha="left", va="top",
                  fontsize=6, color="0.35")
    if ext_tracks:
        ax_b.set_xlim(0.4, 2e9)
        dw_ext = np.concatenate([t["dw"][np.isfinite(t["dw"])]
                                 for t in ext_tracks])
        span = max(float(np.abs(dw_ext).max()), TOLERANCE_MV_LENIENT) * 1.12
        ax_b.set_ylim(0.0, span)
        _bold_decade_ticks(ax_b, [1.0, 1e3, 1e6, 1e9],
                           ["1", "10^3", "10^6", "10^9"])
    else:
        ax_b.set_xlim(0.4, 2e7)
        ylo, yhi = ax_b.get_ylim()
        if not (ylo < LEVEL_SPACING_MV < yhi):
            ax_b.set_ylim(-60.0, 60.0)
        else:
            ax_b.set_ylim(ylo, max(yhi, LEVEL_SPACING_MV * 1.18))
    ax_b.set_xlabel("Stress cycles")
    ax_b.set_ylabel(r"$|\Delta w|$  (mV)" if ext_tracks else r"$\Delta w$  (mV)")

    if ax_ins is not None:
        ax_ins.axhline(0.0, color="0.5", lw=0.6)
        ax_ins.set_xscale("log")
        ax_ins.set_xlim(0.4, 2e3)
        ax_ins.set_ylabel(r"$\Delta a$ (%)", fontsize=6)
        ax_ins.tick_params(labelsize=5.5, length=2, pad=1)
        _hide_top_right(ax_ins)

    # -- (c) drift across the stored-value range -----------------------------
    ax_c.axhspan(0.0 if ext_tracks else -REPRO_MV, REPRO_MV,
                 color="0.5", alpha=0.15, zorder=0)
    ax_c.axhline(0.0, color="0.5", lw=0.6, zorder=1)
    handles = []
    if not ext_tracks:
        # The 10^3 blocks, shown only when there is nothing measured further.
        sel = blocks[(blocks["n_cycles"] == 1000)
                     & np.isclose(blocks["C"], -0.75)].copy()
        n_filled = int(sel["relax_sep"].sum())
        n_out = int((sel["dw_mV"].abs() > REPRO_MV).sum())
        r_dw = _pearson(sel["w0"], sel["dw_mV"])
        r_dF = _pearson(sel["w0"], sel["dF_pct"])
        print(f"  panel c: {len(sel)} blocks, {n_filled} relaxation-separated, "
              f"{n_out} outside ±{REPRO_MV:g} mV")
        print(f"  panel c: Pearson r(w0, dw) = {r_dw:+.3f}, "
              f"r(w0, dF) = {r_dF:+.3f}")
        med_dF = float(np.nanmedian(sel["dF_pct"]))
        ax_cf.axhline(med_dF, color="0.35", ls="--", lw=0.9, zorder=1)
        for _, r in sel.iterrows():
            col = CHIP_COLOR.get(r["chip"], "0.4")
            filled = bool(r["relax_sep"])
            kw = dict(marker="o", ms=4.0, mew=1.0, mec=col, ls="none", zorder=3,
                      mfc=col if filled else "none")
            ax_c.plot(r["w0"], r["dw_mV"], **kw)
            ax_cf.plot(r["w0"], r["dF_pct"], **kw)
        ax_cf.text(0.03, 0.10, f"median {med_dF:+.2f} %",
                   transform=ax_cf.transAxes, ha="left", va="bottom",
                   fontsize=6, color="0.35")
        handles = [
            Line2D([0], [0], marker="o", ls="none", ms=4.0, mfc="0.35",
                   mec="0.35", label=r"relax. separated, $10^3$"),
            Line2D([0], [0], marker="o", ls="none", ms=4.0, mfc="none",
                   mec="0.35", label=r"not separated, $10^3$"),
        ]
    if ext_tracks:
        # Every point here is a run that actually reached 10^9 cycles, across
        # the whole programmable range rather than the +-0.3 V the
        # supplementary blocks covered.
        w_ext = np.array([t["w0"] for t in ext_tracks], float)
        dw_ext = np.abs([t["dw_final"] for t in ext_tracks])
        dF_ext = np.array([t["dF_final"] for t in ext_tracks], float)
        # dF for these runs is the ratio of raw floor codes, not of code/ms:
        # the 10^9 campaign reads the TIA directly at a fixed integration, so
        # there is no integ_ms to divide out. Both are relative changes of the
        # same pedestal, so the percentages sit on one axis.
        for wv, dwv, dfv in zip(w_ext, dw_ext, dF_ext):
            kw = dict(marker="D", ls="none", ms=4.2,
                      mfc=ext_cmap(ext_norm(wv)), mec="black", mew=0.5,
                      zorder=4)
            ax_c.plot(wv, dwv, **kw)
            ax_cf.plot(wv, dfv, **kw)
        ax_c.axhline(TOLERANCE_MV_LENIENT, color="#1f4e79", ls="-.", lw=0.8,
                     zorder=2)
        ax_c.text(0.98, TOLERANCE_MV_LENIENT, "lenient ",
                  transform=ax_c.get_yaxis_transform(), ha="right",
                  va="bottom", fontsize=5.0 + TOL_LABEL_BUMP, color="#1f4e79",
                  bbox=LABEL_BBOX, zorder=7)
        ax_c.text(0.03, 0.97, r"one run per point, $10^9$ cycles",
                  transform=ax_c.transAxes, ha="left", va="top", fontsize=5.0,
                  color="0.35")
        r_ext = _pearson(w_ext, dw_ext)
        print(f"  panel c: {len(w_ext)} single-target runs at 1e9, V_W "
              f"{w_ext.min():+.2f} .. {w_ext.max():+.2f} V, "
              f"Pearson r(w0, |dw@1e9|) = {r_ext:+.3f}")
        lim = max(float(dw_ext.max()), TOLERANCE_MV_LENIENT) * 1.15
        ax_c.set_ylim(0.0, lim)

    # With the 10^9 points in, the panel is empty at the bottom left and busy
    # at the top, and the cycle count belongs in the legend entries rather than
    # in an axis label long enough to collide with the neighbouring panel.
    if handles:
        ax_c.legend(handles=handles, frameon=False, loc="upper left",
                    fontsize=5.0, handletextpad=0.4, borderpad=0.2,
                    labelspacing=0.25)
    if ext_tracks:
        ax_c.set_ylabel(r"$|\Delta w|$ @$10^9$  (mV)")
        ax_cf.set_ylabel(r"$\Delta F$ @$10^9$  (%)")
    else:
        ax_c.set_ylabel(r"$\Delta w$ @$10^3$  (mV)")
        ax_cf.set_ylabel(r"$\Delta F$ @$10^3$  (%)")
    # The stored-value axis now runs -1.95 .. +0.45 V, so the label is wider
    # than the panel; at 8 pt it still reads as the emphasised axis and stops
    # running off the right edge of the figure.
    ax_cf.set_xlabel(r"Stored value  $V_W$  (V)", fontsize=8,
                     fontweight="bold")
    ax_c.tick_params(labelbottom=False)

    for ax, letter in ((ax_a, "a"), (ax_b, "b"), (ax_c, "c")):
        ax.text(0.0, 1.02, letter, transform=ax.transAxes, ha="left", va="bottom",
                fontweight="bold", fontsize=9)
    for ax in (ax_a, ax_b, ax_c, ax_cf):
        _hide_top_right(ax)

    png = outdir / "fig_read_disturb_main.png"
    svg = outdir / "fig_read_disturb_main.svg"
    _savefig(fig, png, dpi=300)
    _savefig(fig, svg)
    plt.close(fig)
    print(f"  wrote {png}")
    print(f"  wrote {svg}")
    return png


def _half_min_spacing_mV() -> float:
    """Half the smallest gap between adjacent programmed states, in mV.

    This is the quantity a read disturbance has to be compared against: two
    states are still told apart as long as the drift stays inside half the gap
    to the nearest neighbour. The ladder is not uniform, so the *minimum* gap
    is what sets the margin, not the mean.

    Uses the measured ladder in LADDER_NOTCHES_V when it is filled in. With it
    still None the fall-back is the nominal design pitch, which is not a
    measurement -- the warning below says so, loudly, because a margin quoted
    against a nominal pitch is not a result.
    """
    if LADDER_NOTCHES_V:
        notches = np.sort(np.asarray(LADDER_NOTCHES_V, dtype=float))
        gaps_mV = np.diff(notches) * 1000.0
        print(f"  ladder: {len(notches)} states, adjacent spacing "
              f"min {gaps_mV.min():.1f} / median {np.median(gaps_mV):.1f} / "
              f"max {gaps_mV.max():.1f} mV")
        return 0.5 * float(gaps_mV.min())
    half = 0.5 * (NOMINAL_LADDER_SPAN_V / (NOMINAL_N_STATES - 1)) * 1000.0
    print("  *** WARNING: LADDER_NOTCHES_V is not set. The decision-boundary "
          f"reference ({half:.1f} mV) is the NOMINAL design pitch, not a "
          "measurement.")
    print("  *** Fill LADDER_NOTCHES_V with the 25 fitted notch positions from "
          "Supplementary Fig. S3 before submission.")
    return half


def _single_measured(ext_tracks: list[dict], strict_mV: float,
                     lenient_mV: float):
    """The measured variant: |dw| vs cycles for the 10^9 single-target runs.

    One trace per stored value, coloured by it. Nothing from the supplementary
    campaign is drawn here -- those runs were stopped at 10^3 cycles, and a
    trace that ends flat next to traces still climbing at 10^9 states something
    the measurement never did.
    """
    fig, ax = plt.subplots(figsize=(3.7, 2.8), constrained_layout=True)
    ax.set_xscale("log")

    w0s = np.array([t["w0"] for t in ext_tracks], float)
    norm = Normalize(vmin=float(w0s.min()), vmax=float(w0s.max()))
    cmap = plt.cm.cividis

    # The strip at the bottom is how well a block repeats at all. The green
    # band that used to run up to the strict bound went with the strict line:
    # a shaded region whose only edge is an undrawn threshold reads as a claim
    # the figure no longer makes.
    ax.axhspan(0.0, REPRO_MV, color="0.5", alpha=0.18, zorder=1)

    for tr in ext_tracks:
        ax.plot(tr["x"], np.abs(tr["dw"]), "-D", color=cmap(norm(tr["w0"])),
                lw=1.4, ms=3.6, mec="black", mew=0.5, zorder=4)
        print(f"  V_W = {tr['w0']:+.3f} V: {tr['slope']:+.1f} mV/decade "
              f"(measured), |dw@1e9| = {abs(tr['dw_final']):.1f} mV -> "
              f"{100.0 * abs(tr['dw_final']) / strict_mV:.0f} % of strict, "
              f"{100.0 * abs(tr['dw_final']) / lenient_mV:.0f} % of lenient")

    # |dw| is the quantity the tolerance bounds, so it is a single line.
    ax.axhline(lenient_mV, color="#1f4e79", ls="-.", lw=1.1, zorder=3)
    ax.text(0.015, lenient_mV, " " + TOLERANCE_LENIENT_LABEL,
            transform=ax.get_yaxis_transform(), ha="left", va="bottom",
            fontsize=5.5 + TOL_LABEL_BUMP, color="#1f4e79", bbox=LABEL_BBOX,
            zorder=7)
    ax.text(0.985, REPRO_MV, "block reproducibility ",
            transform=ax.get_yaxis_transform(), ha="right", va="bottom",
            fontsize=5.0, color="0.45", bbox=LABEL_BBOX, zorder=7)
    # The nominal pitch (27 mV) lands within a few mV of the strict bound and is
    # not a measurement; at this scale the two would be one smear, so only the
    # calibrated bound is drawn.

    dw_all = np.concatenate([np.abs(t["dw"][np.isfinite(t["dw"])])
                             for t in ext_tracks])
    ax.set_xlim(0.5, 2e9)
    ax.set_ylim(0.0, max(float(dw_all.max()), lenient_mV) * 1.12)
    _bold_decade_ticks(ax, [1.0, 1e1, 1e3, 1e5, 1e7, 1e9],
                       ["1", "10", "10^3", "10^5", "10^7", "10^9"])
    ax.set_xlabel("Stress cycles")
    ax.set_ylabel(r"$|\Delta w|$  (mV)")
    return fig, ax, norm, cmap


def _single_extrapolated(blocks: pd.DataFrame, probes: pd.DataFrame,
                         curves: pd.DataFrame, strict_mV: float,
                         lenient_mV: float, half_gap_mV: float):
    """The fallback variant, used when the 10^9 workbook is not present.

    Signed dw for the relaxation-separated blocks -- the ones in which the read
    stress is the only thing acting -- out to the 10^3 cycles they were
    measured to, then a decade fit through the no-write control, drawn inside a
    hatched window so that the extrapolation is never mistaken for data.
    """
    relax = blocks[blocks["relax_sep"]].copy()
    if len(relax) < 5:
        raise AssertionError(
            f"expected at least 5 relaxation-separated blocks, found {len(relax)}; "
            "check the '완화 분리' column mapping in load()/build_blocks()"
        )
    tracks = []
    for _, blk in relax.iterrows():
        tr = _block_track(blk, probes, curves)
        if tr is None:
            continue
        tr["w0"] = float(blk["w0"])
        tr["is_control"] = (blk["run"] == EXEMPLAR_RUN
                            and blk["phase"] == EXEMPLAR_PHASE)
        tracks.append(tr)
    if not tracks:
        raise AssertionError("no usable sweeps in the relaxation-separated blocks")
    control = next((t for t in tracks if t["is_control"]), None)
    if control is None:
        raise AssertionError(
            f"no-write control {EXEMPLAR_RUN}/{EXEMPLAR_PHASE} is not in the "
            "relaxation-separated set"
        )

    fig, ax = plt.subplots(figsize=(3.4, 2.6), constrained_layout=True)
    ax.set_xscale("log")
    ax.axhspan(-REPRO_MV, REPRO_MV, color="0.5", alpha=0.15, zorder=0)
    ax.axvspan(1e3, 1e7, facecolor="0.93", edgecolor="0.78", hatch="///",
               lw=0.0, zorder=0)

    w0s = np.array([t["w0"] for t in tracks], float)
    norm = Normalize(vmin=float(w0s.min()), vmax=float(w0s.max()))
    cmap = plt.cm.cividis
    for tr in tracks:
        color = cmap(norm(tr["w0"]))
        if tr["is_control"]:
            ax.plot(tr["x"], tr["dw"], "-o", color=color, lw=1.8, ms=4.0,
                    mec="black", mew=0.8, zorder=5)
        else:
            ax.plot(tr["x"], tr["dw"], "-o", color=color, lw=1.0, ms=3.0,
                    mew=0.0, zorder=4)

    fit_m = (control["cyc"] >= 1) & np.isfinite(control["dw"])
    if fit_m.sum() >= 2:
        lx = np.log10(control["cyc"][fit_m] + 1.0)
        slope, intercept = np.polyfit(lx, control["dw"][fit_m], 1)
        xx = np.logspace(3, 7, 200)
        ax.plot(xx, slope * np.log10(xx + 1.0) + intercept, ls=":",
                color="black", lw=1.2, zorder=6)
        dw_1e7 = slope * np.log10(1e7 + 1.0) + intercept
        print(f"  no-write control drift: {slope:+.2f} mV/decade "
              f"(cycles >= 1, n = {int(fit_m.sum())})")
        print(f"  extrapolated to 1e7 cycles: {dw_1e7:+.1f} mV  "
              f"(strict {strict_mV:.0f} mV -> "
              f"{100.0*dw_1e7/strict_mV:.0f} %; lenient {lenient_mV:.0f} mV "
              f"-> {100.0*dw_1e7/lenient_mV:.0f} %; nominal half-spacing "
              f"{half_gap_mV:.1f} mV)")

    ax.axhline(lenient_mV, color="#1f4e79", ls="-.", lw=1.1, zorder=3)
    ax.text(0.02, lenient_mV, " " + TOLERANCE_LENIENT_LABEL,
            transform=ax.get_yaxis_transform(), ha="left", va="bottom",
            fontsize=6 + TOL_LABEL_BUMP, color="#1f4e79")
    # Nominal device pitch, faint context.
    ax.axhline(half_gap_mV, color="0.6", ls=":", lw=0.8, zorder=2)
    ax.text(0.98, half_gap_mV, u"nominal ½-spacing ",
            transform=ax.get_yaxis_transform(), ha="right", va="bottom",
            fontsize=5.5, color="0.6")
    ax.text(0.02, -REPRO_MV, " block reproducibility",
            transform=ax.get_yaxis_transform(), ha="left", va="bottom",
            fontsize=6, color="0.35")

    ax.set_xlim(0.4, 2e7)
    dw_all = np.concatenate([t["dw"][np.isfinite(t["dw"])] for t in tracks])
    lo = min(float(dw_all.min()), -REPRO_MV) - 4.0
    # strict_mV is out of this max now that it is not drawn; it was never the
    # binding term anyway (23 mV against a 110 mV lenient bound).
    top_ref = max(lenient_mV, half_gap_mV)
    ax.set_ylim(lo, (top_ref - 0.15 * lo) / 0.85)
    ax.text(3e4, 0.965, "extrapolated", transform=ax.get_xaxis_transform(),
            ha="center", va="top", fontsize=6, color="0.35")
    _bold_decade_ticks(ax, [0.5, 1.0, 1e1, 1e2, 1e3, 1e5, 1e7],
                       ["0", "1", "10", "100", "10^3", "10^5", "10^7"])
    ax.set_xlabel("Stress cycles")
    ax.set_ylabel(r"$\Delta w$  (mV)")
    return fig, ax, norm, cmap


def fig_read_disturb_single(blocks: pd.DataFrame, probes: pd.DataFrame,
                            curves: pd.DataFrame, outdir: Path,
                            ext: pd.DataFrame | None = None) -> Path:
    """Main-text single panel: how far read stress moves the stored value.

    With the 10^9 workbook present the panel carries the single-target runs and
    nothing else: five stored values from -1.95 V to +0.45 V, each stressed in
    place to 10^9 read cycles, |dw| against cycles, nothing extrapolated. The
    supplementary blocks are left out on purpose -- they were stopped at 10^3
    cycles, which is where the measurement ended, not where the drift did.

    The axis carries the magnitude because that is what the tolerances bound: a
    state is misread whichever way it drifts. Sign is in the workbook and in
    out/extended_1e9_checkpoints.csv for anyone who needs it.

    Without that workbook the figure falls back to the signed blocks and the
    decade extrapolation it drew before the campaign.
    """
    print("\nSingle-panel read-disturb figure")
    strict_mV = TOLERANCE_MV_STRICT
    lenient_mV = TOLERANCE_MV_LENIENT
    half_gap_mV = _half_min_spacing_mV()   # nominal, context only
    ext_tracks = extended_tracks(ext) if ext is not None else []

    if ext_tracks:
        fig, ax, norm, cmap = _single_measured(ext_tracks, strict_mV, lenient_mV)
    else:
        fig, ax, norm, cmap = _single_extrapolated(
            blocks, probes, curves, strict_mV, lenient_mV, half_gap_mV)
    _hide_top_right(ax)

    # The colour key rides on the right of the panel again. Vertical rather
    # than the horizontal strip it was before the split: the stored value is a
    # continuous axis like the two the panel already has, and on the right it
    # reads in the same direction as the y axis beside it.
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, location="right", pad=0.02,
                        fraction=0.055, aspect=20)
    cbar.set_label(r"$V_W$  (V)", fontsize=10, fontweight="bold")
    cbar.ax.tick_params(labelsize=TICK_SIZE - 1, length=2, pad=1)
    cbar.ax.grid(False)        # axes.grid is on globally; not on a colour ramp
    _bold_ticks(cbar.ax)

    png = outdir / "fig_read_disturb_single.png"
    svg = outdir / "fig_read_disturb_single.svg"
    _savefig(fig, png, dpi=300)
    _savefig(fig, svg)
    plt.close(fig)
    print(f"  wrote {png}")
    print(f"  wrote {svg}")
    return png


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    path = Path(argv[0]) if argv else DEFAULT_XLSX
    _apply_style()
    outdir = OUTDIR
    outdir.mkdir(parents=True, exist_ok=True)

    probe, curves, summary = load(path)
    ext = load_extended()
    blocks = build_blocks(probe, summary)
    stat_mask = (
        np.isclose(blocks.C, -0.75)
        & (blocks.n_cycles == 1000)
        & blocks.has_base2
    )
    stat_blocks = blocks.loc[stat_mask].copy()
    stat = additivity(stat_blocks, curves)

    csv_path = outdir / "blocks_derived.csv"
    stat.to_csv(csv_path, index=False)
    print(f"\nWrote {csv_path}  ({len(stat)} rows)")

    _print_stats(stat)

    _purge_pdfs(outdir)
    fig_all_blocks(blocks, probe, curves, outdir)
    _purge_pdfs(outdir)
    fig_statistics(stat, outdir)
    leftover = list(outdir.rglob("*.pdf"))
    if leftover:
        raise AssertionError(f"PDF still present after run: {leftover}")
    print(f"\nStatistics figure → {outdir / 'fig2_statistics.png'}")

    if ext is not None:
        # The CSV keeps every checkpoint that was measured, including the
        # resumed run the figures leave out, so the record stays complete.
        ext_csv = outdir / "extended_1e9_checkpoints.csv"
        first = ext.groupby("run")["cyc"].transform("min")
        ext = ext.assign(in_figures=first <= EXT_FIRST_CYCLE)
        ext.to_csv(ext_csv, index=False)
        print(f"Wrote {ext_csv}  ({len(ext)} rows)")
        _print_extended(extended_tracks(ext))

    fig_main_read_disturb(blocks, stat, probe, curves, outdir, ext=ext)
    fig_read_disturb_single(blocks, probe, curves, outdir, ext=ext)


if __name__ == "__main__":
    main()