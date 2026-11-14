# Stage 3 run `random_v2_s3` (random mutator)

Goal: maximise the NO2 sensing score (charge to NO2 x reversibility x selectivity vs CO). Population 8, up to 10 xTB-scored children per generation, gap pre-filter 0.2-1.6 eV, seed 3.

| gen | proposed | valid | xTB-scored | best this gen | best so far | mean scored | time (min) |
|---|---|---|---|---|---|---|---|
| 1 | 30 | 27 | 10 | 0.326 | 0.326 | 0.124 | 4.1 |
| 2 | 30 | 22 | 10 | 0.225 | 0.326 | 0.106 | 4.7 |
| 3 | 30 | 23 | 10 | 0.341 | 0.341 | 0.167 | 6.2 |
| 4 | 30 | 24 | 10 | 0.324 | 0.341 | 0.198 | 5.4 |
| 5 | 30 | 24 | 10 | 0.245 | 0.341 | 0.065 | 8.2 |
| 6 | 30 | 25 | 10 | 0.320 | 0.341 | 0.175 | 6.6 |
| 7 | 30 | 23 | 10 | 0.304 | 0.341 | 0.168 | 5.6 |
| 8 | 30 | 21 | 10 | 0.316 | 0.341 | 0.179 | 7.7 |
| 9 | 30 | 24 | 10 | 0.336 | 0.341 | 0.184 | 7.2 |
| 10 | 30 | 23 | 10 | 0.293 | 0.341 | 0.171 | 4.9 |

## Best new GQDs

| id | parent | edit | hex | gap (xTB) | E_NO2 | NO2 | charge | vs CO | score | parent score |
|---|---|---|---|---|---|---|---|---|---|---|
| g03c012 | gqd_14650 | ADD [-4, 0] | 34 | 0.29 | -0.50 | phys | 0.34 | +0.26 | 0.341 | 0.279 |
| g09c012 | g06c010 | ADD [-8, 3]; ADD [-2, 3] | 38 | 0.34 | -0.51 | phys | 0.34 | +0.27 | 0.336 | 0.320 |
| g01c009 | gqd_18941 | REMOVE [-2, 4] | 29 | 0.50 | -0.46 | phys | 0.33 | +0.21 | 0.326 | 0.322 |
| g04c005 | g01c009 | ADD [1, -1]; ADD [-4, 9] | 31 | 0.52 | -0.46 | phys | 0.32 | +0.23 | 0.324 | 0.326 |
| g06c010 | g03c012 | ADD [-3, 7]; ADD [-9, 9] | 36 | 0.28 | -0.47 | phys | 0.32 | +0.26 | 0.320 | 0.341 |
| g08c013 | g06c010 | ADD [-9, 7]; ADD [0, -2] | 38 | 0.28 | -0.48 | phys | 0.32 | +0.22 | 0.316 | 0.320 |
| g07c007 | g04c005 | ADD [-2, 1] | 32 | 0.40 | -0.40 | phys | 0.30 | +0.18 | 0.304 | 0.324 |
| g07c012 | gqd_14650 | REMOVE [-5, 8] | 32 | 0.34 | -0.46 | phys | 0.30 | +0.21 | 0.303 | 0.279 |
| g04c007 | gqd_18941 | ADD [-6, 6] | 31 | 0.47 | -0.45 | phys | 0.30 | +0.20 | 0.299 | 0.322 |
| g08c011 | g07c012 | ADD [-3, 4]; ADD [-8, 6] | 34 | 0.28 | -0.39 | phys | 0.30 | +0.21 | 0.298 | 0.303 |

## Why children were rejected (before xTB)

- duplicate: 39
- molecular graph: 19
- has 1 hole(s) (an empty region enclosed by hexagons): 6
