# Stage 3 run `llm_s0` (llm mutator)

Goal: maximise the NO2 sensing score (charge to NO2 x reversibility x selectivity vs CO). Population 8, up to 10 xTB-scored children per generation, gap pre-filter 0.3-1.6 eV, seed 0.

| gen | proposed | valid | xTB-scored | best this gen | best so far | mean scored | time (min) |
|---|---|---|---|---|---|---|---|
| 1 | 27 | 9 | 9 | 0.337 | 0.337 | 0.230 | 3.1 |
| 2 | 26 | 8 | 8 | 0.297 | 0.337 | 0.198 | 4.2 |
| 3 | 32 | 13 | 10 | 0.309 | 0.337 | 0.117 | 4.8 |
| 4 | 33 | 9 | 8 | 0.304 | 0.337 | 0.223 | 4.1 |
| 5 | 30 | 7 | 7 | 0.305 | 0.337 | 0.178 | 3.8 |
| 6 | 39 | 9 | 5 | 0.249 | 0.337 | 0.171 | 4.0 |
| 7 | 33 | 8 | 7 | 0.337 | 0.337 | 0.226 | 3.7 |
| 8 | 28 | 9 | 9 | 0.333 | 0.337 | 0.199 | 5.4 |
| 9 | 32 | 9 | 7 | 0.340 | 0.340 | 0.274 | 5.2 |
| 10 | 20 | 11 | 10 | 0.340 | 0.340 | 0.289 | 5.6 |

## Best new GQDs

| id | parent | edit | hex | gap (xTB) | E_NO2 | NO2 | charge | vs CO | score | parent score |
|---|---|---|---|---|---|---|---|---|---|---|
| g10c007 | g01c022 | ADD [-5, 9]; ADD [-6, 10] | 37 | 0.30 | -0.50 | phys | 0.34 | +0.25 | 0.340 | 0.337 |
| g09c019 | g01c022 | ADD [-7, 10]; ADD [-3, 0]; ADD [-5, 9] | 38 | 0.33 | -0.49 | phys | 0.34 | +0.24 | 0.340 | 0.337 |
| g10c004 | g07c026 | ADD [-5, 9]; ADD [-7, 10] | 38 | 0.29 | -0.50 | phys | 0.34 | +0.25 | 0.339 | 0.337 |
| g07c026 | g01c022 | ADD [-6, 10] | 36 | 0.31 | -0.49 | phys | 0.34 | +0.24 | 0.337 | 0.337 |
| g01c022 | gqd_14650 | ADD [-3, 1]; ADD [-6, 9] | 35 | 0.31 | -0.49 | phys | 0.34 | +0.25 | 0.337 | 0.279 |
| g08c004 | g07c026 | ADD [-7, 10]; ADD [-3, 0] | 38 | 0.36 | -0.48 | phys | 0.33 | +0.23 | 0.333 | 0.337 |
| g10c010 | g08c004 | REMOVE [-7, 10]; ADD [-5, 9] | 38 | 0.35 | -0.49 | phys | 0.33 | +0.24 | 0.330 | 0.333 |
| g10c009 | g01c022 | ADD [-3, 0]; ADD [-6, 10] | 37 | 0.36 | -0.49 | phys | 0.33 | +0.24 | 0.329 | 0.337 |
| g08c020 | g01c022 | ADD [-8, 10]; ADD [-2, -1]; ADD [-3, 0] | 38 | 0.37 | -0.48 | phys | 0.33 | +0.23 | 0.328 | 0.337 |
| g09c007 | g08c020 | REMOVE [-8, 10]; REMOVE [-2, -1] | 36 | 0.37 | -0.48 | phys | 0.33 | +0.24 | 0.328 | 0.328 |

## Why children were rejected (before xTB)

- molecular graph: 124
- duplicate: 43
- 4 edits; a child must have 1-3: 10
- ADD [-3, 1]: 2
- ADD [-4, 6]: 2
- ADD [-2, 0]: 2
- ADD [-4, 0]: 2
- ADD [-9, 8]: 2
- has 1 hole(s) (an empty region enclosed by hexagons): 2
- ADD [-4, 5]: 2
- ADD [-4, 1]: 1
- ADD [-6, 8]: 1
- ADD [-5, 6]: 1
- ADD [-4, 3]: 1
- ADD [-3, 3]: 1
- ADD [-3, 6]: 1
- ring count: 1
- ADD [-8, 8]: 1
- ADD [-6, 3]: 1
- ADD [-2, 6]: 1
- REMOVE [-2, 1]: 1
- REMOVE [0, 0]: 1
- REMOVE [-6, 10]: 1
- ADD [-3, -2]: 1
- ADD [-6, 0]: 1
- ADD [-3, 0]: 1
- ADD [-6, 10]: 1
