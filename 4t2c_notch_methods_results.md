# Notch shift in a 4T2C complementary IGZO cell — methods and results

**Device** chip6, 4 × 4 array, cell at row 0 / column pair 0.
**Campaign** 2026-09-04 18:46 → 2026-09-05 11:13 KST, single cell, uninterrupted probe contact.
**Companion dataset** `4t2c_notch_dataset_chip6_R0C0_0904-0905.xlsx`.

---

## 1. Scope

This document covers the array-wired measurements of 2026-09-04 and 09-05 only. Earlier
single-cell work on the same chip (2026-09-02/03: retention, MBL scans, development of the
adaptive window) used a different pin assignment and is not merged here.

Twelve sessions were run: six common-mode scans (CM1–CM6), three read-condition searches
(OPT1–OPT3, 15 conditions × 10 blocks each), and three dense storage-value scans
(FINE1–FINE3, 2 sweep orders × 26 blocks each). In total 606 notch measurements from
13 905 bias points.

---

## 2. Cell and signal definitions

The 4T2C cell stores a differential value on two floating nodes and reads it back through two
complementary transistors whose currents are summed into one transimpedance amplifier (TIA).

| Symbol | Meaning | Set by |
|---|---|---|
| *w* | stored differential value [V] | write pulse |
| *v* | differential read input [V] | SL0 = +*v* + *s*, SL1 = −*v* + *s* |
| *s* | SL common-mode offset [V] | `slcm` |
| *V*<sub>MBL</sub> | read-transistor source bias [V] | MBL DAC |
| *α* | SL → storage-node capacitive divider ratio | device |

**Write.** WL is pulsed on with BL0 = +*w*, BL1 = −*w*, SL = 0 V. All unselected BL and SL
columns are held at 0 V. The two storage nodes settle to ±*q* with *q* ∝ *w*.

**Read.** WL off; all BLs at 0 V; SL0 and SL1 driven differentially about *s*; MBL biased; the
selected row's RBL is held at virtual ground by the TIA. The storage nodes are floating, so
each follows its SL through the divider:

&nbsp;&nbsp;&nbsp;&nbsp;*n*<sub>0</sub> = +*q* + *α*(+*v* + *s*),&nbsp;&nbsp;&nbsp;
*n*<sub>1</sub> = −*q* + *α*(−*v* + *s*)

**Notch.** The summed current *I*(*v*) = *g*(*n*<sub>0</sub>) + *g*(*n*<sub>1</sub>) has a minimum
where the two gate voltages are equal. That minimum — the *notch* — sits at

&nbsp;&nbsp;&nbsp;&nbsp;**v₀ = −w/α + b**

where *b* absorbs branch mismatch. The whole campaign measures *v*₀(*w*).

Note the symmetry property used throughout: for matched branches, *I*(*v*₀ + *u*) is exactly
even in *u* for **any** common mode *s*. The common mode therefore cannot by itself create
left–right asymmetry; asymmetry arises only when one branch leaves saturation before the
other, which mismatch makes happen at different |*u*|.

---

## 3. Instrumentation

FPGA controller driving an 8-channel DAC on the BL/SL columns plus one channel on MBL; one
TIA per row into a 12-bit ADC. Column pair *j* uses DAC channels 2*j* (BL) and 2*j*+1 (SL);
row *i* reads through TIA channel 8 + *i*. Each bias point is sampled 3 times consecutively;
`code_avg` is the mean and `pt_sd_code` the standard deviation of those 3 samples. Larger ADC
code = larger current.

Reported ADC noise is therefore the scatter *within* one bias point, on a millisecond
timescale — see §9.6.

---

## 4. Determining the operating point (common-mode scan)

With *w* = 0 and *v* = 0, both read transistors are driven together while *s* is swept from
−1.6 V to +1.5 V in 0.1 V steps. The estimated common gate voltage is *n* = *α s*.

Because the TIA holds the drain at 0 V while the source sits at *V*<sub>MBL</sub>, the device
regions in terms of the gate voltage *n* are

