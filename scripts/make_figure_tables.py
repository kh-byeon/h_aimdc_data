#!/usr/bin/env python3
"""Standalone table figures (one file per block). Default PAPER_RUN=q1000.

    PAPER_RUN=q1000 python scripts/make_figure_tables.py
    PAPER_RUN=q3500 python scripts/plot_tables_png.py

Writes figures/fig_table_retrieval.png and figures/fig_table_quantization.png.
Statistics come from scripts.make_paper_tables in the analysis repo; they are
not recomputed here.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib import rcParams

PLOT_ROOT = Path(__file__).resolve().parent.parent
ANALYSIS_ROOT = PLOT_ROOT.parent / "H_RAG_cuad_v3.0_MMR_deviceModeling"
sys.path.insert(0, str(PLOT_ROOT))

from table_panel import PNG_DPI, QUANTS, RUN, _data, save_table_figure

OUT_DIR = PLOT_ROOT / "figures"
TICK = 7


def _assert_close(got, exp, name, tol=1e-3):
    if abs(got - exp) > tol:
        raise AssertionError(f"{name}: got {got}, expected {exp} (tol {tol})")


def _assert_stats(cov, div, gen, rs):
    fs = next(r for r in cov if r[0] == "Full support @5")
    if RUN["n"] == 1000:
        _assert_close(fs[1], 0.569, "retrieval Full support @5 L2")
        _assert_close(fs[2], 0.614, "retrieval Full support @5 MMR")
        if rs["only_mmr"] != 99 or rs["only_l2"] != 54:
            raise AssertionError(
                f"retrieval McNemar {rs['only_mmr']} vs {rs['only_l2']}, expected 99 vs 54"
            )

        f1_arms = next(arms for label, arms in gen if label == "Answer F1")
        _assert_close(f1_arms["L2"]["absv"]["fp16"], 0.596, "quantization Answer F1 L2 fp16")
        _assert_close(f1_arms["L2"]["absv"]["int8"], 0.595, "quantization Answer F1 L2 int8")
        _assert_close(f1_arms["L2"]["absv"]["int4"], 0.561, "quantization Answer F1 L2 int4")
        _assert_close(round(f1_arms["L2"]["rel"]["int4"], 2), -5.84, "quantization Answer F1 L2 change %")
        _assert_close(f1_arms["MMR"]["absv"]["fp16"], 0.616, "quantization Answer F1 MMR fp16")
        _assert_close(f1_arms["MMR"]["absv"]["int8"], 0.615, "quantization Answer F1 MMR int8")
        _assert_close(f1_arms["MMR"]["absv"]["int4"], 0.596, "quantization Answer F1 MMR int4")
        _assert_close(round(f1_arms["MMR"]["rel"]["int4"], 2), -3.19, "quantization Answer F1 MMR change %")

        em_arms = next(arms for label, arms in gen if label == "Exact match")
        _assert_close(em_arms["MMR"]["absv"]["fp16"], 0.485, "quantization Exact match MMR fp16")
        _assert_close(em_arms["MMR"]["absv"]["int8"], 0.482, "quantization Exact match MMR int8")
        _assert_close(em_arms["MMR"]["absv"]["int4"], 0.464, "quantization Exact match MMR int4")
        _assert_close(round(em_arms["MMR"]["rel"]["int4"], 2), -4.33, "quantization Exact match MMR change %")

        fa_arms = next(arms for label, arms in gen if label == "Faithfulness")
        if not fa_arms["_sig"].get("int4"):
            raise AssertionError(
                f"quantization Faithfulness _sig must be True at int4 for n=1000; "
                f"got {fa_arms['_sig']}"
            )
        return

    if RUN["n"] == 3500:
        _assert_close(fs[1], 0.565, "retrieval Full support @5 L2")
        _assert_close(fs[2], 0.596, "retrieval Full support @5 MMR")
        pct = 100.0 * (fs[2] - fs[1]) / fs[1]
        _assert_close(round(pct, 1), 5.5, "retrieval Full support @5 Δ%")

        br = next(r for r in div if "Centroid breadth" in r[0])
        _assert_close(br[1], 2.435, "retrieval Centroid breadth L2")
        _assert_close(br[2], 2.669, "retrieval Centroid breadth MMR")

        q0, q1 = QUANTS[0], QUANTS[-1]
        f1_arms = next(arms for label, arms in gen if label == "Answer F1")
        if "int8" in f1_arms["L2"]["absv"]:
            _assert_close(f1_arms["L2"]["absv"]["int8"], 0.581, "quantization Answer F1 L2 int8")
        if "int4" in f1_arms["L2"]["absv"]:
            _assert_close(f1_arms["L2"]["absv"]["int4"], 0.561, "quantization Answer F1 L2 int4")
        if q0 == "int8" and q1 == "int4":
            _assert_close(round(f1_arms["L2"]["rel"][q1], 2), -3.41, "quantization Answer F1 L2 change %")

        fa_arms = next(arms for label, arms in gen if label == "Faithfulness")
        if "int8" in fa_arms["MMR"]["absv"]:
            _assert_close(fa_arms["MMR"]["absv"]["int8"], 0.907, "quantization Faithfulness MMR int8")
        if "int4" in fa_arms["MMR"]["absv"]:
            _assert_close(fa_arms["MMR"]["absv"]["int4"], 0.838, "quantization Faithfulness MMR int4")
        if q0 == "int8" and q1 == "int4":
            _assert_close(round(fa_arms["MMR"]["rel"][q1], 2), -7.63, "quantization Faithfulness MMR change %")
        bad_sig = [q for q in QUANTS if fa_arms["_sig"].get(q)]
        if bad_sig:
            raise AssertionError(
                f"quantization Faithfulness _sig must be False at every precision; "
                f"True at {bad_sig}: {fa_arms['_sig']}"
            )
        if list(QUANTS) != ["int8", "int4"]:
            raise AssertionError(f"n=3500 tables must be two-column, got QUANTS={QUANTS}")
        return

    raise AssertionError(f"no asserts registered for RUN n={RUN['n']}")


def _sci_p(p: float) -> str:
    if p >= 1e-3:
        return f"{p:.3f}"
    e = int(f"{p:.1e}".split("e")[1])
    sup = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")
    return f"{p / 10 ** e:.1f} \u00d7 10{str(e).translate(sup)}"


def _legend_retrieval(rs) -> str:
    n = RUN["n"]
    p_str = _sci_p(rs["p"])
    return (
        f"Retrieval legend. Centre values are means over n = {n} HotpotQA queries. "
        "Intervals (not shown in the table) are 95% CIs from a paired bootstrap "
        "over queries, 20,000 resamples. Intra-list diversity, near-duplicate rate "
        "and centroid breadth are recorded as corpus aggregates and have no per-query "
        f"confidence interval; all other rows are means over the {n} queries. "
        "Full support @5 was compared with an "
        f"exact McNemar test (MMR-only {rs['only_mmr']} vs L2-only {rs['only_l2']}; "
        f"P = {p_str})."
    )


def _legend_quantization(gen, did) -> str:
    f1 = did["Answer F1"]
    q_ref, q_last = QUANTS[0], QUANTS[-1]
    bits = []
    for label, arms in gen:
        marked = [q for q in QUANTS if arms.get("_sig", {}).get(q)]
        where = ", ".join(marked) if marked else "none"
        bits.append(f"{label} at {where}")
    within = (
        "MMR values are in bold (fp16 and int4 only). "
        "Within-precision MMR versus L2 (paired bootstrap 95% CI excludes zero): "
        f"{'; '.join(bits)}."
    )
    return (
        f"Quantization legend. {within} "
        f"The difference-in-differences of {q_last} versus {q_ref} Answer F1 "
        f"between MMR and L2 is not resolved "
        f"(DID {f1['mu']:+.4f}, 95% CI [{f1['lo']:+.4f}, {f1['hi']:+.4f}], "
        f"P = {f1['p']:.2f})."
    )


PNG_MAGIC = bytes((0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A))


def _png_size_mm(path: Path, dpi: float) -> tuple[float, float]:
    """Physical size of a PNG from its IHDR pixel dimensions (no PIL needed)."""
    import struct
    raw = path.read_bytes()
    if raw[:8] != PNG_MAGIC or raw[12:16] != b"IHDR":
        raise RuntimeError(f"not a PNG with a leading IHDR: {path}")
    w_px, h_px = struct.unpack(">II", raw[16:24])
    return w_px / dpi * 25.4, h_px / dpi * 25.4


def main():
    (coverage, diversity, rs), (gen, did) = _data()
    _assert_stats(coverage, diversity, gen, rs)
    print("asserts ok")

    rcParams["font.family"] = "sans-serif"
    rcParams["font.sans-serif"] = ["Arial", "Helvetica", "DejaVu Sans"]
    rcParams["pdf.fonttype"] = 42
    rcParams["ps.fonttype"] = 42
    rcParams["font.size"] = TICK
    rcParams["axes.unicode_minus"] = True

    jobs = (
        ("retrieval", "fig_table_retrieval", "Retrieval"),
        ("quantization", "fig_table_quantization", "Quantization"),
    )
    for block, stem, title in jobs:
        png, (w_mm, h_mm) = save_table_figure(
            block, OUT_DIR, stem=stem, title=title,
            fontsize=TICK, header_fontsize=TICK,
        )
        box_w, box_h = _png_size_mm(png, PNG_DPI)
        print(
            f"saved {png.relative_to(PLOT_ROOT)}  "
            f"figsize {w_mm:.2f} x {h_mm:.2f} mm  "
            f"png {box_w:.2f} x {box_h:.2f} mm"
        )
        # One pixel at 600 dpi is 0.042 mm, so rounding alone stays inside 0.05 mm.
        if abs(box_w - w_mm) > 0.05 or abs(box_h - h_mm) > 0.05:
            raise AssertionError(
                f"{stem}: png {box_w:.3f}x{box_h:.3f} mm != "
                f"figsize {w_mm:.3f}x{h_mm:.3f} mm (bbox_inches tight?)"
            )

    print()
    print(_legend_retrieval(rs))
    print(_legend_quantization(gen, did))


if __name__ == "__main__":
    main()
