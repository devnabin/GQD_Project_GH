<!-- Created date: 2026-11-10 (America/Chicago) -->

# Stage 2: Fast xTB gap predictor

## What this stage does

xTB takes minutes per structure, but the evolution loop (Stage 3) has to score hundreds of children per generation. This stage trains a model that predicts the **GFN2-xTB HOMO–LUMO gap** of a GQD in milliseconds, along with an **uncertainty** (sigma). The loop uses the prediction to rank children and sends only the best or most uncertain ones to real xTB.

- **Input:** a SMILES string or a hexagon list (the format the LLM writes).
- **Output:** predicted gap (eV), sigma (eV), and the prediction of each sub-model.

## Final results (held-out test set, 1,468 structures never used in training or tuning)

| Model | MAE (eV) | RMSE (eV) | R² |
|---|---|---|---|
| Hückel only (linear fit) | 0.0421 | 0.0721 | 0.966 |
| LightGBM (5 folds) | 0.0308 | 0.0638 | 0.974 |
| XGBoost (5 folds) | 0.0307 | 0.0635 | 0.974 |
| **GNN (5 folds)** | **0.0216** | 0.0542 | 0.981 |
| **Ensemble (0.85 GNN + 0.15 XGB), used by `predictor.py`** | **0.0226** | 0.0549 | 0.981 |
| Ensemble, structures without holes (n = 1,344) | 0.0181 | 0.0441 | 0.988 |
| Ensemble, structures with holes (n = 124) | 0.0712 | 0.1208 | 0.863 |

For comparison, the old model in the parent project had MAE 0.386 eV and R² −0.47 on these structures.

**Uncertainty:** 96.7% of test structures fall inside ±1.96·sigma (the target is 95%). Mean sigma is 0.029 eV without holes and 0.114 eV with holes, so the model knows when it is unsure. The Spearman correlation between sigma and the actual error is 0.33.

**Extrapolation checks:**
- Gap tails (test gaps outside the training 5–95% range): LGBM MAE 0.049 vs Hückel 0.064.
- Large sizes (trained on ≤34 hexagons, tested on ≥35): LGBM MAE 0.033, nearly the same as in-range.

### Keep the GNN? Yes.

The GNN cuts the error by about 30% (0.031 → 0.022 eV), so it is kept, even though it has to run in a separate process (see below). The GNN alone (0.0216) is 0.001 eV better than the ensemble on test, which is within noise. The XGB part is kept because the disagreement between XGB and the GNN feeds the uncertainty model.

## How it works

1. **Hückel baseline.** The Hückel HOMO–LUMO gap (eigenvalues of the carbon adjacency matrix) alone correlates with the xTB gap at r = 0.984. A linear fit `gap = 2.5477·huckel + 0.0527` is the baseline.
2. **Residual learning.** Every ML model predicts only the *correction* (xTB − baseline), which is a much easier target.
3. **Physics features (49), `features.py`:**
   - Hückel spectrum: gap, HOMO/LUMO, neighbouring gaps, π energy, near-zero levels, orbital localisation (IPR), frontier-orbital weight on the edge.
   - Kekulé structure count, Clar number (aromatic sextets, via integer programming).
   - Edge hydrogens: solo / duo / trio / quarto.
   - Perimeter shape: fissure, bay, cove, fjord, lagoon.
   - Holes: count, size, inner hydrogens.
   - Size and shape: hexagon/carbon/hydrogen counts, internal-carbon fraction, radius of gyration, aspect ratio, extent, hexagons by neighbour count.
   - A 2,048-bit Morgan fingerprint was also tested. Alone it reaches only R² 0.36, so the physics features carry the signal.
4. **Models.**
   - LightGBM and XGBoost, each tuned with Optuna (100 trials).
   - A graph neural network (`gnn.py`, GIN-style, pure PyTorch). One node per carbon, with node features for edge position, ring membership, hole contact, and frontier-orbital coefficients. The 49 physics features are added as global inputs.