| region | condition |
|---|---|
| cut-off | *n* ≤ *V*<sub>MBL</sub> + *V*<sub>t</sub> |
| saturation | *V*<sub>MBL</sub> + *V*<sub>t</sub> < *n* ≤ *V*<sub>t</sub> |
| triode | *n* > *V*<sub>t</sub> |

so the usable (saturated) gate window is (*V*<sub>MBL</sub> + *V*<sub>t</sub>, *V*<sub>t</sub>]
and its width is exactly |*V*<sub>MBL</sub>|. Centring the operating point in that window,

&nbsp;&nbsp;&nbsp;&nbsp;*s** = (*V*<sub>MBL</sub>/2 + *V*<sub>t</sub>) / *α*,

places both region boundaries equidistant from the notch and maximises the symmetric reach.

**Fitting.** *V*<sub>t</sub> is extracted with a piecewise saturation/triode model
(*B* = *V*<sub>MBL</sub> + *V*<sub>t</sub>, *V*<sub>ds</sub> = −*V*<sub>MBL</sub>):

&nbsp;&nbsp;&nbsp;&nbsp;*n* ≤ *V*<sub>t</sub>: *I* = *C* + *K*(*n* − *B*)²
&nbsp;&nbsp;&nbsp;&nbsp;*n* > *V*<sub>t</sub>: *I* = *C* + *K*(2(*n* − *B*)*V*<sub>ds</sub> − *V*<sub>ds</sub>²)

*V*<sub>t</sub> is the only nonlinear parameter and is grid-searched at 5 mV resolution;
(*C*, *K*) are solved by linear least squares at each trial *V*<sub>t</sub>.

> A √*I*-linear extrapolation was tried first and **rejected**. It selects part of the triode
> region as if it were saturation and extrapolates over ≈ 2 V, returning *V*<sub>t</sub> ≈ −0.37 V
> against +0.29 V from the piecewise fit. The piecewise fitter recovers *V*<sub>t</sub> exactly on
> synthetic data. Any *V*<sub>t</sub> quoted from the √*I* method should be discarded.

---

## 5. Sweep window

The differential input *v* is stepped at 0.1 V. Rather than a fixed range, the window is set
**by the current**: each arm is extended until the measured code exceeds
(1 + *r*) × the block floor, with *r* = `auto_ratio`. This keeps every block at the same
fractional excursion above its own minimum regardless of where the notch sits, which is what
makes curvature comparable across *w*.

Implementation notes that matter for reproducing the data:

- Arm decisions are made relative to the *running argmin*, not the initially predicted notch;
  both arms are re-evaluated from scratch after every point. An earlier centre-relative version
  produced lopsided windows (up to 0.62 V off) and excursions of 48–137 % instead of the
  requested 50 %.
- An arm closes immediately once the criterion is met, even below the minimum-points setting.
  To get more points per block, reduce the *v* step rather than lengthening the arms.
- A predictive stop uses the parabolic increment ratio (2*n*+1)/(2*n*−1) to avoid overshooting
  by one point.

With *r* = 0.5 the realised excursion was 47–48 % and blocks contained 16–20 points at a
half-width of 0.78–0.84 V.

**Read-disturb guard.** The storage node *n* = *q* + *α*(*v* + *s*) is floating; if it falls
below the BL voltage the access transistor turns on and erases the stored value. Before each
condition the worst-case node excursion is computed and the condition is skipped if the node
would go more than 1.2 V below BL. Three of eighteen planned conditions were skipped this way.
(The limit is not conservative: on 2026-09-02 a 1.3 V excursion destroyed 54 % of the stored
value in a single sweep.)

---

## 6. Storage-value ordering and drift control

Writing *w* repeatedly leaves a history. Measured as the shift of the notch when the first *w*
of a run is re-measured at the end:

