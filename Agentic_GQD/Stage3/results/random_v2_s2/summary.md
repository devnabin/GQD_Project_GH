# Stage 3 run `random_v2_s2` (random mutator)

Goal: maximise the NO2 sensing score (charge to NO2 x reversibility x selectivity vs CO). Population 8, up to 10 xTB-scored children per generation, gap pre-filter 0.2-1.6 eV, seed 2.

| gen | proposed | valid | xTB-scored | best this gen | best so far | mean scored | time (min) |
|---|---|---|---|---|---|---|---|
| 1 | 30 | 27 | 10 | 0.296 | 0.322 | 0.191 | 3.5 |
| 2 | 30 | 25 | 10 | 0.349 | 0.349 | 0.170 | 6.6 |
| 3 | 30 | 26 | 10 | 0.300 | 0.349 | 0.144 | 6.2 |
| 4 | 30 | 27 | 10 | 0.301 | 0.349 | 0.177 | 6.2 |
| 5 | 30 | 26 | 10 | 0.354 | 0.354 | 0.172 | 6.7 |
| 6 | 30 | 24 | 10 | 0.247 | 0.354 | 0.082 | 8.9 |
| 7 | 30 | 23 | 10 | 0.283 | 0.354 | 0.157 | 7.2 |
| 8 | 30 | 27 | 10 | 0.321 | 0.354 | 0.164 | 8.0 |
| 9 | 30 | 24 | 10 | 0.280 | 0.354 | 0.141 | 8.2 |
| 10 | 30 | 22 | 10 | 0.311 | 0.354 | 0.169 | 8.1 |

## Best new GQDs

| id | parent | edit | hex | gap (xTB) | E_NO2 | NO2 | charge | vs CO | score | parent score |
|---|---|---|---|---|---|---|---|---|---|---|
| g05c010 | g03c005 | ADD [-10, 9]; REMOVE [-7, 7] | 34 | 0.26 | -0.52 | phys | 0.35 | +0.28 | 0.354 | 0.300 |
| g02c005 | g01c002 | REMOVE [-3, 6] | 35 | 0.43 | -0.47 | phys | 0.35 | +0.16 | 0.349 | 0.296 |
| g08c003 | g05c011 | ADD [-8, 10] | 38 | 0.34 | -0.44 | phys | 0.32 | +0.22 | 0.321 | 0.321 |
| g05c011 | g03c005 | ADD [-7, 9]; ADD [-3, 7] | 37 | 0.33 | -0.44 | phys | 0.32 | +0.22 | 0.321 | 0.300 |
| g10c003 | g04c002 | ADD [-5, 4]; REMOVE [-3, 6] | 38 | 0.56 | -0.46 | phys | 0.31 | +0.16 | 0.311 | 0.301 |
| g05c002 | gqd_18941 | ADD [-7, 3]; ADD [-6, 6] | 32 | 0.42 | -0.41 | phys | 0.30 | +0.18 | 0.304 | 0.322 |
| g04c002 | g01c002 | ADD [0, 1] | 37 | 0.70 | -0.43 | phys | 0.30 | +0.20 | 0.301 | 0.296 |
| g03c005 | gqd_14650 | ADD [-6, 9]; REMOVE [-7, 9] | 34 | 0.27 | -0.40 | phys | 0.30 | +0.16 | 0.300 | 0.279 |
| g02c010 | gqd_90531 | ADD [-9, 3]; ADD [-3, 2] | 37 | 0.63 | -0.41 | phys | 0.30 | +0.17 | 0.299 | 0.289 |
| g04c005 | g02c010 | ADD [-10, 9] | 38 | 0.65 | -0.41 | phys | 0.30 | +0.18 | 0.299 | 0.299 |

## Why children were rejected (before xTB)

- duplicate: 28
- molecular graph: 16
- has 1 hole(s) (an empty region enclosed by hexagons): 5