5. **5-fold cross-validation ensemble.** Each model type is trained 5 times on different folds of the 90% development set, and the folds are averaged at prediction time. The out-of-fold predictions are used to choose the ensemble weights and to train the uncertainty model, so neither ever sees its own training labels.
6. **Uncertainty.** A LightGBM "error model" predicts the expected absolute error from the features plus model disagreement. It is scaled (×1.54) so ±1.96·sigma covers 95% on out-of-fold data.

**Data:** the 14,674 xTB-labelled structures from `Stage1/data/gqd_hex_dataset.csv`. The split is stratified by gap, 80/10/10 train/validation/test (`data/split.csv`), and the test set was used only for the final report.

## Files

| File | What it does |
|---|---|
| `features.py` | `compute_features(mol, hexagons)`: the 49 physics features (~5 ms per molecule). |
| `build_features.py` | Computes features + Morgan bits for all labelled structures in parallel → `data/features_labelled.parquet`. |
| `gnn.py` | Molecule → graph conversion, the `GapGNN` model, training and prediction helpers. |
| `train_gnn.py` | Trains **one** GNN fold in its own process (called by `train.py`). |
| `train.py` | The full pipeline: split, Hückel baseline, Optuna tuning, 5-fold LGBM/XGB, 5 parallel GNNs, ensemble weights, uncertainty model, test report. |
| `gnn_predict.py` | GNN inference in its own process (called by `predictor.py`). |
| `predictor.py` | **`GapPredictor`**: the class the agent and evolution loop use. |
| `models/` | Trained models (162 MB): `lgbm_fold*.txt`, `xgb_fold*.json`, `gnn_fold*.pt`, `error_model.txt`, `huckel_linear.json`, `ensemble.json` (features, weights, scaling). |
| `results/` | `train.log`, `gnn.log`, `metrics.json`, `test_predictions.csv` (per-structure test predictions, sigma, has_hole), out-of-fold GNN predictions. |
| `data/` | `features_labelled.parquet`, `split.csv`, GNN input files. |

## How to use

```python
from Stage2.predictor import GapPredictor

predictor = GapPredictor()                       # loads all models once (~1 s)
table = predictor.predict(hexagons=[[[0, 0], [1, 0], ...], ...])
# or: predictor.predict(smiles=["...", ...])
table[["gap_pred_eV", "sigma_eV", "error"]]
```

- About **4.5 s for 200 structures** (most of that is starting the GNN process once per call), so pass a whole generation in one call rather than one structure at a time.
- Rows that can't be processed have NaN predictions and a reason in `error`, for example a bad hexagon list or **a size outside 20–40 hexagons**. Outside that range the model is meaningless: naphthalene was predicted at −651 eV before this guard was added.
- Checked: `predictor.py` reproduces the saved test-set ensemble to within 0.001 eV, and SMILES and hexagon inputs give identical results.

## How to retrain

```bash
cd Agentic_GQD
.venv/bin/python Stage2/build_features.py                       # ~2 min
.venv/bin/python Stage2/train.py --trials 100 --folds 5 --gnn-epochs 300   # ~80 min on CPU
```

The full run on 2026-11-10 took 78 min:
- LightGBM tuning: 54 min
- XGBoost tuning: 5 min
- 5-fold boosting: 3 min
- 5 GNNs in parallel: 15 min

## Known limitations

- **Holes.** Structures with holes (8.5% of the data) have about 4× larger errors. Either reject holes in the agent (a proposed 6th validation check) or always confirm them with xTB.
- **Training range.** 20–40 hexagons and xTB gaps of 0.00–2.03 eV. Targets near the edges (for example 2.0 eV) are extrapolation, so confirm them with xTB.
- **macOS OpenMP clash.** PyTorch and LightGBM/XGBoost can't share one Python process on macOS (segfault or hang). The GNN therefore always runs in a subprocess (`train_gnn.py`, `gnn_predict.py`).
- **CPU, not the Mac GPU.** For these small graphs, CPU was 12× faster per batch than MPS (25 ms vs 301 ms), so training uses the CPU.