| session | *w* range | blocks | drift (end − start) |
|---|---|---|---|
| OPT1 | ±1.5 V | 10 per condition | −50.8 ± 10.5 mV (n = 15) |
| OPT2 | ±1.5 V | 10 per condition | −52.7 ± 14.3 mV (n = 15) |
| OPT3 | ±1.5 V | 10 per condition | −48.5 ± 9.2 mV (n = 15) |
| FINE1 | ±0.6 V | 26 per pass | +9.9 mV (n = 2) |
| FINE2 | ±0.6 V | 26 per pass | −7.6 mV (n = 2) |
| FINE3 | ±0.6 V | 26 per pass | −2.1 mV (n = 2) |

The drift is a large-|*w*| effect: it is −50 mV over ten blocks spanning ±1.5 V but consistent
with zero over twenty-six blocks spanning ±0.6 V. The floor and the curvature are unchanged by
it, so what moves is the stored value itself (≈ −33 mV referred to *w*), not the readout.

Because a monotone drift in time maps directly onto a slope error when *w* is swept
monotonically, three orders are provided:

- **`seq`** — *w* from −0.6 to +0.6 monotonically. Drift adds directly to the slope.
- **`alt`** — 0, −0.05, +0.05, −0.10, +0.10, … outward from zero. Drift becomes an even
  function of *w* and does not bias the slope; it inflates the residual scatter instead.
- **`seq_recheck`** — monotone with the first *w* repeated at the end (used by OPT1–3).

Each pass re-measures its first *w* at the end, so the drift *D* is measured directly and its
worst-case effect on *α* can be stated as |*D*|·*α*/(*w*<sub>max</sub> − *w*<sub>min</sub>).
For the ±0.6 V runs that bound is 0.1–1.0 %, i.e. drift is not a limiting error there; for a
25-block ±0.6 V run at the ±1.5 V drift rate it would have been ≈ 7 %.

**Validated on synthetic data.** With a true *α* = 0.613 and an injected −6 mV/block drift,
`seq` returns 0.5710 (−6.4 % biased), `alt` returns 0.6103 (−0.4 %), and the visit-index
drift correction recovers 0.6130 from both.

---

## 7. Notch extraction

All 606 notches in the dataset were re-extracted from the raw curves by one method, so that
optscan and finescan rows are directly comparable:

1. take the sampled minimum of the block;
2. keep points within 0.70 V of it (matching `NOTCH_FIT_SPAN` in the measurement code);
3. least-squares quadratic *I*(*v*) = *a v*² + *b v* + *c*; **v₀ = −b/(2a)**;
4. the uncertainty **se(v₀)** is propagated from the polyfit covariance through *v*₀ = −*b*/(2*a*);
5. curvature = 2*a*; floor = *I*(*v*₀); `asym` = right/left amplitude about *v*₀ over the common
   reach of the two arms (1.0 = symmetric).

Two checks on the method:

- **Against the instrument's on-line fit.** For the two sessions where both exist, the
  re-extraction agrees to 0.9–1.1 mV rms (max 3.5 mV) in the low-noise session FINE3 and to
  3.6–5.1 mV rms in the noisy session FINE2 — in both cases well inside the notch uncertainty.
- **Cubic vs quadratic.** Established on the 2026-09-03 data: a cubic fit of the *block* moves
  the notch by only +6 mV (mostly a common offset) and changes *α* by 0.9 %, but doubles se
  (0.0050 → 0.0085 V). The quadratic is used. (Not to be confused with the cubic in *w* of §9.2,
  which is a property of the device, not of the block fit.)
  The `asym` metric is always computed about the **cubic** centre: computed about the
  quadratic centre it inverts (a synthetic 1.09 reads back as 0.90).

---

## 8. Read-condition search

Three independent campaigns (OPT1–3) swept *V*<sub>MBL</sub> ∈ {−1.0, −1.5, −2.0} V,
*s* ∈ {0, 0.5, 1.0, 1.5} × *s**, and `auto_ratio` ∈ {0.5, 0.25, 1.0}, holding the *w* list,
the ordering and the window rule identical across conditions so that only the condition
differs. A baseline condition was re-inserted every four conditions to separate time drift
from condition effect.

Conditions were ranked by **curvature CV across *w*** — how much the response shape changes as
the stored value changes — rather than by a fitted exponent.

