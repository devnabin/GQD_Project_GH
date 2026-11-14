# Stage 3d L2: linked-carbon calibration (GFN2-xTB)

21 hand-made designs (`designs.py`), all five gases, sites ring centre/edge, triple bond, pore. Twin: Stage 3c `twin()` unchanged (20 ppb NO2, 50% RH, recovery spec 300 s). Fused comparison: the 50 Stage 3a calibration GQDs (same xTB protocol).

## Linked vs fused

|  | fused | linked |
|---|---|---|
| set | fused GQDs, Stage 3a (50) | linked carbon (21) |
| n | 50 | 21 |
| all converged | 50 | 21 |
| gap median (eV) | 1.02 | 1.99 |
| E_NO2 median (eV) | -0.642 | -0.967 |
| NO2 chemisorbed | 29/50 | 19/21 |
| q_NO2 median (e) | -0.212 | -0.228 |
| strongest interferent | CO 50 | CO 20, H2O 1 |
| NO2-CO margin median (eV) | 0.384 | 0.756 |
| score > 0 | 38 | 14 |
| score median | 0.142 | 0.0199 |
| score max | 0.322 | 0.197 |
| meet 5-min recovery | 32 | 5 |
| twin response max (e/site) | 0.338 | 0.244 |

## NO2 binding by site type (best orientation at each site, all linked designs)

| site_type | n | E_NO2_median | E_NO2_min | E_NO2_max | chemisorbed | q_NO2_median |
|---|---|---|---|---|---|---|
| pore | 9 | -0.261 | -1.03 | -0.0155 | 2 | -0.113 |
| ring | 42 | -0.232 | -0.973 | -0.168 | 11 | -0.155 |
| triple | 21 | -0.951 | -1.19 | -0.192 | 15 | -0.228 |

## All linked designs (by Stage 3a score)

| design | formula | gqd_gap_eV | E_NO2_eV | site_NO2 | NO2_chemisorbed | q_NO2_e | selectivity_margin_eV | sensing_score | recovery_s | response_20ppb_RH50_e | humidity_equiv_ppb |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gy_ring6 | C48H24 | 2.8 | -0.598 | centre/NO2 | True | -0.197 | 0.438 | 0.197 | 0.0128 | 0.000322 | 0.00635 |
| pyrene_row3_n1 | C52H26 | 2.42 | -0.743 | edge/NO2 | True | -0.199 | 0.55 | 0.128 | 3.59 | 0.0626 | 6.79e-05 |
| naph_row4_n1 | C46H26 | 2.16 | -0.772 | centre/NO2 | True | -0.196 | 0.605 | 0.111 | 11.3 | 0.115 | 1.64e-05 |
| gy_row6 | C46H26 | 2.16 | -0.214 | triple/NO2 | False | -0.137 | 0.0734 | 0.101 | 4.07e-09 | 7.12e-11 | 4.24e+04 |
| gy_tri6 | C54H18 | 1.98 | -0.286 | pore/NO2 | False | -0.14 | 0.0641 | 0.09 | 6.76e-08 | 1.21e-09 | 9.78e+04 |
| coronene_dimer_n1 | C50H22 | 2.09 | -0.864 | centre/NO2 | True | -0.223 | 0.658 | 0.0758 | 404 | 0.219 | 1e-06 |
| gdy_hex7 | C90H18 | 1.76 | -0.919 | triple/NO2 | True | -0.24 | 0.654 | 0.0484 | 3.49e+03 | 0.24 | 1e-06 |
| ovalene_star2_n2 | C52H22 | 1.68 | -0.925 | triple/NO2 | True | -0.231 | 0.74 | 0.0431 | 4.36e+03 | 0.23 | 1e-06 |
| coronene_star3_n2 | C54H24 | 2.12 | -0.943 | triple/NO2 | True | -0.235 | 0.758 | 0.0334 | 8.79e+03 | 0.235 | 1e-06 |
| gdy_tri6 | C72H18 | 1.9 | -0.951 | triple/NO2 | True | -0.241 | 0.686 | 0.0293 | 1.2e+04 | 0.241 | 1e-06 |
| naph_tri3_n2 | C42H18 | 1.99 | -0.967 | triple/NO2 | True | -0.241 | 0.73 | 0.0199 | 2.21e+04 | 0.24 | 3.34e-06 |
| gdy_ring6 | C60H24 | 2.53 | -0.967 | triple/NO2 | True | -0.234 | 0.795 | 0.0192 | 2.23e+04 | 0.234 | 1e-06 |
| ovalene_dimer_n1 | C66H26 | 1.66 | -0.973 | centre/NO2 | True | -0.199 | 0.765 | 0.0133 | 2.83e+04 | 0.199 | 1e-06 |
| gdy_rhomb4 | C44H14 | 2.23 | -0.985 | triple/NO2 | True | -0.241 | 0.723 | 0.00922 | 4.41e+04 | 0.241 | 1e-06 |
| gy_rhomb9 | C86H22 | 1.67 | -1.01 | triple/NO2 | True | -0.224 | 0.791 | 0 | 1.19e+05 | 0.224 | 1e-06 |
| gdy_row5 | C46H22 | 2.01 | -1.01 | triple/NO2 | True | -0.239 | 0.836 | 0 | 1.22e+05 | 0.239 | 1e-06 |
| gy_hex7 | C66H18 | 1.69 | -1.03 | triple/NO2 | True | -0.224 | 0.83 | 0 | 2.53e+05 | 0.224 | 1e-06 |
| coronene_dimer_n2 | C52H22 | 2.02 | -1.04 | triple/NO2_O | True | -0.244 | 0.83 | 0 | 3.31e+05 | 0.244 | 1e-06 |
| coronene_star6_n1 | C72H36 | 1.92 | -1.11 | triple/NO2 | True | -0.227 | 0.885 | 0 | 5.86e+06 | 0.227 | 1e-06 |
| circum_star2_n1 | C70H26 | 1.46 | -1.19 | triple/NO2 | True | -0.231 | 0.988 | 0 | 1.39e+08 | 0.231 | 1e-06 |
| circum_star6_n2 | C114H42 | 1.27 | -1.11 | triple/NO2 | True | -0.228 | 0.906 | 0 | 5.78e+06 | 0.228 | 1e-06 |

## Top 5 by twin score

| design | formula | gqd_gap_eV | E_NO2_eV | site_NO2 | NO2_chemisorbed | q_NO2_e | selectivity_margin_eV | sensing_score | recovery_s | response_20ppb_RH50_e | humidity_equiv_ppb |
|---|---|---|---|---|---|---|---|---|---|---|---|
| naph_row4_n1 | C46H26 | 2.16 | -0.772 | centre/NO2 | True | -0.196 | 0.605 | 0.111 | 11.3 | 0.115 | 1.64e-05 |
| pyrene_row3_n1 | C52H26 | 2.42 | -0.743 | edge/NO2 | True | -0.199 | 0.55 | 0.128 | 3.59 | 0.0626 | 6.79e-05 |
| gy_ring6 | C48H24 | 2.8 | -0.598 | centre/NO2 | True | -0.197 | 0.438 | 0.197 | 0.0128 | 0.000322 | 0.00635 |
| gy_tri6 | C54H18 | 1.98 | -0.286 | pore/NO2 | False | -0.14 | 0.0641 | 0.09 | 6.76e-08 | 1.21e-09 | 9.78e+04 |
| gy_row6 | C46H26 | 2.16 | -0.214 | triple/NO2 | False | -0.137 | 0.0734 | 0.101 | 4.07e-09 | 7.12e-11 | 4.24e+04 |
