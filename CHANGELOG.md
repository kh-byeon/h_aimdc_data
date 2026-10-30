# Changelog

## v1.1.0 — 2026-10-30 (revised manuscript)

Paper: "Monolithic integration of ferroelectric and dielectric capacitors on a unified oxide-TFT
platform for in-memory distance computing" (revised title; the original submission was titled
"Diversity-aware retrieval-augmented generation acceleration at the edge enabled by FeFET-IGZO
heterogeneous analog in-memory distance computing").

Corrected
- TIA-mode current columns (`I_A`, `I_uA`, `i_uA`) in `4t2c_array/4t2c_distance_paper_20260904.xlsx`,
  `4t2c_auto_dataset_0903.xlsx`, `4t2c_auto_0903_curves.csv`, `4t2c_notch_dataset_chip6_R0C0_0904-0905.xlsx`
  and `igzo_4t2c_retention/4t2c_map_chip6_4t2c_a_mbl-2p50_0902_155745.xlsx`: rescaled by 1 MΩ / 27 kΩ = 37.04,
  because the logger assumed a 1 MΩ transimpedance resistor and the board uses 27 kΩ. ADC codes and voltages
  are unchanged; the logger's `TIA_RF_OHM` entries are kept as written. Texts that quoted 1 MΩ or currents
  derived from it (README sheets, `4t2c_array/4t2c_distance_paper_notes_20260904.md`,
  `plot_4t2c_notch_response.py`) now give 27 kΩ.
- Integrator-mode current columns in `2t1c_endurance/endurance_20260724_203233.xlsx` and
  `FeFET_retention/*.xlsx` renamed `*_nominal` (sheet `matrix_I_uA_nominal`): they depend on an integration
  capacitance that could not be verified. The analyses use ADC codes.
  All of the above is done by `scripts/correct_currents_v110.py` (worksheet-level edit; formatting kept).

Added
- `plot_fig4f.py`, `simulation_results/fig4f/`: Fig. 4f redrawn from the values of Supplementary Table 2.
- `plot_fig5d_operands.py` (replaces `plot_fig5d_traffic.py`): Fig. 5d as the idealized count of
  selected-set operands moved per query, without ratio arrows, with the labels "Re-read baseline" and "U-AIMDC".
- `plot_fig5e_memory.py`, `simulation_results/fig5e/fig5e_numbers.json`: Fig. 5e.
- `simulation_results/ablation_q1000/`: simulation ablation (Supplementary Note 6.4, Supplementary Table 14),
  produced with h_rag v1.1.0.

Changed
- README, CITATION: revised title and terminology (U-AIMDC; FeCAP and DeCAP cells); measurement-interface and
  current-unit section; session labels (`chip3`, `chip6`) identified as session names on one die; Fig. 4f,
  5d, 5e and Supplementary Table 14 rows of the figure index; FeFET endurance files now feed Fig. 4f.

## v1.0.0 — 2026-10-21

Version cited in the original submission.
