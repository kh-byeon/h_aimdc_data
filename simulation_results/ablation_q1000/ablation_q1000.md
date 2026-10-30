| Arm | Variation | Dies | Full support@5 | MMR − L2 | Gold recall@5 | Near-dup rate | Same set as digital MMR | Same set as average device |
|---|---|---|---|---|---|---|---|---|
| digital_l2 | none | 1 | 0.569 | — | 0.750 | 0.833 | 0.417 | 0.430 |
| digital_mmr_std | none | 1 | 0.600 | +0.031 [+0.007, +0.055] | 0.771 | 0.790 | 1.000 | 0.755 |
| digital_mmr_plain | none | 1 | 0.620 | +0.051 [+0.018, +0.083] | 0.794 | 0.685 | 0.367 | 0.330 |
| device_avg | none | 1 | 0.614 | +0.045 [+0.021, +0.069] | 0.781 | 0.791 | 0.755 | 1.000 |
| device_var | all_0.5x | 5 | 0.613 ± 0.000 | +0.044 ± 0.000 | 0.780 ± 0.001 | 0.792 ± 0.000 | 0.749 ± 0.003 | 0.962 ± 0.003 |
| device_var | all_1x | 5 | 0.609 ± 0.003 | +0.040 ± 0.003 | 0.778 ± 0.002 | 0.791 ± 0.001 | 0.749 ± 0.007 | 0.939 ± 0.008 |
| device_var | all_2x | 5 | 0.609 ± 0.002 | +0.040 ± 0.002 | 0.779 ± 0.002 | 0.790 ± 0.000 | 0.751 ± 0.010 | 0.875 ± 0.013 |
| device_var | alpha_1x | 5 | 0.613 ± 0.002 | +0.044 ± 0.002 | 0.781 ± 0.002 | 0.791 ± 0.000 | 0.753 ± 0.003 | 0.971 ± 0.007 |
| device_var | gain_1x | 5 | 0.613 ± 0.002 | +0.044 ± 0.002 | 0.779 ± 0.003 | 0.792 ± 0.000 | 0.748 ± 0.009 | 0.974 ± 0.017 |
| device_var | offset_1x | 5 | 0.610 ± 0.003 | +0.041 ± 0.003 | 0.778 ± 0.002 | 0.792 ± 0.000 | 0.744 ± 0.006 | 0.937 ± 0.014 |

questions per run: 1000
L2 arm identical across all runs: 1.0000
average-device run vs published run 20260826_223418_mmr-capacitor_centroid-nvm: 1000/1000 questions with identical L2 and MMR lists
device_avg − digital_mmr_std: full support@5 +0.014 [+0.001, +0.028], discordant 31 vs 17, exact McNemar P = 0.0595
device_avg − digital_mmr_plain: full support@5 -0.006 [-0.032, +0.020], discordant 89 vs 95, exact McNemar P = 0.713
