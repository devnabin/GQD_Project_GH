# Stage 3 run `llm_v2_s3` (llm mutator)

Goal: maximise the NO2 sensing score (charge to NO2 x reversibility x selectivity vs CO). Population 8, up to 10 xTB-scored children per generation, gap pre-filter 0.2-1.6 eV, seed 3.

| gen | proposed | valid | xTB-scored | best this gen | best so far | mean scored | time (min) |
|---|---|---|---|---|---|---|---|
| 1 | 15 | 10 | 10 | 0.337 | 0.337 | 0.193 | 4.2 |
| 2 | 15 | 10 | 10 | 0.312 | 0.337 | 0.090 | 5.2 |
| 3 | 23 | 10 | 10 | 0.288 | 0.337 | 0.155 | 5.6 |
| 4 | 15 | 12 | 10 | 0.305 | 0.337 | 0.205 | 5.4 |
| 5 | 20 | 12 | 10 | 0.348 | 0.348 | 0.210 | 5.5 |
| 6 | 22 | 13 | 10 | 0.310 | 0.348 | 0.206 | 5.4 |
| 7 | 17 | 11 | 10 | 0.311 | 0.348 | 0.213 | 4.8 |
| 8 | 20 | 11 | 10 | 0.299 | 0.348 | 0.257 | 5.5 |
| 9 | 23 | 14 | 10 | 0.348 | 0.348 | 0.246 | 5.9 |
| 10 | 21 | 11 | 10 | 0.314 | 0.348 | 0.130 | 4.8 |

## Best new GQDs

| id | parent | edit | hex | gap (xTB) | E_NO2 | NO2 | charge | vs CO | score | parent score |
|---|---|---|---|---|---|---|---|---|---|---|
| g05c019 | g01c010 | ADD [-9, 7]; ADD [-9, 9] | 37 | 0.30 | -0.50 | phys | 0.35 | +0.26 | 0.348 | 0.337 |
| g09c016 | g05c019 | ADD [-9, 8]; ADD [-8, 10] | 40 | 0.29 | -0.50 | phys | 0.35 | +0.25 | 0.348 | 0.348 |
| g01c010 | gqd_14650 | ADD [-3, 1]; ADD [-6, 9] | 35 | 0.31 | -0.49 | phys | 0.34 | +0.25 | 0.337 | 0.279 |
| g09c018 | g01c010 | ADD [-9, 8]; ADD [-8, 10] | 38 | 0.23 | -0.45 | phys | 0.33 | +0.21 | 0.327 | 0.337 |
| g05c010 | g02c008 | REMOVE [-5, 0]; REMOVE [0, 0] | 34 | 0.34 | -0.44 | phys | 0.33 | +0.20 | 0.326 | 0.312 |
| g09c020 | g05c010 | ADD [-5, 0]; ADD [-5, 1] | 37 | 0.36 | -0.44 | phys | 0.32 | +0.18 | 0.321 | 0.326 |
| g10c018 | g02c008 | REMOVE [-5, 0]; REMOVE [0, 0] | 34 | 0.37 | -0.43 | phys | 0.31 | +0.19 | 0.314 | 0.312 |
| g05c005 | gqd_18941 | REMOVE [-5, 6]; REMOVE [-1, 2] | 29 | 0.59 | -0.44 | phys | 0.31 | +0.19 | 0.313 | 0.322 |
| g02c008 | gqd_23821 | REMOVE [-5, 5]; REMOVE [0, 5] | 35 | 0.25 | -0.42 | phys | 0.31 | +0.19 | 0.312 | 0.301 |
| g07c012 | gqd_18941 | ADD [-5, 5]; ADD [-1, 1] | 33 | 0.27 | -0.47 | phys | 0.31 | +0.26 | 0.311 | 0.322 |

## Why children were rejected (before xTB)

- molecular graph: 29
- duplicate: 18
- has 1 hole(s) (an empty region enclosed by hexagons): 7
- ADD [-4, 7]: 3
- ADD [-8, 7]: 2
- ADD [0, 0]: 2
- ADD [-4, 8]: 1
- ADD [-9, 7]: 1
- ADD [-2, -2]: 1
- ADD [-6, 4]: 1
- ADD [-3, 1]: 1
- ADD [-3, -1]: 1
- 4 edits; a child must have 1-3: 1
- ADD [-11, 8]: 1
- ADD [0, 4]: 1
- ADD [-5, 1]: 1
- ADD [-2, 0]: 1
- ADD [-1, 5]: 1
- REMOVE [-9, 8]: 1
- ADD [-1, 0]: 1
- ADD [-1, -1]: 1
- ADD [-2, 6]: 1
