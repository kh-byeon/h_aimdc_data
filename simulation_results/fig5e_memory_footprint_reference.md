# Memory-footprint reference — H_RAG v3.0 (on-the-fly MMR, FeFET + IGZO device path)

Extracted from the repository and its built indices so that array sizing, cell counts and
device-capacity calculations can be done elsewhere. **Every number below is measured from
the code or the on-disk artifacts, not estimated**, unless explicitly marked
`ASSUMED` / `DERIVED`.

Snapshot: repo `H_RAG_cuad_v3.0_MMR_deviceModeling`, indices built 2026-08-06 (hotpot) /
2026-04-17 (cuad). Sweep run `20260813_162948_mmr-capacitor_centroid-nvm`.

---

## 1. What is mapped onto hardware, and what is not

The pipeline has **two** analog compute blocks. They are physically different technologies,
store different things, and have different persistence requirements. Everything else stays
in conventional digital memory.

| Block | Technology | Stores | Persistence | Written |
|---|---|---|---|---|
| **A. Coarse centroid search** (`step3_coarse_search`) | **FeFET** (NVM) | IVF centroids | Non-volatile | Once, offline |
| **B. MMR pair distance** (`step5_on_the_fly_mmr`) | **IGZO TFT + boost cap** (AIMDC) | Selected-buffer embeddings | Volatile (capacitor-held) | Every MMR step |
| PQ/OPQ, posting lists, chunk text, metadata | digital (DRAM/SRAM) | — | — | — |

Block A is the *non-volatile weight array*. Block B is a *scratchpad* rewritten
continuously during a single query — its capacity requirement is tiny but its write
bandwidth/endurance requirement is the dominant one.

Source of truth for the split: `online_accelerator_device.py:495` (centroid path) and
`online_accelerator_device.py:899` (MMR path); the runtime prints it as
`"[Device-L2] scope: AIMDC is strictly the MMR diversity accelerator"`.

---

## 2. Embedding & index configuration

From `offline_data_<domain>/config.pkl` (identical for both domains except chunking):

| Parameter | Value |
|---|---|
| Encoder | `sentence-transformers/multi-qa-mpnet-base-dot-v1` |
| Embedding dim `D` | **768** |
| Embedding dtype | `float32` |
| L2-normalized | yes (`embeddings_l2_normalized: True`) |
| Encoder max_length | 512 tokens |
| IVF centroids `nlist` | **128** |
| PQ subspaces `m` | **8** |
| PQ subvector dim `D/m` | **96** |
| PQ codewords per subspace `k*` | **256** (⇒ 8 bit/subvector) |
| PQ code per chunk | 8 × uint8 = **8 B = 64 bit** |
| OPQ rotation | 768 × 768 `float32` |
| chunk_size_chars | 300 (hotpot) / 1500 (cuad) |
| chunk_overlap_chars | 150 (hotpot) / 300 (cuad) |

Runtime search defaults (`online_accelerator_device.py`):
`nprobe = 32`, `top_r = 128` (chunks loaded per centroid), `top_k ∈ {5,10,20,50}` in the sweep.

---

## 3. Corpus scale

| | hotpot | cuad |
|---|---|---|
| Chunks indexed (= vectors) | **9,767** | **47,765** |
| Chunks per centroid | min 11 / mean 76.3 / max 215 | — |
| Corpus source | `processed_hotpot/hotpot_corpus.json` | `processed_cuad/cuad_corpus.json` |

Note for hotpot: one corpus paragraph → one chunk, so `doc_id` == corpus paragraph index
(this invariant is what makes supporting-passage recall well-defined).

---

## 4. On-disk index artifacts (digital memory)

Measured file sizes. `offline_data_hotpot/`:

