# Stage 2d results: LLM writes hexagons

- Model: Azure deployment from `studio/.env`; 50 independent requests; up to 2 retries with the error fed back; 0.8 min.
- **First-try pass rate: 46%** (23/50)
- **Pass rate after retries: 64%** (32/50); mean attempts 1.98

## Rejection reasons (all failed attempts)

| Check | Count |
|---|---|
| molecular graph | 67 |

Most common messages:

- (66×) structure has no Kekulé form (open-shell / radical GQD)
- (1×) valid Kekulé structure, but RDKit cannot re-read its SMILES (RDKit kekulization limit)

## Valid designs

- Size accuracy: requested vs built hexagons, mean |difference| 0.2
- Hexagon count stated by LLM vs ring count: 100% equal (differs when the shape has holes)
- Unique among themselves: 28/32
- Already in the 91k dataset: 0/32
- With holes: 0/32
- Predicted gap (eV): min 0.01, median 0.40, max 1.58

| Shape asked | Valid / asked |
|---|---|
| L-shaped | 0/6 |
| elongated (a ribbon about 3 hexagons wide) | 6/7 |
| irregular / asymmetric | 3/6 |
| rectangular | 5/6 |
| roughly round (compact, like a disc) | 7/7 |
| triangular | 1/6 |
| with armchair edges as far as possible | 6/6 |
| with zigzag edges as far as possible | 4/6 |
