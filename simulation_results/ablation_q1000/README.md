# Simulation ablation on the 1,000 HotpotQA questions (Supplementary Note 6.4, Supplementary Table 14)

Produced with h_rag v1.1.0 (`scripts/run_ablation_q1000.sh`, then `scripts/analyze_ablation.py`),
k = 5, λ = 0.7, γ = 0.7, τ_dup = −1.0, distractor setting, retrieval only.

| Arm (manifest `arm`) | Diversity distance in the dynamic tier |
|---|---|
| `digital_l2` (derived from the `digital_mmr_std` run) | none: relevance-only top-5 |
| `digital_mmr_std` | exact Euclidean distance with the identical procedure (Algorithm S1: calibration pass, standardized gate, spread-matched score; `--mmr_mode software_std`) |
| `digital_mmr_plain` | exact Euclidean distance without the per-query standardization (`--mmr_mode software`) |
| `device_avg` | calibrated DeCAP array model (the reported configuration); identical to the reported run `20260826_223418` for 1,000 of 1,000 questions |
| `device_var` | `device_avg` plus frozen per-cell variation of the DeCAP coupling ratio, gain and branch threshold offset; scenario and die (seed) in the manifest, configs in `noise_configs/` |

Variation at 1× (from `4t2c_array/4t2c_distance_paper_20260904.xlsx`, see the docstring of
h_rag `scripts/make_ablation_noise_configs.py`): coupling-ratio CV 0.067 (six cells), gain s.d.
0.12 in log10 (curvature s.d. 0.31 in ln over 18 calibrations, coupling share removed),
branch-threshold s.d. 0.31 V in simulator volts (notch s.d. 75 mV over a 2.06 V physical query
span, scaled to the 6 V simulator window, × √2 per branch).

Files: `ablation_q1000.md` (table), `ablation_q1000_summary.csv` (mean, s.d., range over dies),
`ablation_q1000_runs.csv` (one row per run, with the paired-bootstrap interval of MMR − L2 full
support@5), `ablation_q1000_comparisons.json` (paired comparisons of the reference arms and the
identity check), `ablation_q1000_perquestion.csv.gz` (retrieved paragraph ids and full support@5
of both arms for every run and question; replaces the 1 GB of per-run JSONL), `manifest.tsv`,
`runs/<run_id>/` (flags, manifest and aggregate grid of each run). The query embeddings were
replayed from `sweep_exports/query_emb_q1000_searchtext.npz` written by h_rag
`scripts/dump_search_text_embeddings.py` (`--query_emb_map`).