| Artifact | Shape | dtype | Bytes |
|---|---|---|---|
| `raw_embeddings.npy` | (9767, 768) | float32 | 30,004,352 |
| `opq_rotation.npy` | (768, 768) | float32 | 2,359,424 |
| `pq_codebooks.npy` | (8, 256, 96) | float32 | 786,560 |
| `lut_packed.npy` | (196608,) | float32 | 786,560 |
| `centroids.npy` | (128, 768) | float32 | 393,344 |
| `centroids_packed.npy` | (98304,) | float32 | 393,344 |
| `metadata_db.pkl` | 9,767 entries | — | 6,139,987 |
| `posting_lists.pkl` | 128 lists / 9,767 entries | — | 585,643 |
| `df_stats.json` | — | — | 774,640 |
| `chunk_ids_order.pkl` | — | — | 86,836 |
| **Total** | | | **≈ 42.3 MB** |

`offline_data_cuad/` (47,765 chunks): `raw_embeddings.npy` 146,734,208 B,
`metadata_db.pkl` 34,335,771 B, `posting_lists.pkl` 2,872,991 B; the codebook / rotation /
centroid artifacts are **identical in size** to hotpot (they do not scale with corpus size).
Total ≈ 188.7 MB.

### Per-chunk cost (scaling rule)

| Item | Bytes/chunk | Scales with corpus |
|---|---|---|
| Raw embedding (768 × float32) | 3,072 | yes |
| PQ code (8 × uint8) | 8 | yes |
| Posting-list entry (`chunk_id` str + `pq_code` + `vector_id`) | ≈ 60 (pickle) | yes |
| Metadata entry (incl. chunk text) | ≈ 629 (hotpot) / ≈ 719 (cuad) | yes |
| Codebooks + rotation + centroids | 3,539,328 total | **no** (fixed) |

`raw_embeddings.npy` is used for the software-L2 upper bound (`L2_RAW`) and for auto-fitting
the device scaler. A deployed accelerator that only serves the PQ path does not need it —
that is a **391× reduction** per chunk (3,072 B → 8 B) if excluded.

---

## 5. Block A — FeFET centroid array

### What is stored

The IVF centroid matrix, `centroids.npy` = **(128, 768) float32**.

```
analog weights = nlist × D = 128 × 768 = 98,304
```

### Cell topology

From the SPICE deck `h_aimdc_sim/fefet_cell_read_v4.py:generate_fefet_cell_deck_v4`
(2-FeFET differential cell, one per weight):

```spice
V_W1  SL_F    G1   DC {w}                * weight = programmed Vth (rigid shift)
V_W2  SL_F_B  G2   DC {V_FOLD - w}       * exact complement
XMF1  MBL_F  G1  ML_F  fefet             * drain=MBL_F, gate=G1, source=ML_F
XMF2  MBL_F  G2  ML_F  fefet
BSLB  SL_F_B 0  V={V_FOLD - V(SL_F)}     * input complement
```

- **2 FeFETs per stored weight** (differential pair sharing the match line `ML_F`).
- The weight is the programmed **threshold voltage** (validated as a rigid Vth shift with
  residual at the noise floor), *not* a resistance.
- Currents sum on the match line in the **linear/current domain** (`reduce="linear_sum"`);
  log-domain reduction is deprecated for this path.

```
FeFET device count = 2 × 128 × 768 = 196,608
```

Python twin: `aimdc_nvm_device_distance/__init__.py:_bit_current`, with
`g1 = V_SL − w − V_ML`, `g2 = w − V_SL − V_ML`, `I = I(g1) + I(g2)`.
(The `V_FOLD` terms cancel algebraically, so the complement is exact and the deprecated
inverter-VTC LUT has no role.)

### Measured device characteristics

From `h_aimdc_sim/fefet_ref_fit_smu.json` (`model: fefet_ref_lut_v1`, `backend: lut`,
SMU B1500 measurement, `reference_source: fefet_vth_1.0 t=0, Vd=0.1V`):

| Property | Value |
|---|---|
| LUT grid | 121 points, V ∈ [−5.0, +1.0], step 0.05 V |
| Valid range `v_valid` | **[−5.0, +1.0]** (asymmetric) |
| Current range | 1.960e−13 A … 2.273e−07 A |
| Dynamic range | **1.16 × 10⁶ ×** |
| Current floor `i_floor` | 1.96e−13 A |
| Knee `v_knee` | −1.15 V |
| Measured `V_DS` | 0.1 V |
| `power_law_p` | 1.15 (linear/triode; saturation unreachable due to read-disturb limit) |
| `rel_noise` | 0.05 |

