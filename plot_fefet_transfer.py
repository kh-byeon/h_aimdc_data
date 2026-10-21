"""
Batch-plot FeFET transfer curves from Agilent/Keysight B1500A I/V-Sweep CSV exports.
"""

from __future__ import annotations

import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration — edit FOLDER to point at your CSV directory
# ---------------------------------------------------------------------------
FOLDER = Path(__file__).resolve().parent / "FeFET_TR"
OUTPUT_DIR = FOLDER / "output_plots"

Y_LIM = (1e-15, 1e-3)
DPI = 300


# ---------------------------------------------------------------------------
# Filename parsing — edit these patterns if your naming convention changes
# ---------------------------------------------------------------------------
def parse_filename_conditions(stem: str) -> tuple[int, int, int, int, int]:
    """
    Extract (W, L, overlap, divider_num, divider_den) from a CSV filename stem.

    Expected encodings (examples):
      IGZO_TR [5,5,2,1_1(19) ; ...]     -> W=5, L=5, overlap=2, divider=1:1
      IGZO_TR [5_5_2_1_1]               -> same, underscore-separated
      IGZO_TR_5_5_2_1_1                 -> fallback when brackets were lost

    The fourth field uses an underscore for the capacitance-divider ratio
    (e.g. 1_1 -> 1:1, 2_3 -> 2:3).
    """
    # Bracketed form: [W, L, overlap, num_den(...optional device id...)]
    bracket_pat = re.compile(
        r"\[\s*(\d+)\s*[,_]\s*(\d+)\s*[,_]\s*(\d+)\s*[,_]\s*(\d+)_(\d+)",
        re.IGNORECASE,
    )
    m = bracket_pat.search(stem)
    if m:
        return tuple(int(g) for g in m.groups())  # type: ignore[return-value]

    # Fallback: five numbers after the IGZO_TR prefix (brackets replaced by underscores)
    prefix_pat = re.compile(
        r"IGZO_TR[_\s]+(\d+)[_,](\d+)[_,](\d+)[_,](\d+)_(\d+)",
        re.IGNORECASE,
    )
    m = prefix_pat.search(stem)
    if m:
        return tuple(int(g) for g in m.groups())  # type: ignore[return-value]

    raise ValueError(f"Could not parse W/L/overlap/divider from filename: {stem!r}")


def build_title(stem: str, w: int, l: int, overlap: int, div_num: int, div_den: int) -> tuple[str, str]:
    """Return (main title, subtitle with original filename)."""
    main = f"W/L/Overlap = {w}/{l}/{overlap} um,  Divider = {div_num}:{div_den}"
    return main, stem


# ---------------------------------------------------------------------------
# B1500A CSV parsing
# ---------------------------------------------------------------------------
def parse_b1500_csv(csv_path: Path) -> pd.DataFrame:
    """
    Locate the DataName header row and read all subsequent DataValue rows.

    Returns a DataFrame with columns taken from the DataName line (typically
    gate, IG, ID).
    """
    with csv_path.open(encoding="utf-8-sig") as fh:
        lines = fh.readlines()

    data_name_idx = None
    col_names: list[str] = []
    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line.startswith("DataName"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 2:
            continue
        col_names = parts[1:]
        data_name_idx = i
        break

    if data_name_idx is None or not col_names:
        raise ValueError("DataName header row not found")

    rows: list[list[float]] = []
    for raw in lines[data_name_idx + 1 :]:
        line = raw.strip()
        if not line.startswith("DataValue"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 1 + len(col_names):
            continue
        try:
            values = [float(parts[j + 1]) for j in range(len(col_names))]
        except ValueError as exc:
            raise ValueError(f"Non-numeric DataValue row: {line[:80]!r}") from exc
        rows.append(values)

    if not rows:
        raise ValueError("No DataValue rows found after DataName header")

    return pd.DataFrame(rows, columns=col_names)


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------
def apply_plot_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "0.3",
            "axes.linewidth": 0.8,
            "font.size": 11,
            "axes.labelsize": 12,
            "axes.titlesize": 13,
            "legend.fontsize": 10,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
        }
    )


def plot_transfer_curve(df: pd.DataFrame, main_title: str, subtitle: str, out_path: Path) -> None:
    gate_col = df.columns[0]
    gate = df[gate_col].to_numpy()

    id_col = next((c for c in df.columns if c.upper() == "ID"), None)
    if id_col is None:
        raise ValueError(f"ID column not found; columns={list(df.columns)}")
    abs_id = np.abs(df[id_col].to_numpy())

    ig_col = next((c for c in df.columns if c.upper() == "IG"), None)

    # Guard against log(0); clip to a tiny floor for plotting only
    floor = Y_LIM[0] * 0.1
    abs_id_plot = np.clip(abs_id, floor, None)

    fig, ax = plt.subplots(figsize=(6.5, 4.5), layout="constrained")

    ax.semilogy(
        gate,
        abs_id_plot,
        color="#1f77b4",
        linewidth=1.4,
        marker="o",
        markersize=2.5,
        markevery=max(1, len(gate) // 40),
        label=r"$|I_D|$",
        zorder=3,
    )

    if ig_col is not None:
        abs_ig_plot = np.clip(np.abs(df[ig_col].to_numpy()), floor, None)
        ax.semilogy(
            gate,
            abs_ig_plot,
            color="#888888",
            linewidth=1.0,
            linestyle="--",
            marker=".",
            markersize=2,
            markevery=max(1, len(gate) // 40),
            label=r"$|I_G|$",
            zorder=2,
        )

    ax.set_xlabel(r"$V_{GS}$ (V)")
    ax.set_ylabel("Current (A)")
    ax.set_title(main_title, pad=18)
    fig.suptitle(subtitle, fontsize=9, color="0.45", y=1.02)

    ax.set_ylim(Y_LIM)
    x_pad = 0.05 * (gate.max() - gate.min()) if gate.max() != gate.min() else 0.5
    ax.set_xlim(gate.min() - x_pad, gate.max() + x_pad)

    ax.legend(loc="best", framealpha=0.9)
    for spine in ax.spines.values():
        spine.set_linewidth(0.8)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=DPI, facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Batch driver
# ---------------------------------------------------------------------------
def process_file(csv_path: Path) -> None:
    stem = csv_path.stem
    w, l, overlap, div_num, div_den = parse_filename_conditions(stem)
    df = parse_b1500_csv(csv_path)
    main_title, subtitle = build_title(stem, w, l, overlap, div_num, div_den)
    out_path = OUTPUT_DIR / f"{stem}.png"
    plot_transfer_curve(df, main_title, subtitle, out_path)
    print(
        f"{csv_path.name} -> W={w}, L={l}, overlap={overlap}, "
        f"divider={div_num}:{div_den}, n={len(df)} -> {out_path.name}"
    )


def main() -> None:
    apply_plot_style()
    csv_files = sorted(FOLDER.glob("*.csv"))
    if not csv_files:
        print(f"No CSV files found in {FOLDER}")
        return

    print(f"Processing {len(csv_files)} file(s) from {FOLDER}")
    ok, failed = 0, 0
    for csv_path in csv_files:
        try:
            process_file(csv_path)
            ok += 1
        except Exception as exc:
            failed += 1
            print(f"WARNING: failed to process {csv_path.name}: {exc}")

    print(f"Done: {ok} succeeded, {failed} failed. Plots saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
