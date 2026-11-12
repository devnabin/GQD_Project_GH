# Stage 2d: basic-fixes

- 80 requests, 1.0 min
- First-try pass rate: 36%
- Pass rate after retries: 90% (mean attempts 1.82)
- Distinct valid: 67; new vs 91k: 70; point-symmetric: 24%; with holes: 0

## Rejection reasons (all failed attempts)

| Reason | Count |
|---|---|
| open-shell (no Kekulé form) | 67 |
| RDKit cannot re-read SMILES | 4 |
| hexagons are not all connected: | 2 |
| hexagons must be a list of | 1 |

## Pass rate by requested shape

| Shape | First try | Final |
|---|---|---|
| L-shaped | 0/10 | 9/10 |
| elongated (a ribbon about 3 hexagons wide) | 7/10 | 8/10 |
| irregular / asymmetric | 1/10 | 10/10 |
| rectangular | 5/10 | 10/10 |
| roughly round (compact, like a disc) | 6/10 | 9/10 |
| triangular | 3/10 | 8/10 |
| with armchair edges as far as possible | 3/10 | 10/10 |
| with zigzag edges as far as possible | 4/10 | 8/10 |
