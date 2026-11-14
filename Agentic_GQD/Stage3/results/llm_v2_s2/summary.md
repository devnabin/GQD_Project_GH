# Stage 3 run `llm_v2_s2` (llm mutator)

Goal: maximise the NO2 sensing score (charge to NO2 x reversibility x selectivity vs CO). Population 8, up to 10 xTB-scored children per generation, gap pre-filter 0.2-1.6 eV, seed 2.

| gen | proposed | valid | xTB-scored | best this gen | best so far | mean scored | time (min) |
|---|---|---|---|---|---|---|---|
| 1 | 18 | 10 | 10 | 0.293 | 0.322 | 0.160 | 4.6 |
| 2 | 18 | 10 | 10 | 0.343 | 0.343 | 0.182 | 4.2 |
| 3 | 23 | 11 | 10 | 0.295 | 0.343 | 0.161 | 6.0 |
| 4 | 31 | 15 | 10 | 0.301 | 0.343 | 0.113 | 5.4 |
| 5 | 25 | 10 | 10 | 0.314 | 0.343 | 0.169 | 6.5 |
| 6 | 22 | 12 | 10 | 0.321 | 0.343 | 0.205 | 5.5 |
| 7 | 32 | 11 | 10 | 0.316 | 0.343 | 0.263 | 5.6 |
| 8 | 33 | 12 | 10 | 0.318 | 0.343 | 0.151 | 5.4 |
| 9 | 32 | 13 | 10 | 0.325 | 0.343 | 0.154 | 6.8 |
| 10 | 21 | 11 | 10 | 0.313 | 0.343 | 0.164 | 4.7 |

## Best new GQDs

| id | parent | edit | hex | gap (xTB) | E_NO2 | NO2 | charge | vs CO | score | parent score |
|---|---|---|---|---|---|---|---|---|---|---|
| g02c005 | gqd_23821 | REMOVE [-5, 2]; REMOVE [0, 0] | 34 | 0.39 | -0.46 | phys | 0.34 | +0.22 | 0.343 | 0.301 |
| g09c027 | g06c021 | ADD [-11, 6]; ADD [-4, 0]; ADD [-10, 7] | 40 | 0.30 | -0.44 | phys | 0.32 | +0.20 | 0.325 | 0.321 |
| g06c021 | g05c009 | ADD [-11, 7]; ADD [-4, -1] | 36 | 0.36 | -0.44 | phys | 0.32 | +0.19 | 0.321 | 0.314 |
| g08c030 | g07c009 | ADD [-11, 4]; ADD [-12, 5] | 35 | 0.39 | -0.44 | phys | 0.32 | +0.17 | 0.318 | 0.316 |
| g07c009 | g05c009 | REMOVE [-11, 5]; REMOVE [-3, -1] | 33 | 0.40 | -0.43 | phys | 0.32 | +0.17 | 0.316 | 0.314 |
| g07c030 | g05c009 | ADD [-11, 4]; ADD [-4, -1] | 37 | 0.40 | -0.43 | phys | 0.32 | +0.17 | 0.316 | 0.314 |
| g08c011 | g07c030 | REMOVE [-11, 4]; REMOVE [-12, 5] | 35 | 0.42 | -0.43 | phys | 0.31 | +0.17 | 0.315 | 0.316 |
| g05c009 | g02c011 | REMOVE [-10, 7]; REMOVE [-1, 0] | 34 | 0.42 | -0.43 | phys | 0.31 | +0.17 | 0.314 | 0.301 |
| g10c007 | g08c030 | REMOVE [-12, 5]; ADD [-11, 6] | 36 | 0.43 | -0.42 | phys | 0.31 | +0.17 | 0.313 | 0.318 |
| g05c005 | gqd_18941 | ADD [-5, 5]; ADD [-1, 1] | 33 | 0.27 | -0.47 | phys | 0.31 | +0.26 | 0.311 | 0.322 |

## Why children were rejected (before xTB)

- molecular graph: 73
- duplicate: 28
- has 1 hole(s) (an empty region enclosed by hexagons): 5
- ADD [-4, 1]: 4
- ADD [-3, 0]: 3
- ADD [-3, -1]: 3
- ADD [-4, 5]: 2
- ADD [-3, 1]: 2
- ADD [-5, 2]: 2
- ADD [-4, 2]: 2
- ADD [-8, 6]: 2
- ADD [-3, 6]: 2
- ADD [-4, -1]: 2
- ADD [-3, 5]: 1
- ADD [-4, 6]: 1
- ADD [0, 0]: 1
- ADD [-1, -2]: 1
- ADD [-1, 3]: 1
- ADD [0, 1]: 1
- ADD [-3, 2]: 1
- REMOVE [0, 0]: 1
- ADD [-5, 5]: 1
- ADD [-11, 6]: 1