### Operating point (embedding → gate voltage)

`fefet_ref_fit_smu.scaler.json`:

```
x_lo = -0.08004254564642906     # 1st percentile of embedding values
x_hi =  0.0906163961440325      # 99th percentile
v_min, v_max = -1.0, +1.0       # embedding voltage window
embedding_dim = 768
```

Linear map: `V = v_min + (x − x_lo)/(x_hi − x_lo) × (v_max − v_min)`.

With `V_SL, w ∈ [−1, +1]`, the differential drive is `g = V_SL − w ∈ [−2, +2]`, so
`V_gs = g − V_ML`. Sweeping `V_ML` (a real source rail, `V_ML ML_F 0 DC {v_ml}`):

| `V_ML` (V) | `V_gs` range | inside `v_valid`? | I dynamic range over the window |
|---|---|---|---|
| 0.0 | [−2.00, +2.00] | no — **24.9 %** out | 11.5 × |
| 0.7 | [−2.70, +1.30] | no — 7.7 % out | 1.36 × 10³ |
| 1.0 | [−3.00, +1.00] | yes | 2.25 × 10⁴ |
| **1.4** | **[−3.40, +0.60]** | **yes** | **2.34 × 10⁵** |
| 2.0 | [−4.00, 0.00] | yes | 2.53 × 10⁴ |
| 2.5 | [−4.50, −0.50] | yes | 1.09 × 10³ |

`V_ML = 1.4 V` is near-optimal: zero extrapolation **and** peak current contrast, because it
centres the knee (−1.15 V) inside the operating window. This is the value used in the
current runs.

---

## 6. Block B — IGZO capacitor (AIMDC) array

### What is stored

The MMR selected buffer: anchors + already-selected chunks, `N × D` where
`N = |anchor_entries| + |mmr_buffer|`, bounded by `top_k`. Measured on the 108-combo run,
the final buffer is always exactly `top_k`:

| `top_k` | buffer rows `N` | analog weights `N × 768` |
|---|---|---|
| 5 | 5 | 3,840 |
| 10 | 10 | 7,680 |
| 20 | 20 | 15,360 |
| 50 | 50 | 38,400 |

### Cell topology

From `h_aimdc_sim/aimdc_sim_core.py:generate_spice_deck` — differential capacitive-boosting
cell, **one pair per dimension**:

```spice
* ---- Left cell ----
XW1   BL      WL   SN      igzo_tft     * write transistor
Ccpl1 SL_bar  SN   {C_BOOST}            * boost capacitor
XR1   MBL     RWL  N_mid1  igzo_tft     * read transistor
XS1   N_mid1  SN   ML      igzo_tft     * sense transistor
* ---- Right cell (differential) ----
XW2   BL_bar  WL   SN_bar  igzo_tft
Ccpl2 SL      SN_bar {C_BOOST}
XR2   MBL     RWL  N_mid2  igzo_tft
XS2   N_mid2  SN_bar ML    igzo_tft
```

Per stored weight (one embedding dimension):

```
6 IGZO TFTs + 2 boost capacitors     (C_BOOST = 100 fF each; 1e-13 F in the fit JSON)
```

The weight lives as `±V_PRG` on the **floating storage nodes** `SN` / `SN_bar`
(`.IC V(SN)={V_PRG} V(SN_bar)={-V_PRG}`) — capacitor-held, hence volatile.

```
IGZO TFT count  = 6 × N × 768
boost capacitors = 2 × N × 768
```

| `top_k` | IGZO TFTs | boost caps |
|---|---|---|
| 5 | 23,040 | 7,680 |
| 10 | 46,080 | 15,360 |
| 20 | **92,160** | **30,720** |
| 50 | 230,400 | 76,800 |

Python twin: `aimdc_device_distance/__init__.py:_bit_current`, with
`v_sn = V_PRG − V_SL − V_ML`, `v_sn_bar = −V_PRG + V_SL − V_ML`,
`I = 10^f(v_sn) + 10^f(v_sn_bar)` where `f` is the fitted composite tanh+cubic log-current model
(7 parameters, `h_aimdc_sim/igzo_fit.json`, fit RMSE 0.126 dec).

