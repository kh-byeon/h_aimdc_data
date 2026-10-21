#!/usr/bin/env python3
"""Shared notation and plot style for the notch figures in this folder.

Every notch measurement here -- 4T2C complementary IGZO and FeFET alike -- is
describing the same structure: a differential read input is swept, the summed
current has a minimum (the *notch*), and the position of that minimum reports
what the cell stores. The scripts grew separately and drifted apart in how they
name those quantities, which made two figures of the same thing look like
figures of different things. This module is the single place that fixes it.

Users
-----
``plot_4t2c_notch_campaign.py``   2026-09-04/05 array-wired campaign (chip6)
``plot_4t2c_notch_response.py``   2026-09-03 single-cell auto-window dataset
``plot_fefet_notch_shift.py``     chip3 FeFET notch campaign
``plot_igzo_4t2c_retention.py``   IGZO 4T2C retention

The notation
------------
=================  ========================================================
``v``              differential read input, the swept axis
``v0``             notch position, where the summed current is minimum
``w``              the stored differential value, what the cell holds
``kappa``          curvature of the notch, d2(code)/dv2 at v0
``p``              exponent of code = C + A|v - v0|^p
``alpha``          SL-to-storage-node capacitive divider ratio
=================  ========================================================

Two collisions this resolves, so they do not come back:

* ``plot_fefet_notch_shift.py`` used ``w`` for the notch *position*, while the
  4T2C scripts use ``w`` for the *stored value* and ``v0`` for the notch. The
  notch is ``v0`` everywhere now.
* ``plot_igzo_4t2c_retention.py`` wrote the notch as ``v_notch`` and the stored
  value as ``w_store``. Plain ``v0`` and ``w``; ``w_est`` is kept where the
  stored value is *inferred* from a notch rather than programmed, since that is
  a real distinction and not a naming one.

Instrument units genuinely differ and are not forced together: the 4T2C chain
reports a TIA code in LSB, the FeFET script a current in code/ms.
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
# Notation -- axis and colourbar labels
# ---------------------------------------------------------------------------
LBL_V = "Differential read input  $v$  (V)"
LBL_W = "Stored value  $w$  (V)"
LBL_W_EST = "Estimated stored value  $w_{est}$  (V)"
LBL_V0 = "Notch position  $v_0$  (V)"
LBL_DV = "$v - v_0$  (V)"

# Readout, per instrument.
LBL_CODE = "TIA code (LSB)"
LBL_CODE_NORM = "Normalised code"
LBL_CURRENT = "Current  $I$  (code / ms)"
LBL_CURRENT_NORM = "Normalised current  $I$"

# Derived quantities.
LBL_CURV = r"Curvature  $\kappa$  (code/V$^2$)"
LBL_SWING = "Notch swing (LSB)"
LBL_FLOOR = r"Notch floor (LSB)"
LBL_P = "Fitted exponent  $p$"
LBL_ALPHA = r"Small-signal  $\alpha$"
LBL_DW = r"Stored-value loss  $\Delta w$  (mV)"

# The model, for annotating a panel.
MODEL_LINEAR = r"$v_0(w) = -w/\alpha + b$"
MODEL_CUBIC = r"$v_0(w) = -w/\alpha + b + c_3 w^3$"
MODEL_POWER = r"$code = C + A\,|v - v_0|^{\,p}$"

# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------
DPI = 300
FONT_BASE = 20
FONT_AXIS = 20
FONT_PANEL = 20
LW_CURVE = 2.0
GRID_ALPHA = 0.5
MARKERSIZE = 7

# The stored value and the notch are signed and centred on zero, so they get a
# diverging ramp with a neutral midpoint rather than a sequential one.
CMAP_NOTCH = "coolwarm"
CMAP_W = CMAP_NOTCH          # historical alias

# Okabe-Ito, which stays legible in greyscale and to colour-blind readers.
C_REF = "#333333"       # ideal / reference lines
C_FIT = "#666666"       # fitted guides
C_MAIN = "#0072B2"      # blue    -- primary series
C_ALT = "#D55E00"       # orange  -- second series
C_OK = "#009E73"        # green   -- the good case
C_WARN = "#CC3311"      # red     -- the failure case
C_PURPLE = "#8256A5"    # fourth series

# Role aliases, so a script reads in its own terms without re-picking colours.
C_DOWN = C_MAIN
C_UP = C_ALT
C_LOWER = "#3B4CC0"
C_UPPER = "#E66100"
C_LOSS = C_ALT
C_CODE = C_MAIN
C_SWING = C_OK
C_CRIT = C_WARN


def apply_plot_style() -> None:
    """rcParams shared by every notch figure."""
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": FONT_BASE,
        "axes.labelsize": FONT_AXIS,
        "axes.titlesize": FONT_PANEL,
        "legend.fontsize": FONT_BASE - 5,
        "xtick.labelsize": FONT_BASE - 2,
        "ytick.labelsize": FONT_BASE - 2,
    })


def style_ax(ax: plt.Axes) -> None:
    """Bold ticks, a full frame and a light grid."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(True)
    ax.tick_params(axis="both", which="major", width=1.5, length=6)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontweight("bold")
    ax.grid(True, which="major", alpha=GRID_ALPHA, linewidth=0.5)