> Why not the exponent: the on-line log–log exponent estimator is biased by +0.3–0.4 because a
> narrow window makes the amplitude and the exponent strongly correlated (it returned 2.19
> where a C-free symmetrised estimator gave 1.85). Ranking on it once put the *worst* condition
> (CV 8.7 %) first. The C-free estimator symmetrises,
> *S*(*d*) = [*I*(*v*₀+*d*) + *I*(*v*₀−*d*)]/2, and solves
> [*S*(3*d*) − *S*(2*d*)]/[*S*(2*d*) − *S*(*d*)] = (3<sup>p</sup> − 2<sup>p</sup>)/(2<sup>p</sup> − 1);
> its bias is +0.03–0.05 with a per-curve SD of 0.16.

**Result — curvature CV [%] at `auto_ratio` = 0.5, *V*<sub>MBL</sub> = −1.0 V**
(as computed on line by the search script over its own ten-block *w* list; the re-extracted
values in §9.6 use a different fit span and run 0.5–3 points higher):

| *s* relative to window centre | OPT1 | OPT2 | OPT3 |
|---|---|---|---|
| 0 (× 0) | 7.43 | 7.44 | 7.17 |
| × 0.5 | 4.32 | 4.29 | 4.92 |
| **× 1.0 (centre)** | **2.72** | **3.34** | **2.60** |
| × 1.5 | 6.70 | 8.67 | 8.74 |

and by MBL (best condition at each): −1.0 V → 2.72 / 3.34 / 2.60 %; −1.5 V → 3.80 / 4.94 /
4.68 %; −2.0 V → 13.44 / 14.05 / 14.98 % (at *s* = 0 the −2.0 V case saturates the ADC).

**Optimum, replicated three times: *V*<sub>MBL</sub> = −1.0 V, *s* at the window centre
(≈ −0.44 V), `auto_ratio` = 0.5.** All subsequent measurements use it.

---

## 9. Results

### 9.1 Threshold and operating window

| session | time | *V*<sub>t</sub> [V] | window [V] | *s** [V] | fit rms [code] |
|---|---|---|---|---|---|
| CM1 | 09-04 18:46 | +0.287 | (−0.713, +0.287] | −0.341 | 5.4 |
| CM2 | 09-04 18:54 | +0.264 | (−0.736, +0.264] | −0.377 | 7.6 |
| CM3 | 09-04 19:14 | +0.259 | (−0.741, +0.259] | −0.385 | 6.3 |
| CM4 | 09-04 21:04 | +0.239 | (−0.761, +0.239] | −0.417 | 7.2 |
| CM5 | 09-05 00:02 | +0.224 | (−0.776, +0.224] | −0.441 | 5.6 |
| CM6 | 09-05 09:17 | +0.184 | (−0.816, +0.184] | −0.505 | 9.3 |

*V*<sub>t</sub> falls monotonically by 103 mV over 14.5 h, moving the ideal common mode by
−164 mV. The window width stays |*V*<sub>MBL</sub>| = 1.0 V by construction.

### 9.2 The notch-shift model

A straight line does not describe *v*₀(*w*) over ±1.5 V: it leaves 119–127 mV rms, and the
fitted *α* depends on the range used (0.705–0.716 over ±1.5 V versus 0.619–0.627 over ±0.6 V).
Adding a single cubic term resolves this:

&nbsp;&nbsp;&nbsp;&nbsp;**v₀(w) = −w/α + b + c₃ w³**

| session | range | *α* (linear) | *α* (cubic) | *c*₃ [V/V³] | rms linear | rms cubic |
|---|---|---|---|---|---|---|
| OPT1 | ±1.5 | 0.716 | 0.586 | +0.185 ± 0.014 | 127 mV | 23 mV |
| OPT2 | ±1.5 | 0.713 | 0.590 | +0.175 ± 0.013 | 120 mV | 21 mV |
| OPT3 | ±1.5 | 0.705 | 0.585 | +0.174 ± 0.012 | 119 mV | 20 mV |
| FINE3 alt | ±0.6 | 0.628 | 0.617 | +0.128 ± 0.042 | 8.5 mV | 7.1 mV |
| FINE3 seq | ±0.6 | 0.618 | 0.604 | +0.160 ± 0.026 | 7.3 mV | 4.4 mV |

