# Stage 3c sensor twin: first results

85 GQDs (Stage 3a calibration + full checks of the evolution runs). Conditions: 20 ppb NO2, 50% RH, 10 ppb NH3, 0.5 ppm CO, 298 K. Spec: recovery <= 300 s. O2 not included. xTB energies and charges.

- Entropy cost T*dS at 298 K (eV): NO2 -0.31, H2O -0.26, NH3 -0.26, CO -0.27
- GQDs meeting the recovery spec: 67 of 85
- Spearman rank correlation, Stage 3a score vs twin score: 0.62

## Top 10 by twin score

| id | gqd_gap_eV | E_NO2_eV | NO2_chemisorbed | score_stage3a | recovery_s | response_20ppb_RH50_e | humidity_equiv_ppb |
|---|---|---|---|---|---|---|---|
| gqd_83340 | 1.9 | -0.814 | True | 0.109 | 56.7 | 0.205 | 5.2e-06 |
| gqd_24021 | 0.211 | -0.817 | True | 0.0932 | 64.2 | 0.181 | 3.96e-06 |
| gqd_58903 | 0.526 | -0.802 | True | 0.104 | 36.6 | 0.174 | 1.03e-05 |
| gqd_70353 | 1.48 | -0.801 | True | 0.106 | 34.8 | 0.174 | 6.8e-06 |
| gqd_18216 | 0.534 | -0.72 | True | 0.144 | 1.48 | 0.0327 | 0.0015 |
| gqd_81287 | 0.69 | -0.662 | True | 0.175 | 0.158 | 0.0041 | 0.00472 |
| gqd_13400 | 0.562 | -0.653 | True | 0.182 | 0.107 | 0.00283 | 0.00282 |
| gqd_12066 | 1.22 | -0.632 | True | 0.204 | 0.0475 | 0.00133 | 0.118 |
| gqd_29688 | 1.77 | -0.624 | True | 0.196 | 0.035 | 0.000928 | 0.012 |
| gqd_95498 | 0.698 | -0.611 | True | 0.208 | 0.021 | 0.00057 | 0.0174 |

## Top 10 by Stage 3a score

| id | gqd_gap_eV | E_NO2_eV | NO2_chemisorbed | score_stage3a | recovery_s | response_20ppb_RH50_e | humidity_equiv_ppb |
|---|---|---|---|---|---|---|---|
| random_v2_s1/g09c010 | 0.32 | -0.516 | False | 0.356 | 0.000523 | 2.37e-05 | 2.26 |
| random_v2_s2/g05c010 | 0.261 | -0.521 | False | 0.355 | 0.000634 | 2.87e-05 | 2.18 |
| random_v2_s1/g06c006 | 0.336 | -0.512 | False | 0.353 | 0.000453 | 2.04e-05 | 2.78 |
| random_v2_s2/g02c005 | 0.43 | -0.473 | False | 0.349 | 9.85e-05 | 4.39e-06 | 0.736 |
| llm_v2_s3/g05c019 | 0.305 | -0.502 | False | 0.349 | 0.000305 | 1.36e-05 | 0.389 |
| llm_v2_s3/g09c016 | 0.294 | -0.505 | False | 0.348 | 0.000338 | 1.5e-05 | 0.154 |
| llm_v2_s2/g02c005 | 0.391 | -0.461 | False | 0.343 | 6.29e-05 | 2.75e-06 | 48 |
| llm_v2_s1/g10c025 | 0.285 | -0.482 | False | 0.341 | 0.000141 | 6.12e-06 | 32 |
| llm_s0/g10c004 | 0.289 | -0.498 | False | 0.341 | 0.000262 | 1.14e-05 | 0.261 |
| llm_s0/g10c007 | 0.297 | -0.496 | False | 0.34 | 0.000245 | 1.06e-05 | 0.394 |
