# h_aimdc_data — device measurements, simulation results and figure scripts

Data underlying **"Diversity-aware retrieval-augmented generation acceleration at the edge
enabled by FeFET-IGZO heterogeneous analog in-memory distance computing"**
(K. A. Byun, H. S. Choi, C. Joe, D. H. Han, M. H. Park and S. Kim, Seoul National University).

The repository holds (i) the raw and processed electrical measurements of the FeFET and
IGZO-capacitor cells and 2 × 2 arrays (Figs. 3 and 4), (ii) the outputs of the
measurement-calibrated system simulation on CUAD and HotpotQA (Figs. 2 and 5, Supplementary
Data 1), and (iii) the Python scripts that turn these files into the figure panels.
The simulation code itself is in the companion repository
**[h_rag](https://github.com/kh-byeon/h_rag)** (tag `v1.0.0`).

Version: **v1.0.0**.

## Figure-by-figure index

| Panel | Data file(s) | Plot script |
|---|---|---|
| Fig. 2b (reads per write vs lifetime) | `simulation_results/fig2/fig2_tiers.csv`, `fig2_counts.csv`, `fig2_measured_inputs.csv` | `plot_fig2_tiers.py` |
| Fig. 2c (stored-value precision per tier) | `simulation_results/fig2/fig2_precision.csv`, `fig2_precision_bits.csv`, `fig2_precision_meta.json` | `plot_fig2_precision.py` |
| Fig. 3b (FeFET cell response, 25 programmed states) | `FeFET_chip3_notch_campaign_20260829.xlsx` | `plot_fefet_notch_shift.py` |
| Fig. 3c (IGZO-capacitor 4T2C cell response, 25 stored values) | `4t2c_notch_dataset_chip6_R0C0_0904-0905.xlsx` (earlier automated campaign: `4t2c_auto_dataset_0903.xlsx`, `4t2c_auto_0903_*.csv`) | `plot_4t2c_notch_campaign.py` (`plot_4t2c_notch_response.py`) |
| Fig. 3e (measured vs predicted distance, 2 × 2 arrays) | `fefet_array/FeFET_2x2_distance_0905-0906.xlsx`, `4t2c_array/4t2c_distance_paper_20260904.xlsx` | `plot_distance_l2.py`, `4t2c_array/plot_figures.py` |
| Fig. 4b (FeFET transfer curve, memory window) | `FeFET_TR/260611/*.xlsx`, `FeFET_TR/*.csv` | `plot_fefet_tr_xlsx.py`, `plot_fefet_transfer.py` |
| Fig. 4c (FeFET retention, 10 h, six read voltages) | `FeFET_retention/*_dac_retention_v2_*.xlsx` | `plot_fefet_retention.py` |
| Fig. 4d (2T1C write endurance, 10¹⁰ cycles) | `2t1c_endurance/endurance_20260724_203233.xlsx`, `degradation_thresholds.csv` | `plot_2t1c_endurance.py` |
| Fig. 4e (FeFET read disturb, 10⁹ reads) | `FeFET_read_disturb_1e9_20260911.xlsx`, `FeFET_read_disturb_supplementary_20260901.xlsx`, `out/blocks_derived.csv`, `out/extended_1e9_checkpoints.csv` | `read_disturb_plots.py` |
| Fig. 4f (retention vs endurance, this work and literature) | literature values and this work's points are tabulated in `Fig5d_draft.py` (file named under an earlier figure numbering); IGZO-capacitor 10 h retention: `igzo_4t2c_retention/` | `Fig5d_draft.py`, `plot_igzo_4t2c_retention.py` |
| Fig. 5a (CUAD cap-on-liability query) | `simulation_results/cuad_fig5a/` | — (figure assembled from the retrieval dump and generation outputs) |
| Fig. 5b, c (HotpotQA, n = 1,000) | `q1000_metrics.xlsx` (Supplementary Data 1), `simulation_results/hotpotqa_q1000/` | `plot_q1000_figures.py`, `table_panel.py` |
| Fig. 5d (memory traffic vs k) | analytical count; N = 6.9 from `simulation_results/write_stats/` | `plot_fig5d_traffic.py` |
| Fig. 5e (memory footprint) | `simulation_results/fig5e_memory_footprint_reference.md` | — |
| Supplementary Table (single-cell stored-value resolution) | `FeFET_chip3_raw_20260828.xlsx` (sheet `Csweep2`, repeat reads), `4t2c_notch_methods_results.md` §9 | — |
| Supplementary Note (HotpotQA additional analyses, incl. the n = 3,500 robustness check) | `simulation_results/hotpotqa_q3500/`, `q1000_metrics.xlsx` | — |

## Device measurement files

All devices were fabricated at Seoul National University (FeFET: TiN/HAO–HZO/TiN ferroelectric
stack on a ZAZ gate dielectric with an In₂O₃/IGZO channel, W/L = 5/5 µm; IGZO-capacitor cells
on the same chip). Each workbook that carries a `README` sheet documents its own columns and
the measurement conditions; a few sheet names are in Korean (the English `README` sheet of the
same workbook explains them). Measurement protocols are summarised in the Methods of the paper.

| File | Content |
|---|---|
| `FeFET_chip3_notch_campaign_20260829.xlsx` | FeFET cell (2-FeFET complementary pair) notch campaign: `summary`, `traverse`, `dose_law` (programming dose = pulse width × pulse count, +5 V / −5 V), `relaxation`, `notch_curves`, raw sweeps `raw_nr2`, `raw_nr3_*`. Notch = vertex of a quadratic fit to the summed half-cell output, read at V_D = −1.5 V. 25 states spanning 1.31 V, differential-law slope 0.99, R² = 0.999 (Fig. 3b). |
| `FeFET_chip3_raw_20260828.xlsx` | Device I–V blocks and the C-sweep probes/curves; `Csweep2` holds the 8 repeat reads at C = 0 used for the repeat precision (σ = 3.5 mV, Supplementary Table 1). |
| `FeFET_read_disturb_1e9_20260911.xlsx`, `FeFET_read_disturb_supplementary_20260901.xlsx` | Read-disturb runs on chip 6: 1 µs, 0 → +1 V read pulses on both gates up to 10⁹ cycles, notch re-measured at every decade; the first file holds the five isolated single-target runs that are quantified in Fig. 4e, the second the full block list, probe and curve originals. `out/blocks_derived.csv` and `out/extended_1e9_checkpoints.csv` are the derived per-block notch shifts. |
| `FeFET_retention/*.xlsx` | FeFET retention at six gate voltages, 1 s – 10 h, with the read budget recorded in `config` (Fig. 4c). |
| `FeFET_TR/` | FeFET transfer curves (V_G = −5 → +5 V and back, V_D = 0.1 V) of several devices; the 6/11 batch (`260611/`) and the 6/27–28 CSV exports (Fig. 4b). |
| `554 3-13#1.xlsx`, `556 2-17.xlsx` | FeFET cycling (10⁰ – 10⁸ cycles, one sheet per decade) — FeFET endurance characterisation, not shown in the main figures (`plot_fefet_endurance.py`). |
| `4t2c_notch_dataset_chip6_R0C0_0904-0905.xlsx` | IGZO 4T2C cell notch campaign on chip 6 (cell R0C0): `SESSIONS`, `NOTCH`, `CONDITIONS`, `FITS`, common-mode scan (`CMSCAN_*`), `NOISE`, `VALIDATION`, `CURVES`. Written as BL0 = +w, BL1 = −w, read at V_MBL = −1.0 V; 25 stored values from −0.6 to +0.6 V (Fig. 3c), repeat precision σ = 8.5 mV. Methods and results are written up in `4t2c_notch_methods_results.md`. |
| `4t2c_auto_dataset_0903.xlsx`, `4t2c_auto_0903_curves.csv`, `4t2c_auto_0903_notch.csv` | Earlier automated 4T2C notch campaign (9/3) with its curve and notch tables. |
| `4t2c_array/4t2c_distance_paper_20260904.xlsx` | IGZO-capacitor array distance measurement (two-column, two-dimensional query): notch curves, α linearity, superposition, 2-D distance map, argmin accuracy, per-cell calibration; notes in `4t2c_distance_paper_notes_20260904.md` (Fig. 3e, IGZO). |
| `fefet_array/FeFET_2x2_distance_0905-0906.xlsx` | FeFET 2 × 2 array distance measurement, one-column calibration (v0, κ, S) and two-column prediction, all rounds and the final condition (Fig. 3e, FeFET). |
| `2t1c_endurance/endurance_20260724_203233.xlsx` | 2T1C test-cell write endurance: −1 V, 5 µs write pulses at a 7 µs period to 10¹⁰ cycles, read at six plate voltages (−2 to +3 V); `config` sheet holds the pulse train; `degradation_thresholds.csv` the 10 % / 20 % drop cycles (Fig. 4d). |
| `igzo_4t2c_retention/` | 4T2C stored-value map at V_MBL = −2.5 V and the 10 h retention summary (drift 0.20 V; lower bound in Fig. 4f). |
| `single_cell_adc_results.xlsx` | Earlier single-cell ADC shift characterisation (`single_cell_shift.py`); not used in the final figures. |

## Simulation results (`simulation_results/`)

Produced with [h_rag](https://github.com/kh-byeon/h_rag) v1.0.0; the run flags are stored next to each result.

| Folder | Content |
|---|---|
| `hotpotqa_q1000/` | The n = 1,000 HotpotQA distractor run (run id `20260826_223418`): `retrieval/` — per-question retrieved sets of both arms (L2, on-the-fly MMR) with the write statistics (`retrieval_*.jsonl`, `run_flags.txt`, `run_manifest.json`); `generation/{fp16,int8,int4}/` — every Llama-3-8B-Instruct answer (`llm_combo_00001.json`); `perq_em_f1_q1000.csv`, `faith_rel_q1000.csv`, `em_f1_q1000.csv` — per-question answer EM/F1, faithfulness/relevance and the per-arm aggregates. |
| `../q1000_metrics.xlsx` | **Supplementary Data 1**: every reported HotpotQA number (headline, retrieval, key contrasts, mechanism, subgroups, faithfulness cut-off sensitivity, power, per-question table) with 95 % paired-bootstrap intervals; `README` sheet inside. |
| `hotpotqa_q3500/` | Larger-sample robustness check (n = 3,500, different index build) referenced in the Supplementary Information. |
| `fig2/` | Analytical operation counts and write statistics behind Fig. 2b (`fig2_counts.csv`, `fig2_tiers.csv`, `fig2_totals.csv`, `fig2_redundancy.csv`, `fig2_measured_inputs.csv`) and the stored-value precision sweep behind Fig. 2c (`fig2_precision*.csv`, `fig2_precision_meta.json`); assumptions and provenance in `fig2_notes.md`. |
| `write_stats/` | Write / readout statistics of the dynamic tier for k = 5, 10, 20 in the distractor and cross scopes (`write_stats_summary.json` + provenance per run): candidates per query N = 6.9, rejection rate, writes per episode, episode length. |
| `cuad_fig5a/` | CUAD intra-document experiment: the cap-on-liability retrieval dump and post-processed answers (`CUAD_CapOnLiability_*.md`), the six L2/MMR × fp16/int8/int4 answers for the Fig. 5a query (`generations/*.txt`), all 50-query answers after reference resolution (`generations/refined_*.jsonl`) and the per-aspect retrieval-coverage evaluation (`evaluation/<quant>/`). |
| `fig5e_memory_footprint_reference.md` | Measured on-chip and DRAM memory footprint of the pipeline (Fig. 5e). |

## Regenerating the figures

```bash
pip install numpy pandas scipy matplotlib openpyxl
python plot_fefet_notch_shift.py          # Fig. 3b
python plot_4t2c_notch_campaign.py        # Fig. 3c
python plot_distance_l2.py                # Fig. 3e
python plot_fefet_retention.py            # Fig. 4c
python plot_2t1c_endurance.py             # Fig. 4d
python read_disturb_plots.py              # Fig. 4e
python plot_fig2_tiers.py     --data simulation_results/fig2   # Fig. 2b
python plot_fig2_precision.py --data simulation_results/fig2   # Fig. 2c
python plot_fig5d_traffic.py              # Fig. 5d
```

Each script writes its panels to `figures/` (or next to its data) and documents its inputs
and options in its docstring (`python <script> --help` where an option exists).

## License

Data (measurement files, simulation outputs, notes): **CC BY 4.0** (`LICENSE`).
Scripts (`*.py`): **MIT** (`LICENSE-CODE`).
The CUAD and HotpotQA excerpts contained in `simulation_results/` derive from CUAD
(The Atticus Project, CC BY 4.0) and HotpotQA (CC BY-SA 4.0), and the generated answers from
Meta-Llama-3-8B-Instruct (Meta Llama 3 Community License).

## Citation

Please cite the paper (preprint/DOI to be added) and this repository.
