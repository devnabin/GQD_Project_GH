# Stage 2d: rule-fixes

- 80 requests, 0.8 min
- First-try pass rate: 57%
- Pass rate after retries: 99% (mean attempts 1.52)
- Distinct valid: 55; new vs 91k: 79; point-symmetric: 48%; with holes: 0

## Rejection reasons (all failed attempts)

| Reason | Count |
|---|---|
| open-shell (no Kekulé form) | 39 |
| hexagons must be a list of | 1 |
| ring count: 19 hexagons, need 20-40 | 1 |
| RDKit cannot re-read SMILES | 1 |
| duplicate hexagons: | 1 |

## Pass rate by requested shape

| Shape | First try | Final |
|---|---|---|
| L-shaped | 2/10 | 10/10 |
| elongated (a ribbon about 3 hexagons wide) | 7/10 | 10/10 |
| irregular / asymmetric | 4/10 | 10/10 |
| rectangular | 8/10 | 10/10 |
| roughly round (compact, like a disc) | 6/10 | 10/10 |
| triangular | 7/10 | 10/10 |
| with armchair edges as far as possible | 5/10 | 9/10 |
| with zigzag edges as far as possible | 7/10 | 10/10 |