### Operating point

`h_aimdc_sim/igzo_fit.scaler.json` / CLI defaults:

```
x_lo = -0.06479702144861221 , x_hi = 0.06511063873767853   # 1st/99th pct of embeddings
scaler window   : v_min, v_max = -1.0, +1.0
run-time window : --device_v_min -3.0  --device_v_max 3.0   (explicit override wins)
C_BOOST = 1e-13 F , V_MBL = 0.1 V , V_RWL = 3.0 V , V_WL = -3.0 V
T_RAMP = 9.9 µs , T_APPLY = 10 µs , T_SAMPLE = 15 µs , T_END = 20 µs
```

Software-L2 calibration `h_aimdc_sim/igzo_fit.k.json`: `k = 1.6787e-4`
(ratio p5 1.526e−4 / p95 1.892e−4, n = 128×128, calibrated at window [−3, +3],
`reduction_mode: "sum"`).

---

## 7. Device access counts per query (for energy / bandwidth, not capacity)

### Block A (FeFET, read-only)

One coarse search per query per facet:

```
1 × (1 query × 128 centroids × 768 dims)  = 98,304 cell reads
```

`nprobe = 32` selects the 32 nearest centroids *after* all 128 distances are computed, so the
full array is read regardless of `nprobe`.

### Block B (IGZO, read + write)

Per MMR step, one `pair_matrix(cand[1×768], selected[N×768])` call, i.e. `N × 768` cell reads,
with the `N × 768` weights **rewritten** whenever the buffer changes.

Additionally — and this is easy to miss — `_mmr_diversity_core`
(`online_accelerator_device.py:708`, on by default via `--standardize_mmr_terms`) performs a
**separate per-query calibration pass** of up to `min(pool, 32)` extra `pair_matrix` calls
before the main loop. Empirically this is what makes
`tests/test_mmr_single_readout.py::test_call_count_equals_mmr_stream_length` fail (expects 3
calls, observes 7). Any "one readout per MMR step" energy claim must account for it separately.

```
readouts/query ≈ (#streamed candidates × N × 768)          main loop
               + (min(pool,32) × (min(pool,32)−1) × 768)   standardization pass
```

Candidate pool size ≈ `nprobe × chunks-per-centroid`, capped by `top_r = 128` per centroid;
for hotpot at `nprobe = 32` that is ≈ 32 × 76.3 ≈ 2,400 candidates before dedup.

---

## 8. Precision / noise assumptions

`noise_configs/*.json` — all mechanisms default to **off** (deterministic); these are the
configured sweep points:

| Config | Fields |
|---|---|
| `clean.json` | `rng_seed: 42` only |
| `d2d.json` | `sigma_vth: 0.03` V, `sigma_log_mu: 0.05` dec |
| `d2d_retention.json` | + `retention_tau: 10.0` s, `t_hold: 0.01` s |
| `full.json` | + `adc_bits: 8`, `adc_i_fullscale: 1e-6` A |

Available but unused mechanisms in `NoiseModel`: `ktc_C` (kTC on the boost cap,
σ = √(k_B·T/C), T = 300 K), `sigma_alpha` (coupling-ratio variation), `flicker_sigma`,
`rtn_sigma`, `shot_enable` (with `read_bandwidth_hz = 1e6`).

**Caveats to carry into any calculation:**

- `sigma_vth = 0.03 V` is **ASSUMED, not measured** — the fit JSON states
  `"assumed/unmeasured (SWEEP_REPEAT=1; no cycle-to-cycle data)"`.
- The `V_DS` scaling factor is an **UNVALIDATED HEURISTIC**: only one `V_DS` point (0.1 V)
  was measured; `step_pos × vds/√(vds²+vds_ref²)` was never fitted.
- `power_law_p` fit hit its bound (`n = 2.5` within 1e−3 of the [0.5, 2.5] limit).
- No cell area, pitch, or process node exists anywhere in this repo — area/density must come
  from an external source.