**c₃ = +0.178 ± 0.006 V/V³** (mean ± SD of the three full-range campaigns). One parameter cuts
the full-range residual by a factor of six.

The consistency test that matters: *c*₃ obtained from the dense ±0.6 V data alone agrees with
the full-range value, and *c*₃ × 1.5³ = 0.60 V reproduces the "compression" seen at |*w*| = 1.5.
The 500 mV departure at large *w* and the 8 mV ripple resolved at small *w* are the same term.

*Caveats.* The cubic is an effective description, not the exact form: the full-range residual
after the cubic (20–23 mV) is still above the notch uncertainty there (4–6 mV), and with *c*₃
fixed at the full-range value the narrow-range *α* comes out 0.602–0.614 against 0.585–0.590
from the full range — a 2–4 % gap. A higher-order term is present but has not been resolved.

### 9.3 Small-signal α and the linear range

Over |*w*| ≤ 0.6 V the response is linear to the measurement floor. Nine independent
determinations give

&nbsp;&nbsp;&nbsp;&nbsp;**α = 0.6231 ± 0.0050** (±0.8 %, spanning 14.5 h)

At the best condition and after a power cycle (FINE3): notch spacing at Δ*w* = 0.05 V is
Δ*v*₀ = 80 mV against a notch uncertainty of 3.2 mV — 25 σ, so all 25 notches in the range are
individually resolved; curvature 470 code/V² with a CV of 1.8–1.9 % across the 25 stored values.

### 9.4 The offset b tracks the threshold

*b* drifts monotonically from +0.004 V to −0.129 V over the campaign. Against the
independently measured *V*<sub>t</sub> from the preceding common-mode scan:

| *V*<sub>t</sub> [V] | *b* [V] |
|---|---|
| +0.2592 | +0.0042 |
| +0.2392 | −0.0423 |
| +0.2242 | −0.0736 |
| +0.1842 | −0.1209 |

