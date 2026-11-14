# Stage 3 run `llm_v2_s1` (llm mutator)

Goal: maximise the NO2 sensing score (charge to NO2 x reversibility x selectivity vs CO). Population 8, up to 10 xTB-scored children per generation, gap pre-filter 0.2-1.6 eV, seed 1.

| gen | proposed | valid | xTB-scored | best this gen | best so far | mean scored | time (min) |
|---|---|---|---|---|---|---|---|
| 1 | 15 | 12 | 10 | 0.293 | 0.322 | 0.164 | 4.6 |
| 2 | 20 | 12 | 10 | 0.312 | 0.322 | 0.161 | 5.1 |
| 3 | 22 | 12 | 10 | 0.323 | 0.323 | 0.218 | 4.5 |
| 4 | 20 | 10 | 10 | 0.312 | 0.323 | 0.230 | 5.5 |
| 5 | 17 | 13 | 10 | 0.293 | 0.323 | 0.190 | 4.8 |
| 6 | 24 | 14 | 10 | 0.297 | 0.323 | 0.185 | 5.4 |
| 7 | 25 | 12 | 9 | 0.324 | 0.324 | 0.200 | 4.7 |
| 8 | 20 | 13 | 10 | 0.334 | 0.334 | 0.201 | 5.4 |
| 9 | 15 | 12 | 10 | 0.311 | 0.334 | 0.179 | 4.6 |
| 10 | 29 | 12 | 10 | 0.342 | 0.342 | 0.211 | 6.4 |

## Best new GQDs

| id | parent | edit | hex | gap (xTB) | E_NO2 | NO2 | charge | vs CO | score | parent score |
|---|---|---|---|---|---|---|---|---|---|---|
| g10c025 | g08c008 | ADD [-6, 5]; ADD [0, 2] | 33 | 0.29 | -0.48 | phys | 0.34 | +0.24 | 0.342 | 0.334 |
| g08c008 | g07c006 | REMOVE [-6, 2]; REMOVE [0, 5] | 30 | 0.30 | -0.47 | phys | 0.33 | +0.23 | 0.334 | 0.313 |
| g10c018 | g07c010 | ADD [-5, 1]; ADD [-1, 2] | 36 | 0.32 | -0.45 | phys | 0.33 | +0.18 | 0.333 | 0.324 |
| g10c001 | g08c008 | ADD [-6, 3]; ADD [0, 5] | 32 | 0.42 | -0.46 | phys | 0.33 | +0.22 | 0.325 | 0.334 |
| g07c010 | g02c004 | REMOVE [-5, 0]; REMOVE [0, 0] | 34 | 0.34 | -0.44 | phys | 0.32 | +0.20 | 0.324 | 0.312 |
| g03c005 | g02c004 | REMOVE [-5, 0]; REMOVE [-5, 3] | 34 | 0.44 | -0.46 | phys | 0.32 | +0.19 | 0.323 | 0.312 |
| g07c006 | gqd_18941 | ADD [-6, 2]; ADD [0, 5]; REMOVE [-6, 3] | 32 | 0.26 | -0.41 | phys | 0.31 | +0.18 | 0.313 | 0.322 |
| g02c004 | gqd_23821 | REMOVE [-5, 5]; REMOVE [0, 5] | 35 | 0.25 | -0.42 | phys | 0.31 | +0.19 | 0.312 | 0.301 |
| g08c015 | gqd_18941 | REMOVE [-5, 6]; REMOVE [-1, 2] | 29 | 0.59 | -0.44 | phys | 0.31 | +0.19 | 0.312 | 0.322 |
| g04c009 | gqd_18941 | ADD [-5, 5]; ADD [-1, 1] | 33 | 0.27 | -0.47 | phys | 0.31 | +0.26 | 0.312 | 0.322 |

## Why children were rejected (before xTB)

- molecular graph: 32
- duplicate: 24
- ADD [-1, 5]: 4
- ADD [-4, 5]: 3
- has 1 hole(s) (an empty region enclosed by hexagons): 3
- ADD [-2, 1]: 3
- REMOVE [0, 0]: 2
- ADD [-1, 3]: 2
- ADD [0, 4]: 2
- ADD [-5, -1]: 2
- ADD [-4, 7]: 1
- ADD [-3, 4]: 1
- ADD [-5, 3]: 1
- ADD [-5, 5]: 1
- ADD [-5, 6]: 1
- ADD [-2, 2]: 1
- ADD [-1, 6]: 1
- ADD [-2, -1]: 1
