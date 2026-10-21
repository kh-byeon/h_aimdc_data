"""Draw paper tables into a caller-owned axes (no figure, no save).

Statistics are imported from scripts.make_paper_tables in the analysis repo;
this module only typesets. Default PAPER_RUN=q1000 (fp16/int8/int4, one index).
A thin wrapper ``save_table_figure`` sizes one figure per block and writes a PNG.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

PLOT_ROOT = Path(__file__).resolve().parent
ANALYSIS_ROOT = PLOT_ROOT.parent / "H_RAG_cuad_v3.0_MMR_deviceModeling"
if not (ANALYSIS_ROOT / "scripts" / "make_paper_tables.py").is_file():
    raise FileNotFoundError(
        f"analysis repo not found at {ANALYSIS_ROOT}\n"
        "Expected sibling folder H_RAG_cuad_v3.0_MMR_deviceModeling "
        "(contains scripts/make_paper_tables.py)."
    )
if str(ANALYSIS_ROOT) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_ROOT))

from scripts.make_paper_tables import RUN, QUANTS, generation, retrieval

MINUS = "\u2212"
PT_PER_IN = 72.0
MM_PER_IN = 25.4
PNG_DPI = 600.0
MARGIN_MM = 2.0
MARGIN_PT = MARGIN_MM / MM_PER_IN * PT_PER_IN

# Gaps are multiples of row pitch, except row pitch itself (1.5 × fontsize).
TITLE_TO_RULE = 0.7
ABOVE_SUBHEAD = 0.6
SUBHEAD_TO_ROW = 0.25
BETWEEN_GROUPS = 0.35
RULE_TO_FOOTNOTE = 0.5
RULE_TO_TEXT = 0.20          # booktabs pad around header / last row
PAD_AFTER_METRIC_PT = 10.0   # metric labels → first following column
COLSEP_PT = 10.0              # between packed columns
SUBHEAD_COLOR = "#3A3A3A"

_CACHE: dict = {}
_MEAS_CACHE: dict[tuple, float] = {}
_MEAS_FIG: Figure | None = None


def _data():
    if not _CACHE:
        _CACHE["retr"] = retrieval()
        _CACHE["gen"] = generation()
    return _CACHE["retr"], _CACHE["gen"]


def _plain(name: str) -> str:
    return (
        name.replace(r" $\uparrow$", " \u2191")
        .replace(r" $\downarrow$", " \u2193")
        .replace("$\\uparrow$", "\u2191")
        .replace("$\\downarrow$", "\u2193")
    )


def _fmt(v, dp=3) -> str:
    return f"{v:.{dp}f}".replace("-", MINUS)


def _signed(v, dp=3) -> str:
    return f"{v:+.{dp}f}".replace("-", MINUS)


def _font(size: float, weight: str = "normal", style: str = "normal") -> FontProperties:
    return FontProperties(family="Arial", size=size, weight=weight, style=style)


def _meas_renderer():
    global _MEAS_FIG
    if _MEAS_FIG is None:
        _MEAS_FIG = Figure(figsize=(8, 2), dpi=150)
        FigureCanvasAgg(_MEAS_FIG)
    return _MEAS_FIG, _MEAS_FIG.canvas.get_renderer()


def _text_width_pt(s: str, fontsize: float, weight: str = "normal",
                   style: str = "normal") -> float:
    key = (s, fontsize, weight, style)
    if key in _MEAS_CACHE:
        return _MEAS_CACHE[key]
    fig, renderer = _meas_renderer()
    t = fig.text(0, 0, s, fontproperties=_font(fontsize, weight, style))
    bb = t.get_window_extent(renderer=renderer)
    t.remove()
    w = float(bb.width) * PT_PER_IN / fig.dpi
    _MEAS_CACHE[key] = w
    return w


@dataclass
class _Cell:
    x: float
    y: float
    text: str
    ha: str
    fontsize: float
    weight: str = "normal"
    style: str = "normal"
    color: str = "black"
    va: str = "center"


@dataclass
class _Rule:
    y: float
    lw: float
    x0: float
    x1: float


@dataclass
class _Layout:
    width_pt: float
    height_pt: float
    cells: list[_Cell] = field(default_factory=list)
    rules: list[_Rule] = field(default_factory=list)
    col_x: tuple[float, ...] = ()


def _pack_columns(left_groups: list[list[tuple[str, float, str, str]]],
                  right_groups: list[list[tuple[str, float, str, str]]],
                  x0: float) -> tuple[list[float], list[float], float]:
    """Pack left-aligned groups then right-aligned groups. Returns (x_left, x_right, x_end)."""
    x = x0
    x_left: list[float] = []
    for i, group in enumerate(left_groups):
        w = max((_text_width_pt(s, fs, wt, st) for s, fs, wt, st in group), default=0.0)
        x_left.append(x)
        pad = PAD_AFTER_METRIC_PT if i == 0 else COLSEP_PT
        x += w + pad
    x_right: list[float] = []
    for i, group in enumerate(right_groups):
        w = max((_text_width_pt(s, fs, wt, st) for s, fs, wt, st in group), default=0.0)
        x += w
        x_right.append(x)
        if i < len(right_groups) - 1:
            x += COLSEP_PT
    return x_left, x_right, x


def _layout_retrieval(fontsize: float, header_fontsize: float,
                      thick: float, thin: float, title: str | None) -> _Layout:
    coverage, diversity, _rs = _data()[0]
    pitch = 1.5 * fontsize
    fs, hfs = fontsize, header_fontsize

    cov_rows = []
    for name, a, b, bold in coverage:
        pct = 100.0 * (b - a) / a
        cov_rows.append((_plain(name), _fmt(a), _fmt(b), _signed(pct, 1), bold))
    div_rows = []
    for name, a, b, bold in diversity:
        pct = 100.0 * (b - a) / a
        div_rows.append((_plain(name), _fmt(a), _fmt(b), _signed(pct, 1), bold))

    headers = ("Metric", "L2", "MMR", "\u0394 (%)")
    subheads = ("Evidence coverage", "Diversity of the retrieved set")
    indent = 1.5 * _text_width_pt("0", fs)
    w_metric = max(
        _text_width_pt(headers[0], hfs, "bold"),
        max(_text_width_pt(s, fs, style="italic") for s in subheads),
        indent + max(_text_width_pt(r[0], fs) for r in cov_rows + div_rows),
    )
    l2_strs = [(headers[1], hfs, "bold", "normal")] + [
        (r[1], fs, "normal", "normal") for r in cov_rows + div_rows
    ]
    mmr_strs = [(headers[2], hfs, "bold", "normal")] + [
        (r[2], fs, "bold", "normal") for r in cov_rows + div_rows
    ]
    pct_strs = [(headers[3], hfs, "bold", "normal")] + [
        (r[3], fs, "normal", "normal") for r in cov_rows + div_rows
    ]

    x0 = MARGIN_PT
    x_metric = x0
    _, x_right, x_end = _pack_columns(
        [], [l2_strs, mmr_strs, pct_strs], x_metric + w_metric + PAD_AFTER_METRIC_PT,
    )
    x_l2, x_mmr, x_pct = x_right
    width_pt = x_end + MARGIN_PT

    cells: list[_Cell] = []
    rules: list[_Rule] = []
    y_top = 0.0  # running distance from the top of the figure

    def y_mpl(y_from_top: float, height: float) -> float:
        return height - y_from_top

    # We don't know height yet; accumulate from-top positions, then flip.
    placed: list[tuple[str, object]] = []

    def skip(dy: float) -> None:
        nonlocal y_top
        y_top += dy

    def add_text(x, y_from_top, text, ha, fontsize, weight="normal", style="normal",
                 color="black", va="center"):
        placed.append(("cell", _Cell(x, y_from_top, text, ha, fontsize, weight, style, color, va)))

    def add_rule(y_from_top, lw):
        placed.append(("rule", _Rule(y_from_top, lw, x0, x_end)))

    skip(MARGIN_PT)
    if title:
        add_text(x_metric, y_top, title, "left", hfs, "bold", va="top")
        skip(hfs)
        skip(TITLE_TO_RULE * pitch)
    add_rule(y_top, thick)
    skip(RULE_TO_TEXT * pitch)
    add_text(x_metric, y_top + 0.5 * hfs, headers[0], "left", hfs, "bold")
    add_text(x_l2, y_top + 0.5 * hfs, headers[1], "right", hfs, "bold")
    add_text(x_mmr, y_top + 0.5 * hfs, headers[2], "right", hfs, "bold")
    add_text(x_pct, y_top + 0.5 * hfs, headers[3], "right", hfs, "bold")
    skip(hfs)
    skip(RULE_TO_TEXT * pitch)
    add_rule(y_top, thin)

    def section(label: str, rows: list) -> None:
        nonlocal y_top
        skip(ABOVE_SUBHEAD * pitch)
        add_text(x_metric, y_top + 0.5 * fs, label, "left", fs,
                 style="italic", color=SUBHEAD_COLOR)
        skip(fs)
        skip(SUBHEAD_TO_ROW * pitch)
        for i, (lab, sa, sb, sp, _bold) in enumerate(rows):
            yc = y_top + 0.5 * fs
            add_text(x_metric + indent, yc, lab, "left", fs)
            add_text(x_l2, yc, sa, "right", fs)
            add_text(x_mmr, yc, sb, "right", fs, "bold")
            add_text(x_pct, yc, sp, "right", fs)
            if i < len(rows) - 1:
                skip(pitch)
            else:
                skip(fs)

    section("Evidence coverage", cov_rows)
    section("Diversity of the retrieved set", div_rows)

    skip(RULE_TO_TEXT * pitch)
    add_rule(y_top, thick)
    skip(MARGIN_PT)

    height_pt = y_top
    cells_out: list[_Cell] = []
    rules_out: list[_Rule] = []
    for kind, obj in placed:
        if kind == "cell":
            c = obj
            cells_out.append(_Cell(
                c.x, height_pt - c.y, c.text, c.ha, c.fontsize,
                c.weight, c.style, c.color, c.va,
            ))
        else:
            r = obj
            rules_out.append(_Rule(height_pt - r.y, r.lw, r.x0, r.x1))
    return _Layout(
        width_pt, height_pt, cells_out, rules_out,
        col_x=(x_metric, x_l2, x_mmr, x_pct),
    )


def _layout_quantization(fontsize: float, header_fontsize: float,
                         thick: float, thin: float, title: str | None) -> _Layout:
    gen, _did = _data()[1]
    q_ref, q_last = QUANTS[0], QUANTS[-1]
    pitch = 1.5 * fontsize
    fs, hfs = fontsize, header_fontsize
    chg_header = "\u0394 (%)"
    headers = ("Metric", "Retriever", *QUANTS, chg_header)

    metric_labels = [label for label, _arms in gen]
    metric_strs = (
        [(headers[0], hfs, "bold", "normal")]
        + [(lab, fs, "normal", "normal") for lab in metric_labels]
    )
    retr_strs = [(headers[1], hfs, "bold", "normal"), ("L2", fs, "normal", "normal"),
                 ("MMR", fs, "normal", "normal")]
    val_strs = {q: [(q, hfs, "bold", "normal")] for q in QUANTS}
    chg_strs = [(chg_header, hfs, "bold", "normal")]
    for _label, arms in gen:
        for arm in ("L2", "MMR"):
            for q in QUANTS:
                w = "bold" if (arm == "MMR" and q in ("fp16", "int4")) else "normal"
                val_strs[q].append((_fmt(arms[arm]["absv"][q]), fs, w, "normal"))
            chg_strs.append((_signed(arms[arm]["rel"][q_last], 2), fs, "normal", "normal"))

    x0 = MARGIN_PT
    x_left, x_right, x_end = _pack_columns(
        [metric_strs, retr_strs],
        [val_strs[q] for q in QUANTS] + [chg_strs],
        x0,
    )
    x_metric, x_retr = x_left
    x_vals = x_right[:-1]
    x_chg = x_right[-1]
    width_pt = x_end + MARGIN_PT

    placed: list[tuple[str, object]] = []
    y_top = 0.0

    def skip(dy: float) -> None:
        nonlocal y_top
        y_top += dy

    def add_text(x, y_from_top, text, ha, fontsize, weight="normal", style="normal",
                 color="black", va="center"):
        placed.append(("cell", _Cell(x, y_from_top, text, ha, fontsize, weight, style, color, va)))

    def add_rule(y_from_top, lw):
        placed.append(("rule", _Rule(y_from_top, lw, x0, x_end)))

    skip(MARGIN_PT)
    if title:
        add_text(x_metric, y_top, title, "left", hfs, "bold", va="top")
        skip(hfs)
        skip(TITLE_TO_RULE * pitch)
    add_rule(y_top, thick)
    skip(RULE_TO_TEXT * pitch)
    yc_h = y_top + 0.5 * hfs
    add_text(x_metric, yc_h, headers[0], "left", hfs, "bold")
    add_text(x_retr, yc_h, headers[1], "left", hfs, "bold")
    for q, xq in zip(QUANTS, x_vals):
        add_text(xq, yc_h, q, "right", hfs, "bold")
    add_text(x_chg, yc_h, chg_header, "right", hfs, "bold")
    skip(hfs)
    skip(RULE_TO_TEXT * pitch)
    add_rule(y_top, thin)
    skip(RULE_TO_TEXT * pitch)

    n_metrics = len(gen)
    for m_i, (label, arms) in enumerate(gen):
        for a_i, arm in enumerate(("L2", "MMR")):
            yc = y_top + 0.5 * fs
            if a_i == 0:
                add_text(x_metric, yc, label, "left", fs)
            add_text(x_retr, yc, arm, "left", fs)
            for q, xq in zip(QUANTS, x_vals):
                w = "bold" if (arm == "MMR" and q in ("fp16", "int4")) else "normal"
                add_text(xq, yc, _fmt(arms[arm]["absv"][q]), "right", fs, w)
            add_text(x_chg, yc, _signed(arms[arm]["rel"][q_last], 2), "right", fs)
            if a_i == 0:
                skip(pitch)
            else:
                skip(fs)
        if m_i < n_metrics - 1:
            skip(BETWEEN_GROUPS * pitch)

    skip(RULE_TO_TEXT * pitch)
    add_rule(y_top, thick)
    skip(MARGIN_PT)

    height_pt = y_top
    cells_out: list[_Cell] = []
    rules_out: list[_Rule] = []
    for kind, obj in placed:
        if kind == "cell":
            c = obj
            cells_out.append(_Cell(
                c.x, height_pt - c.y, c.text, c.ha, c.fontsize,
                c.weight, c.style, c.color, c.va,
            ))
        else:
            r = obj
            rules_out.append(_Rule(height_pt - r.y, r.lw, r.x0, r.x1))
    return _Layout(
        width_pt, height_pt, cells_out, rules_out,
        col_x=(x_metric, x_retr, *x_vals, x_chg),
    )


def compute_layout(block: str, *, fontsize: float = 7, header_fontsize: float = 7,
                   rule_lw: tuple[float, float] = (1.0, 0.5),
                   title: str | None = None) -> _Layout:
    thick, thin = rule_lw
    if block == "retrieval":
        return _layout_retrieval(fontsize, header_fontsize, thick, thin, title)
    if block == "quantization":
        return _layout_quantization(fontsize, header_fontsize, thick, thin, title)
    raise ValueError(f"unknown block {block!r}; expected 'retrieval' or 'quantization'")


def _paint(ax, lay: _Layout) -> None:
    ax.set_axis_off()
    ax.set_xlim(0, lay.width_pt)
    ax.set_ylim(0, lay.height_pt)
    for r in lay.rules:
        ax.plot(
            [r.x0, r.x1], [r.y, r.y],
            color="black", lw=r.lw, solid_capstyle="butt", clip_on=False,
        )
    for c in lay.cells:
        ax.text(
            c.x, c.y, c.text,
            ha=c.ha, va=c.va,
            fontsize=c.fontsize,
            fontweight=c.weight,
            fontstyle=c.style,
            color=c.color,
            fontproperties=_font(c.fontsize, c.weight, c.style),
            clip_on=False,
        )


def draw_table_panel(ax, block, *, fontsize=7, header_fontsize=7,
                     rule_lw=(1.0, 0.5), col_x=None, title=None):
    """Render one tabular block into `ax`. Creates no figure, saves nothing.

    Draws in point coordinates; the wrapper sizes the figure to the layout.
    ``col_x`` is accepted for signature compatibility and is ignored — each
    block packs its own columns from text extents.
    returns: the packed column x positions actually used.
    """
    del col_x  # packed per block; no shared grid
    lay = compute_layout(
        block, fontsize=fontsize, header_fontsize=header_fontsize,
        rule_lw=rule_lw, title=title,
    )
    _paint(ax, lay)
    return lay.col_x


def save_table_figure(
    block: str,
    out_dir: Path,
    *,
    stem: str | None = None,
    title: str | None = None,
    fontsize: float = 7,
    header_fontsize: float = 7,
    rule_lw: tuple[float, float] = (1.0, 0.5),
) -> tuple[Path, tuple[float, float]]:
    """One figure per block, sized to packed content. PNG @ 600 dpi."""
    if stem is None:
        stem = f"fig_table_{block}"
    lay = compute_layout(
        block, fontsize=fontsize, header_fontsize=header_fontsize,
        rule_lw=rule_lw, title=title,
    )
    w_in = lay.width_pt / PT_PER_IN
    h_in = lay.height_pt / PT_PER_IN
    fig, ax = plt.subplots(figsize=(w_in, h_in))
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    _paint(ax, lay)

    out_dir.mkdir(parents=True, exist_ok=True)
    png = out_dir / f"{stem}.png"
    fig.savefig(png, dpi=PNG_DPI, facecolor="white")
    plt.close(fig)
    w_mm = w_in * MM_PER_IN
    h_mm = h_in * MM_PER_IN
    return png, (w_mm, h_mm)
