#!/usr/bin/env python3
"""
Publication figures for the n=1000 HotpotQA distractor run.

    python plot_q1000_figures.py
    python plot_q1000_figures.py --width 3.4
    python plot_q1000_figures.py --combined
    python plot_q1000_figures.py --with-mechanism

Run this from RAG_MFMIS. Statistics live in the analysis repo and are imported
from ``scripts.analyze_q1000`` (not recomputed here). Figures are written to
this repo's ``figures/``.

``lo``/``hi`` are 95% CIs of the paired difference (MMR - L2); they are never
drawn on an individual arm's mean.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

PLOT_ROOT = Path(__file__).resolve().parent
ANALYSIS_ROOT = PLOT_ROOT.parent / "H_RAG_cuad_v3.0_MMR_deviceModeling"
if not (ANALYSIS_ROOT / "scripts" / "analyze_q1000.py").is_file():
    raise FileNotFoundError(
        f"analysis repo not found at {ANALYSIS_ROOT}\n"
        "Expected sibling folder H_RAG_cuad_v3.0_MMR_deviceModeling "
        "(contains scripts/analyze_q1000.py)."
    )
sys.path.insert(0, str(ANALYSIS_ROOT))

from scripts.analyze_q1000 import ROOT, load_all, analyse  # noqa: E402

# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------
C_L2 = "#0173B2"
C_MMR = "#DE8F05"
C_REF = "#4D4D4D"
C_MATCH = "#2A2A2A"
C_DELTA = "#9A9A9A"

OUTDIR = PLOT_ROOT / "figures"
PREC = ("fp16", "int8", "int4")
GEN_METRICS = ("F1", "EM", "faithfulness")
FILE_STEM = {"F1": "f1", "EM": "em", "faithfulness": "faithfulness"}
HATCH = "///"
DPI = 300


def apply_plot_style() -> None:
    """Match ``plot_fefet_transfer.py``."""
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "0.3",
            "axes.linewidth": 0.8,
            "font.size": 14,
            "axes.labelsize": 16,
            "axes.titlesize": 16,
            "legend.fontsize": 13,
            "xtick.labelsize": 14,
            "ytick.labelsize": 14,
            "hatch.linewidth": 0.22,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def _style_axes(ax: plt.Axes) -> None:
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.8)
        spine.set_color("0.3")
    ax.grid(True, which="major", linestyle="--", linewidth=0.6, color="0.75", zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=14)
    for lab in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
        lab.set_fontweight("bold")


def _save(fig: plt.Figure, stem: Path) -> None:
    stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(stem.with_suffix(".png"), dpi=DPI, facecolor="white", bbox_inches="tight")
    plt.close(fig)


def _retr_row(retr: pd.DataFrame, prefix: str) -> pd.Series:
    hits = retr[retr["metric"].astype(str).str.startswith(prefix)]
    if len(hits) != 1:
        raise KeyError(f"expected one retrieval row starting {prefix!r}, got {len(hits)}")
    return hits.iloc[0]


def _head_row(head: pd.DataFrame, quant: str, metric: str) -> pd.Series:
    hits = head[(head["quantization"] == quant) & (head["metric"] == metric)]
    if len(hits) != 1:
        raise KeyError(f"expected one headline row {quant}/{metric}, got {len(hits)}")
    return hits.iloc[0]


def _mech_row(mech: pd.DataFrame, group: str, quant: str = "int4") -> pd.Series:
    hits = mech[(mech["quantization"] == quant) & (mech["group"] == group)]
    if len(hits) != 1:
        raise KeyError(f"expected one mechanism row {quant}/{group!r}, got {len(hits)}")
    return hits.iloc[0]


def _sig_style(row: pd.Series) -> tuple[str, str]:
    """Return (marker_face, annotation) from table logic. Do not invent a threshold."""
    bonf = str(row.get("bonferroni", "")).strip().lower()
    sig = str(row.get("sig95", "")).strip().lower()
    if bonf == "pass":
        return "filled", "**"
    if sig == "yes":
        return "filled", "*"
    return "open", ""


def _delta_tick(row: pd.Series) -> str:
    return f"{float(row.delta):+.3f}"


def assert_published(tables: dict) -> None:
    """Fail loudly if imported tables drift from the published point estimates."""
    tol = 1e-3
    retr = tables["retrieval"]
    head = tables["headline"]
    mech = tables["mechanism"]

    r = _retr_row(retr, "full support @5")
    assert abs(float(r.l2) - 0.5690) < tol, r.l2
    assert abs(float(r.mmr) - 0.6140) < tol, r.mmr
    assert abs(float(r.delta) - 0.0450) < tol, r.delta
    assert abs(float(r.mcnemar_p) - 3.4e-4) < tol, r.mcnemar_p
    assert int(r.mcnemar_mmr_only) == 99, r.mcnemar_mmr_only
    assert int(r.mcnemar_l2_only) == 54, r.mcnemar_l2_only

    f1 = _head_row(head, "int4", "F1")
    assert abs(float(f1.l2) - 0.5612) < tol, f1.l2
    assert abs(float(f1.mmr) - 0.5958) < tol, f1.mmr
    assert abs(float(f1.delta) - 0.0347) < tol, f1.delta
    assert str(f1.bonferroni).strip().lower() == "pass", f1.bonferroni

    em = _head_row(head, "int4", "EM")
    assert abs(float(em.l2) - 0.4270) < tol, em.l2
    assert abs(float(em.mmr) - 0.4640) < tol, em.mmr
    assert abs(float(em.delta) - 0.0370) < tol, em.delta
    assert str(em.bonferroni).strip().lower() == "pass", em.bonferroni

    f1p = _head_row(head, "fp16", "F1")
    assert abs(float(f1p.l2) - 0.5960) < tol, f1p.l2
    assert abs(float(f1p.mmr) - 0.6155) < tol, f1p.mmr

    m = _mech_row(mech, "RETRIEVAL-MATCHED (both+neither)")
    assert int(m.n) == 847, m.n
    assert abs(float(m.delta) - 0.0092) < tol, m.delta
    assert str(m.sig95).strip().lower() == "no", m.sig95


def print_ci_table(head: pd.DataFrame) -> None:
    """Paired-difference CIs for the LaTeX caption. Never drawn on arm means."""
    print()
    print("caption CI table (paired Delta = MMR - L2, 95% CI):")
    print("** survives Bonferroni at 0.05/20; * 95% CI excludes zero only")
    for metric in GEN_METRICS:
        for q in PREC:
            row = _head_row(head, q, metric)
            d, lo, hi = float(row.delta), float(row.lo), float(row.hi)
            _, star = _sig_style(row)
            tag = f" {star}" if star else ""
            print(
                f"{metric:<13} {q:<5}  "
                f"Δ {d:+.4f} [{lo:+.4f}, {hi:+.4f}]{tag}"
            )


# ---------------------------------------------------------------------------
# Retrieval: paired bars + centroid-breadth strip (no mechanism panel)
# ---------------------------------------------------------------------------
def plot_retrieval(tables: dict, outdir: Path) -> None:
    retr = tables["retrieval"]
    specs = [
        ("full support @5 (both gold paragraphs)", "full support @5", False),
        ("gold recall @5", "gold recall @5", False),
        ("ILD (diversity)", "ILD (diversity)", True),
        ("RR (near-duplicate rate)", "RR (near-dup. rate)  ↓", True),
        ("ROUGE-L of retrieved text", "ROUGE-L (retrieved)", True),
    ]
    rows = [_retr_row(retr, p) for p, *_ in specs]
    breadth = _retr_row(retr, "centroid breadth")
    full = rows[0]

    fig = plt.figure(figsize=(6.5, 5.0), layout="constrained")
    gs = fig.add_gridspec(2, 1, height_ratios=[5.4, 1.35], hspace=0.12)
    ax_a = fig.add_subplot(gs[0])
    ax_br = fig.add_subplot(gs[1])

    y = np.arange(len(specs))
    h = 0.32
    for i, (row, spec) in enumerate(zip(rows, specs)):
        agg = spec[2]
        hatch = HATCH if agg else ""
        edge = "#8A8A8A" if agg else "white"
        ax_a.barh(
            i + h / 2, float(row.l2), height=h, color=C_L2, edgecolor=edge,
            linewidth=0.35, hatch=hatch, zorder=3,
        )
        ax_a.barh(
            i - h / 2, float(row.mmr), height=h, color=C_MMR, edgecolor=edge,
            linewidth=0.35, hatch=hatch, zorder=3,
        )

    ax_a.set_yticks(y)
    ax_a.set_yticklabels([s[1] for s in specs])
    ax_a.set_xlabel("score (0-1)")
    ax_a.set_xlim(0.0, 1.0)
    ax_a.set_ylim(-0.55, len(specs) - 0.40)
    ax_a.invert_yaxis()
    _style_axes(ax_a)

    ax_a.legend(
        handles=[
            Patch(facecolor=C_L2, edgecolor="none", label="L2"),
            Patch(facecolor=C_MMR, edgecolor="none", label="MMR"),
            Patch(
                facecolor="0.88", edgecolor="#9A9A9A", hatch=HATCH, linewidth=0.25,
                label="aggregate (no CI)",
            ),
        ],
        loc="best", framealpha=0.9,
    )

    ax_br.barh(
        0.18, float(breadth.l2), height=0.32, color=C_L2, edgecolor="#8A8A8A",
        linewidth=0.25, hatch=HATCH, zorder=3,
    )
    ax_br.barh(
        -0.18, float(breadth.mmr), height=0.32, color=C_MMR, edgecolor="#8A8A8A",
        linewidth=0.25, hatch=HATCH, zorder=3,
    )
    ax_br.set_yticks([0])
    ax_br.set_yticklabels(["centroid breadth"])
    ax_br.set_xlabel("mean # centroids")
    ax_br.set_xlim(0, 3.2)
    ax_br.set_ylim(-0.55, 0.55)
    _style_axes(ax_br)

    p_str = f"{float(full.mcnemar_p):.1e}".replace("e-0", "e-")
    ax_br.text(
        0.0, -0.18,
        f"McNemar: MMR-only {int(full.mcnemar_mmr_only)} vs "
        f"L2-only {int(full.mcnemar_l2_only)},  p = {p_str}",
        transform=ax_br.transAxes, ha="left", va="top",
        fontsize=12, color="0.45",
    )

    _save(fig, outdir / "fig_retrieval_q1000")
    print("caption retrieval - Measured once, before generation; independent of "
          "the generator and its precision. Hatched bars are corpus aggregates "
          "(ILD, RR, ROUGE-L, centroid breadth) with no CI. RR: lower is better. "
          "Centroid breadth has its own axis because it is not a 0-1 score.")


# ---------------------------------------------------------------------------
# Mechanism forest (opt-in)
# ---------------------------------------------------------------------------
def plot_mechanism(tables: dict, outdir: Path) -> None:
    mech = tables["mechanism"]
    order = [
        "MMR-only full",
        "L2-only full",
        "both arms full",
        "neither arm full",
        "RETRIEVAL-MATCHED (both+neither)",
    ]
    short = {
        "MMR-only full": "MMR-only full",
        "L2-only full": "L2-only full",
        "both arms full": "both arms full",
        "neither arm full": "neither arm full",
        "RETRIEVAL-MATCHED (both+neither)": "RETRIEVAL-MATCHED",
    }
    mech_rows = [_mech_row(mech, g) for g in order]
    yy = np.arange(len(order))[::-1]

    fig, ax = plt.subplots(figsize=(6.5, 4.5), layout="constrained")

    ax.axvline(0.0, color=C_REF, lw=0.9, zorder=1)
    ax.axhspan(yy[4] - 0.42, yy[4] + 0.42, color="#F0F0F0", zorder=0)
    ax.axhline(yy[4] + 0.48, color="#C8C8C8", lw=0.7, zorder=1)

    for i, (g, row) in enumerate(zip(order, mech_rows)):
        d, lo, hi = float(row.delta), float(row.lo), float(row.hi)
        matched = g.startswith("RETRIEVAL-MATCHED")
        color = C_MATCH if matched else C_L2
        ax.errorbar(
            d, yy[i],
            xerr=[[d - lo], [hi - d]],
            fmt="o", color=color, ecolor=color,
            elinewidth=1.7 if matched else 1.1,
            capsize=2.2,
            markersize=6.0 if matched else 4.5,
            markerfacecolor=color, markeredgecolor=color, zorder=4,
        )
        ax.text(
            0.56, yy[i], f"n={int(row.n)}",
            ha="left", va="center", fontsize=13,
            fontweight="bold" if matched else "normal",
            color=C_MATCH if matched else "0.25",
        )

    ax.set_yticks(yy)
    ax.set_yticklabels([short[g] for g in order])
    for lab, g in zip(ax.get_yticklabels(), order):
        if g.startswith("RETRIEVAL-MATCHED"):
            lab.set_fontweight("bold")
            lab.set_color(C_MATCH)
    ax.set_xlim(-0.45, 0.72)
    ax.set_ylim(-0.65, len(order) - 0.35)
    ax.set_xlabel("Δ F1  (MMR − L2),  95% CI")
    _style_axes(ax)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)

    _save(fig, outdir / "fig_mechanism_q1000")
    print("caption mechanism - int4 F1 split by which arm retrieved both gold "
          "paragraphs. When retrieval is matched (n=847) the generation gap is "
          "indistinguishable from zero, so the accuracy gain is retrieval-side.")


# ---------------------------------------------------------------------------
# Generation: one axes per metric
# ---------------------------------------------------------------------------
def _pt_to_data_y(ax: plt.Axes, pts: float) -> float:
    """Convert a vertical offset in typographic points to y-data units."""
    bbox = ax.get_position()
    ax_h_pt = bbox.height * ax.figure.get_size_inches()[1] * 72.0
    y0, y1 = ax.get_ylim()
    return abs(y1 - y0) * pts / ax_h_pt if ax_h_pt else 0.0


def _draw_generation_axes(
    ax: plt.Axes, head: pd.DataFrame, metric: str, *, delta_row: bool = True,
) -> None:
    x = np.arange(len(PREC))
    l2 = [float(_head_row(head, q, metric).l2) for q in PREC]
    mmr = [float(_head_row(head, q, metric).mmr) for q in PREC]

    ax.plot(
        x, l2, "-o", color=C_L2, lw=1.4, markersize=4,
        markerfacecolor=C_L2, markeredgecolor=C_L2, zorder=3, label="L2",
    )
    ax.plot(
        x, mmr, "-s", color=C_MMR, lw=1.4, markersize=4,
        markerfacecolor=C_MMR, markeredgecolor=C_MMR, zorder=3, label="MMR",
    )

    if metric in ("F1", "EM"):
        base = float(_head_row(head, "fp16", metric).l2)
        ax.axhline(base, color=C_REF, ls="--", lw=1.0, zorder=1)
        

    ys = l2 + mmr
    ylo, yhi = min(ys), max(ys)
    margin = 0.08 * (yhi - ylo) if yhi > ylo else 0.01
    ax.set_xticks(x)
    ax.set_xticklabels(PREC)
    ax.set_xlim(-0.28, 2.28)
    ax.set_ylim(ylo - margin, yhi + margin)
    ax.set_ylabel(metric)
    ax.set_xlabel("precision")
    _style_axes(ax)

    if delta_row:
        gap = _pt_to_data_y(ax, 2.5)  # marker radius (~2 pt) + ~0.5 pt air
        for i, q in enumerate(PREC):
            y_lo, y_hi = (l2[i], mmr[i]) if l2[i] < mmr[i] else (mmr[i], l2[i])
            if y_hi - y_lo > 2 * gap:
                ax.plot(
                    [i, i], [y_lo + gap, y_hi - gap],
                    color=C_DELTA, lw=0.8, solid_capstyle="butt", zorder=2,
                )
            mid = 0.5 * (l2[i] + mmr[i])
            row = _head_row(head, q, metric)
            # int4: flip left so the label does not run past the right spine
            if i == len(PREC) - 1:
                dx, ha = -4, "right"
            else:
                dx, ha = 4, "left"
            ax.annotate(
                _delta_tick(row),
                xy=(i, mid),
                xytext=(dx, 0),
                textcoords="offset points",
                ha=ha, va="center",
                fontsize=13, fontweight="bold", color=C_REF, zorder=4,
            )

    legend_loc = {
        "F1": "lower left",
        "EM": "lower left",
        "faithfulness": "lower left",
    }[metric]
    ax.legend(loc=legend_loc, framealpha=0.9)


def plot_generation_single(tables: dict, outdir: Path, width: float) -> None:
    head = tables["headline"]
    height = width * (4.5 / 6.5)
    for metric in GEN_METRICS:
        fig, ax = plt.subplots(figsize=(width, height), layout="constrained")
        _draw_generation_axes(ax, head, metric)
        stem = outdir / f"fig_generation_{FILE_STEM[metric]}"
        _save(fig, stem)
        print(f"wrote {stem.with_suffix('.png')}")


def plot_generation_combined(tables: dict, outdir: Path) -> None:
    """Absolute levels only, three panels. No Delta row. Opt-in via --combined."""
    head = tables["headline"]
    fig, axes = plt.subplots(
        1, 3, figsize=(7.0, 3.2), layout="constrained",
    )
    for ax, metric in zip(axes, GEN_METRICS):
        _draw_generation_axes(ax, head, metric, delta_row=False)
    _save(fig, outdir / "fig_generation_q1000")
    print(f"wrote {(outdir / 'fig_generation_q1000').with_suffix('.png')}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--width", type=float, default=6.5,
        help="width in inches of each single-metric generation figure (default 6.5)",
    )
    parser.add_argument(
        "--combined", action="store_true",
        help="also write the 3-panel absolute-level figure fig_generation_q1000",
    )
    parser.add_argument(
        "--with-mechanism", action="store_true",
        help="write the int4 retrieval-mechanism forest plot",
    )
    args = parser.parse_args()

    apply_plot_style()
    print("Loading cached per-query tables (rebuild=False) ...")
    perq, faith, retr, _official = load_all(ROOT, rebuild=False)
    tables = analyse(ROOT, perq, faith, retr)
    assert_published(tables)
    print("published-value asserts: OK")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    plot_retrieval(tables, OUTDIR)
    plot_generation_single(tables, OUTDIR, width=args.width)
    if args.combined:
        plot_generation_combined(tables, OUTDIR)
    if args.with_mechanism:
        plot_mechanism(tables, OUTDIR)
    print_ci_table(tables["headline"])
    print(f"wrote {OUTDIR / 'fig_retrieval_q1000.png'}")


if __name__ == "__main__":
    main()