d*b*/d*V*<sub>t</sub> = **+1.63**, against 1/*α* = 1.60, with *r* = +0.983 (n = 4). The notch
offset drift is quantitatively consistent with a gate-referred threshold drift divided by the
capacitive divider. Practically this means *α* can be carried between sessions but *b* cannot;
*b* is, however, predictable from the common-mode scan rather than needing its own calibration.

With only four points, and both quantities monotone in time, this should be confirmed by
deliberately shifting *V*<sub>t</sub> (e.g. by bias stress) rather than waiting for drift.

### 9.5 A reproducible dependence on write order

In all three FINE sessions the `alt` order returns a larger *α* than `seq` by

&nbsp;&nbsp;&nbsp;&nbsp;Δ*α* = +0.0106, +0.0103, +0.0107 (1.7 %, SD 0.0002)

while the net drift within each pass is ≤ 10 mV. This is not a time drift — it is reproducible
to 2 % of itself and depends only on the sequence in which values are written. In `alt`
consecutive writes alternate in polarity; in `seq` they step monotonically. The effective
stored value therefore retains a dependence on the previous write. Any calibration of *α*
must fix the write order.

### 9.6 Readout noise and the power-cycle effect

| session | powered | per-point ADC SD [code] | notch se [mV] | curvature CV [%] |
|---|---|---|---|---|
| OPT1–3 | ≈ 5 h | 4.6 / 4.9 / 4.9 | 4.2 / 6.2 / 5.5 | 3.5 / 6.4 / 3.2 |

(notch se and curvature CV re-extracted here at the best condition; ±1.5 V *w* range)
| FINE1 | overnight | 11.0 | 9.1 | 6.7 |
| FINE2 | overnight | 9.9 | 9.7 | 5.1 |
| **FINE3** | **after power cycle** | **3.0** | **3.2** | **1.8** |

The excess noise in FINE1/FINE2 was characterised before it was removed, because it is a
readout property that has to be excluded before any device claim is made:

- **Not thermal.** Johnson noise scales as √(*kT*); a 20 °C rise gives +3.3 %, not ×2.4.
- **Additive, not signal-dependent.** Per-point SD is flat against current (4.2 / 4.4 / 3.9 at
  ADC code 350 / 450 / 570 at night; 11.6 / 10.5 / 9.5 in the morning). Shot noise from the
  cell current would rise as √*I*; a gain or reference error would rise ∝ *I*.
- **Flat against SL output voltage** (0 → 3 V), so not the DAC output stage.
- **Gaussian** (excess kurtosis −0.08 to +0.14 in both states), so not one dominant mains line.
- **Steady, not intermittent.** Block-to-block CV of the noise level is 15–27 % in both states.
- **Fast.** At night the block residual is 1.5–1.7 × the 3-sample averaged error; in the noisy
  state it is 1.1 ×. The added noise is entirely at the sub-point timescale and averages as
  1/√N.
- **Not a function of hours powered.** Over five continuous hours the level went
  4.31 → 5.29 → 4.22 with no trend.

A power cycle with no other change returned the noise to 3.0 code — *below* every earlier
session. The mechanism was not pursued; the operational rule is to re-power the board before a
precision run.

**Why this mattered scientifically.** In FINE1/FINE2 the linear residual (8.8–12.4 mV) equalled
the notch uncertainty (9.1–12.4 mV), so no nonlinearity could be claimed; the residual shape
did not correlate between passes (*r* = −0.04, +0.34). In FINE3 the uncertainty fell to 3.2 mV
while the residual stayed at 7.3–8.5 mV, and the two passes now correlate at *r* = +0.69. That
is what made §9.2 possible.

---

## 10. Data availability

`4t2c_notch_dataset_chip6_R0C0_0904-0905.xlsx`

| sheet | rows | content |
|---|---|---|
| README | — | provenance, column definitions, extraction method |
| SESSIONS | 12 | session log in time order |
| NOTCH | 606 | one row per block — the primary table |
| CONDITIONS | 45 | optscan condition table with quality metrics |
| FITS | 9 | per-session linear and cubic model fits |
| CMSCAN_FIT | 6 | threshold and window from each common-mode scan |
| CMSCAN_PTS | 186 | raw common-mode scan points |
| NOISE | 6 | per-point ADC scatter by session |
| VALIDATION | 4 | re-extraction vs the instrument's on-line fit |
| CURVES | 13 905 | every raw bias point behind NOTCH |

Every row carries `source_file`, naming the original CSV written by the measurement script.
Acquisition code: `igzo_4t2c_response.py` (hardware layer, common-mode scan, notch extraction),
`igzo_4t2c_optscan.py` (condition search), `igzo_4t2c_finescan.py` (dense *w* scan).

---

## 11. Open items

1. **Form of the nonlinearity.** *w*³ leaves 20 mV over ±1.5 V against a 5 mV floor. Extend the
   dense scan to ±1.0 V at 0.1 V after a power cycle to fit *w*³ and *w*⁵ together.
2. **Origin of the cubic.** Not yet separated into write compression versus a voltage-dependent
   *α*. A write-pulse-width or write-voltage sweep at fixed read conditions would separate them.
3. **Write-order effect (§9.5).** Reproducible at 1.7 % but unexplained. Compare `alt`, `seq`
   and a randomised order at fixed everything else.
4. **b–V<sub>t</sub> link (§9.4).** n = 4 and time-confounded; confirm by deliberately shifting
   *V*<sub>t</sub>.
5. **Instrument asymmetry.** The `swap` control (SL polarity exchange) has not been run; until
   it is, the residual `asym` cannot be split between cell mismatch and instrument asymmetry.
6. **Noise mechanism (§9.6).** Diagnosed as far as "broadband, additive, resets on power
   cycle". A long single-bias sample burst with a spectrum, logged from a cold start, would
   settle it. Note that `bl` and `dark` read exactly 0.0 in every session, so no readout-only
   reference at a realistic output level exists yet — that should be fixed first.
