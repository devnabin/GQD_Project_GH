# Stage 2d: basic-plain

- 80 requests, 1.2 min
- First-try pass rate: 34%
- Pass rate after retries: 52% (mean attempts 2.21)
- Distinct valid: 33; new vs 91k: 42; point-symmetric: 45%; with holes: 0

## Rejection reasons (all failed attempts)

| Reason | Count |
|---|---|
| open-shell (no Kekulé form) | 131 |
| duplicate hexagons: | 2 |
| RDKit cannot re-read SMILES | 1 |
| hexagons are not all connected: | 1 |

## Pass rate by requested shape

| Shape | First try | Final |
|---|---|---|
| L-shaped | 1/10 | 1/10 |
| elongated (a ribbon about 3 hexagons wide) | 6/10 | 7/10 |
| irregular / asymmetric | 0/10 | 0/10 |
| rectangular | 5/10 | 8/10 |
| roughly round (compact, like a disc) | 7/10 | 10/10 |
| triangular | 2/10 | 3/10 |
| with armchair edges as far as possible | 4/10 | 6/10 |
| with zigzag edges as far as possible | 2/10 | 7/10 |
