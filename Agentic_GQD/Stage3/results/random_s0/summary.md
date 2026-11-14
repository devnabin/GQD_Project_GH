# Stage 3 run `random_s0` (random mutator)

Goal: maximise the NO2 sensing score (charge to NO2 x reversibility x selectivity vs CO). Population 8, up to 10 xTB-scored children per generation, gap pre-filter 0.3-1.6 eV, seed 0.

| gen | proposed | valid | xTB-scored | best this gen | best so far | mean scored | time (min) |
|---|---|---|---|---|---|---|---|
| 1 | 30 | 21 | 10 | 0.287 | 0.322 | 0.176 | 2.8 |
| 2 | 30 | 18 | 10 | 0.331 | 0.331 | 0.168 | 4.9 |
| 3 | 30 | 19 | 10 | 0.320 | 0.331 | 0.188 | 6.0 |
| 4 | 30 | 14 | 10 | 0.329 | 0.331 | 0.210 | 5.5 |
| 5 | 30 | 17 | 10 | 0.329 | 0.331 | 0.195 | 6.2 |
| 6 | 30 | 15 | 10 | 0.327 | 0.331 | 0.182 | 5.6 |
| 7 | 30 | 13 | 10 | 0.330 | 0.331 | 0.201 | 6.2 |
| 8 | 30 | 14 | 10 | 0.326 | 0.331 | 0.187 | 6.2 |
| 9 | 30 | 15 | 10 | 0.329 | 0.331 | 0.218 | 6.4 |
| 10 | 30 | 16 | 10 | 0.316 | 0.331 | 0.178 | 6.3 |

## Best new GQDs

| id | parent | edit | hex | gap (xTB) | E_NO2 | NO2 | charge | vs CO | score | parent score |
|---|---|---|---|---|---|---|---|---|---|---|
| g02c004 | gqd_14650 | ADD [-10, 10]; ADD [-10, 9] | 35 | 0.36 | -0.49 | phys | 0.33 | +0.24 | 0.331 | 0.279 |
| g07c013 | g06c012 | ADD [2, 2] | 33 | 0.45 | -0.47 | phys | 0.33 | +0.22 | 0.330 | 0.327 |
| g09c022 | g05c002 | REMOVE [-1, -1] | 36 | 0.44 | -0.51 | phys | 0.33 | +0.24 | 0.329 | 0.329 |
| g04c020 | g02c004 | ADD [-5, 4] | 36 | 0.44 | -0.51 | phys | 0.33 | +0.24 | 0.329 | 0.331 |
| g05c002 | g04c020 | ADD [0, -1] | 37 | 0.42 | -0.48 | phys | 0.33 | +0.20 | 0.329 | 0.329 |
| g06c012 | g03c009 | ADD [-6, 4] | 32 | 0.44 | -0.47 | phys | 0.33 | +0.22 | 0.327 | 0.320 |
| g08c006 | g06c012 | REMOVE [-2, 4]; ADD [0, 5] | 32 | 0.47 | -0.48 | phys | 0.33 | +0.20 | 0.326 | 0.327 |
| g09c015 | g07c013 | ADD [-5, 7] | 34 | 0.42 | -0.45 | phys | 0.32 | +0.21 | 0.325 | 0.330 |
| g06c013 | g02c005 | REMOVE [-8, 4] | 35 | 0.42 | -0.44 | phys | 0.32 | +0.21 | 0.323 | 0.308 |
| g07c027 | g06c007 | ADD [1, 4]; REMOVE [-3, 4] | 32 | 0.52 | -0.45 | phys | 0.32 | +0.20 | 0.322 | 0.319 |

## Why children were rejected (before xTB)

- molecular graph: 97
- duplicate: 36
- has 1 hole(s) (an empty region enclosed by hexagons): 5