# ---------------------------------------------------------------------------
# Bare copies: the same figure with the labelling taken off
# ---------------------------------------------------------------------------
BARE_SUFFIX = "_bare"


def _is_number(label: str) -> bool:
    """True if a tick label is just a number (mathtext minus sign included)."""
    t = label.strip().replace("\u2212", "-").replace("$", "")
    if not t:
        return True
    try:
        float(t)
    except ValueError:
        return False
    return True


def strip_text(fig: plt.Figure) -> None:
    """Remove every piece of text from a figure except numeric tick labels.

    Titles, axis labels, legends, annotations, panel letters and colourbar
    labels all go; colourbars are ordinary axes, so the same loop clears them.

    Tick labels are the one thing kept, and only when they are numbers -- they
    carry the scale, and an axis without it cannot be read at all. Categorical
    ticks are words, so they go with the rest: the exponent panel's row of
    session names, for instance, is labelling and belongs in the caption.
    """
    for txt in list(fig.texts):          # suptitle and figure-level notes
        txt.remove()
    for ax in fig.axes:                  # includes colourbar axes
        ax.set_title("")
        ax.set_xlabel("")
        ax.set_ylabel("")
        leg = ax.get_legend()
        if leg is not None:
            leg.remove()
        for txt in list(ax.texts):
            txt.remove()
        for axis, getter in ((ax.xaxis, ax.get_xticklabels),
                             (ax.yaxis, ax.get_yticklabels)):
            labels = [t.get_text() for t in getter()]
            if labels and not all(_is_number(t) for t in labels):
                axis.set_ticklabels([""] * len(labels))

# ---------------------------------------------------------------------------
# Notch shape: the exponent of code = C + A|v - v0|^p
# ---------------------------------------------------------------------------
def _solve_p(ratio: float) -> float:
    """Invert (3^p - 2^p)/(2^p - 1) = ratio. Monotone in p, so bisect."""
    def f(q):
        return (3.0 ** q - 2.0 ** q) / (2.0 ** q - 1.0)

    lo, hi = 0.20, 8.0
    if not (f(lo) <= ratio <= f(hi)):
        return float("nan")
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if f(mid) < ratio:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def exponent_cfree(v, code, v0: float) -> float:
    """Exponent of code = C + A|v - v0|^p, by the C-free symmetrised estimator.

    Methods doc section 8. Build S(d) = [I(v0+d) + I(v0-d)]/2 at d, 2d and 3d
    across the common reach of the two arms, then solve

        [S(3d) - S(2d)] / [S(2d) - S(d)] = (3^p - 2^p) / (2^p - 1)

    C cancels in the differences and A cancels in the ratio, so neither is
    fitted. That matters here: in a narrow window A and p are strongly
    correlated, which biases the on-line log-log estimator by +0.3 to 0.4 (it
    returned 2.19 where this estimator gives 1.85). This one carries a +0.03 to
    +0.05 bias and a per-curve SD of 0.16, so it is an ensemble statistic --
    a single block's value means little.

    Being built from differences and a ratio, it is invariant under any affine
    rescaling of the code axis: normalising y does not change p.
    """
    v = np.asarray(v, dtype=float)
    code = np.asarray(code, dtype=float)
    order = np.argsort(v)
    v, code = v[order], code[order]
    reach = min(v0 - v[0], v[-1] - v0)
    if reach <= 0:
        return float("nan")
    d = reach / 3.0
    s = []
    for k in (1, 2, 3):
        s.append(0.5 * (np.interp(v0 + k * d, v, code)
                        + np.interp(v0 - k * d, v, code)))
    if s[1] - s[0] <= 0:
        return float("nan")
    return _solve_p((s[2] - s[1]) / (s[1] - s[0]))

def panel_label(ax: plt.Axes, text: str, dx: float = -0.16) -> None:
    """Panel letter, placed outside the axes at the top left."""
    ax.text(dx, 1.03, text, transform=ax.transAxes, fontsize=FONT_PANEL,
            fontweight="bold", va="bottom", ha="left")
