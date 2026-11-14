# Stage 3 run `random_v2_s1` (random mutator)

Goal: maximise the NO2 sensing score (charge to NO2 x reversibility x selectivity vs CO). Population 8, up to 10 xTB-scored children per generation, gap pre-filter 0.2-1.6 eV, seed 1.

| gen | proposed | valid | xTB-scored | best this gen | best so far | mean scored | time (min) |
|---|---|---|---|---|---|---|---|
| 1 | 30 | 27 | 10 | 0.282 | 0.322 | 0.178 | 5.2 |
| 2 | 30 | 28 | 10 | 0.311 | 0.322 | 0.155 | 6.3 |
| 3 | 30 | 26 | 10 | 0.311 | 0.322 | 0.179 | 6.4 |
| 4 | 30 | 22 | 10 | 0.333 | 0.333 | 0.262 | 6.7 |
| 5 | 30 | 26 | 10 | 0.282 | 0.333 | 0.136 | 5.9 |
| 6 | 30 | 21 | 10 | 0.353 | 0.353 | 0.189 | 9.1 |
| 7 | 30 | 26 | 10 | 0.332 | 0.353 | 0.221 | 6.0 |
| 8 | 30 | 27 | 10 | 0.316 | 0.353 | 0.134 | 6.6 |
| 9 | 30 | 26 | 10 | 0.356 | 0.356 | 0.171 | 6.5 |
| 10 | 30 | 23 | 10 | 0.268 | 0.356 | 0.158 | 5.6 |

## Best new GQDs

| id | parent | edit | hex | gap (xTB) | E_NO2 | NO2 | charge | vs CO | score | parent score |
|---|---|---|---|---|---|---|---|---|---|---|
| g09c010 | g06c006 | ADD [0, -2]; ADD [-10, 8] | 39 | 0.32 | -0.52 | phys | 0.36 | +0.26 | 0.356 | 0.353 |
| g06c006 | g03c005 | ADD [-7, 6]; ADD [-3, 5] | 36 | 0.34 | -0.51 | phys | 0.35 | +0.26 | 0.353 | 0.298 |
| g04c010 | gqd_23821 | ADD [-1, -3]; ADD [0, -3] | 38 | 0.53 | -0.46 | phys | 0.33 | +0.23 | 0.333 | 0.301 |
| g07c003 | g03c003 | ADD [0, -2] | 33 | 0.38 | -0.47 | phys | 0.33 | +0.22 | 0.332 | 0.311 |
| g08c008 | g02c004 | REMOVE [-1, 3]; ADD [-5, 5] | 29 | 0.24 | -0.48 | phys | 0.32 | +0.19 | 0.316 | 0.311 |
| g06c010 | g02c004 | ADD [-6, 7] | 30 | 0.59 | -0.43 | phys | 0.31 | +0.19 | 0.312 | 0.311 |
| g02c004 | gqd_18941 | REMOVE [-1, 2] | 29 | 0.60 | -0.43 | phys | 0.31 | +0.19 | 0.311 | 0.322 |
| g03c003 | gqd_14650 | REMOVE [-5, 6] | 32 | 0.41 | -0.44 | phys | 0.31 | +0.17 | 0.311 | 0.279 |
| g04c002 | g03c005 | ADD [-6, 2] | 35 | 0.61 | -0.46 | phys | 0.30 | +0.20 | 0.301 | 0.298 |
| g06c012 | g02c006 | REMOVE [-4, -1]; ADD [-6, 6] | 39 | 0.71 | -0.42 | phys | 0.30 | +0.16 | 0.298 | 0.294 |

## Why children were rejected (before xTB)

- duplicate: 27
- molecular graph: 14
- has 1 hole(s) (an empty region enclosed by hexagons): 6
- ring count: 1
