# Stage 2d: rule-plain

- 80 requests, 0.9 min
- First-try pass rate: 56%
- Pass rate after retries: 82% (mean attempts 1.66)
- Distinct valid: 45; new vs 91k: 66; point-symmetric: 58%; with holes: 0

## Rejection reasons (all failed attempts)

| Reason | Count |
|---|---|
| open-shell (no Kekulé form) | 63 |
| hexagons are not all connected: | 2 |
| duplicate hexagons: | 2 |

## Pass rate by requested shape

| Shape | First try | Final |
|---|---|---|
| L-shaped | 5/10 | 9/10 |
| elongated (a ribbon about 3 hexagons wide) | 4/10 | 6/10 |
| irregular / asymmetric | 2/10 | 5/10 |
| rectangular | 6/10 | 10/10 |
| roughly round (compact, like a disc) | 8/10 | 8/10 |
| triangular | 7/10 | 9/10 |
| with armchair edges as far as possible | 5/10 | 9/10 |
| with zigzag edges as far as possible | 8/10 | 10/10 |