- The number of distinct analog **levels** required per weight is not fixed anywhere in the
  code. Weights are stored as `float64` in simulation; the only quantization present is the
  optional 8-bit **output ADC** on the current sum, not the stored weight. A weight-precision
  requirement has to be derived (e.g. by sweeping quantization against retrieval recall) —
  it is not a measured property of this pipeline today.

---

## 9. Legacy / alternative device fits (do not mix)

| File | Model | Params | Used by |
|---|---|---|---|
| `fefet_ref_fit_smu.json` | `fefet_ref_lut_v1` | 121-pt LUT | **current** FeFET centroid path |
| `igzo_fit.json` | `igzo_composite_v1` | 7 (tanh+cubic) | **current** IGZO MMR path |
| `igzo_fit_v3.json` | `igzo_powerlaw_v3` | 8 | legacy IGZO+inverter centroid path |
| `fefet_ref_fit.json` | earlier FeFET fit | — | superseded |

`sweep_eval.py` still **defaults** `--centroid_fit_path` to `igzo_fit_v3.json` with
`--centroid_reduce sum`, i.e. the legacy path. The FeFET path only runs when
`--centroid_fit_path h_aimdc_sim/fefet_ref_fit_smu.json --centroid_reduce linear_sum` is passed
explicitly. Confirm which fit a given run used before attributing numbers to FeFET —
the run manifest does not record it.

`igzo_fit_v3.json` operating point (`nvm_operating_point.json`, legacy):
VDD 3.0, VGG 3.0, VSS −3.0, V_MBL 0.5, V_ML 0.0, v_min/v_max ±1.5,
current floor 1.17e−10 A, ceiling 1.28e−06 A, **dynamic range 1.09 × 10⁴**.

---

## 10. Quick-reference summary

```
D (embedding dim)            = 768        float32, L2-normalized
nlist (IVF centroids)        = 128
m (PQ subspaces)             = 8    ×  k* = 256  ⇒ 8 B/chunk PQ code
chunks                       = 9,767 (hotpot) | 47,765 (cuad)

Block A — FeFET, non-volatile, written once
  weights                    = 128 × 768        = 98,304
  devices (2 FeFET/weight)   = 196,608
  V_gs window @ V_ML=1.4 V   = [-3.40, +0.60]   ⊂ v_valid [-5, +1]
  I range                    = 1.96e-13 .. 2.27e-07 A   (1.16e6 dynamic range)

Block B — IGZO + boost cap, volatile, rewritten per MMR step
  weights                    = top_k × 768      (20 × 768 = 15,360 at the headline top_k)
  devices (6 TFT/weight)     = 92,160 TFT + 30,720 caps @ top_k=20
  C_BOOST                    = 100 fF/cap
  timing                     = T_APPLY 10 µs, T_SAMPLE 15 µs, T_END 20 µs

Digital index (hotpot)       ≈ 42.3 MB total
  of which raw_embeddings    = 30.0 MB   (droppable if only the PQ path is served)
  fixed (codebook+rot+cent)  = 3.54 MB   (independent of corpus size)
```

---

## Provenance

| Number | Source |
|---|---|
| Index config, artifact shapes/sizes | `offline_data_*/config.pkl`, `os.path.getsize`, `np.load` |
| FeFET cell topology | `h_aimdc_sim/fefet_cell_read_v4.py` (SPICE deck) |
| FeFET I-V, valid range, knee | `h_aimdc_sim/fefet_ref_fit_smu.json` |
| IGZO cell topology | `h_aimdc_sim/aimdc_sim_core.py:generate_spice_deck` |
| IGZO fit + circuit params | `h_aimdc_sim/igzo_fit.json`, `igzo_fit.scaler.json`, `igzo_fit.k.json` |
| Embedding→voltage scaler | `*.scaler.json` (1st/99th percentile map) |
| Buffer sizes, candidate counts | `sweep_exports/20260813_162948_*/retrieval_*.jsonl` (10,800 records) |
| Noise configs | `noise_configs/*.json` |
| Readout counts | `online_accelerator_device.py:708` (`_mmr_diversity_core`), `:899` |
