# Created date: 2026-11-10 (America/Chicago)
"""Predict the xTB HOMO-LUMO gap (eV) of GQDs, with an uncertainty.

    from Stage2.predictor import GapPredictor
    predictor = GapPredictor()
    table = predictor.predict(smiles=["c1ccc2ccccc2c1", ...])
    table = predictor.predict(hexagons=[[[0, 0], [1, 0], ...], ...])

Returns a pandas DataFrame, one row per input:
    gap_pred_eV    ensemble prediction of the xTB gap
    sigma_eV       1-sigma uncertainty (±1.96·sigma ≈ 95% interval)
    huckel_eV      Hückel-only baseline
    lgbm_eV, xgb_eV, gnn_eV   the three model types
    error          reason if the structure could not be processed (other columns NaN)

Trust the prediction less when sigma is large (e.g. structures with holes) or
the structure is far outside the training data (20-40 hexagons, gap 0-2.03 eV).
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import xgboost as xgb
from rdkit import Chem

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from features import compute_features  # noqa: E402
from Stage1.gqd_hex import HexError, hex_to_mol, mol_to_hex  # noqa: E402

MODELS = HERE / "models"
MIN_HEX, MAX_HEX = 20, 40  # size range of the training data; outside it the model is unreliable


class GapPredictor:
    def __init__(self):
        self.config = json.loads((MODELS / "ensemble.json").read_text())
        self.linear = json.loads((MODELS / "huckel_linear.json").read_text())
        folds = self.config["folds"]
        self.lgbm = [lgb.Booster(model_file=str(MODELS / f"lgbm_fold{k}.txt")) for k in range(folds)]
        self.xgb = []
        for k in range(folds):
            booster = xgb.Booster()
            booster.load_model(str(MODELS / f"xgb_fold{k}.json"))
            self.xgb.append(booster)
        self.error_model = lgb.Booster(model_file=str(MODELS / "error_model.txt"))

    # ------------------------------------------------------------------
    def predict(self, smiles=None, hexagons=None) -> pd.DataFrame:
        if (smiles is None) == (hexagons is None):
            raise ValueError("give exactly one of smiles= or hexagons=")
        items = smiles if smiles is not None else hexagons
        rows, valid = [], []
        for item in items:
            try:
                if smiles is not None:
                    mol = Chem.MolFromSmiles(item)
                    if mol is None:
                        raise HexError("RDKit could not parse the SMILES")
                    cells = mol_to_hex(mol)
                else:
                    mol, cells = hex_to_mol(item), item
                if not MIN_HEX <= len(cells) <= MAX_HEX:
                    raise HexError(f"{len(cells)} hexagons is outside the training range "
                                   f"{MIN_HEX}-{MAX_HEX}; the prediction would be meaningless")
                rows.append({"SMILES": Chem.MolToSmiles(mol), **compute_features(mol, cells), "error": ""})
                valid.append(True)
            except HexError as error:
                rows.append({"error": str(error)})
                valid.append(False)

        table = pd.DataFrame(rows)
        out = pd.DataFrame({"SMILES": table.get("SMILES"), "gap_pred_eV": np.nan, "sigma_eV": np.nan,
                            "huckel_eV": np.nan, "lgbm_eV": np.nan, "xgb_eV": np.nan, "gnn_eV": np.nan,
                            "error": table["error"]})
        ok = np.array(valid)
        if not ok.any():
            return out

        X = table.loc[ok, self.config["features"]].to_numpy(np.float32)
        baseline = self.linear["slope"] * table.loc[ok, "huckel_gap"].to_numpy() + self.linear["intercept"]
        preds = {
            "lgbm": np.mean([m.predict(X) for m in self.lgbm], axis=0),
            "xgb": np.mean([m.predict(xgb.DMatrix(X)) for m in self.xgb], axis=0),
            "gnn": self._gnn(table.loc[ok, "SMILES"].tolist(), X),
        }
        weights = self.config["weights"]
        gap = baseline + sum(weights[t] * preds[t] for t in weights)

        disagreement = np.column_stack([np.abs(preds["lgbm"] - preds["xgb"]), np.abs(preds["lgbm"] - preds["gnn"]),
                                        np.abs(preds["xgb"] - preds["gnn"])])
        expected_error = np.clip(self.error_model.predict(np.column_stack([X, disagreement])),
                                 self.config["error_floor"], None)

        out.loc[ok, "gap_pred_eV"] = gap
        out.loc[ok, "sigma_eV"] = self.config["uncertainty_scale"] * expected_error
        out.loc[ok, "huckel_eV"] = baseline
        for t in preds:
            out.loc[ok, f"{t}_eV"] = baseline + preds[t]
        return out

    # ------------------------------------------------------------------
    def _gnn(self, smiles: list[str], X: np.ndarray) -> np.ndarray:
        """Run the GNN folds in a separate process (OpenMP clash with LightGBM/XGBoost)."""
        mean = np.array(self.config["global_mean"], dtype=np.float32)
        std = np.array(self.config["global_std"], dtype=np.float32)
        globals_ = np.nan_to_num((X - mean) / std).astype(np.float32)
        with tempfile.TemporaryDirectory() as tmp:
            inputs, output = Path(tmp) / "in.npz", Path(tmp) / "out.npy"
            np.savez(inputs, smiles=np.array(smiles, dtype=object), globals=globals_)
            subprocess.run([sys.executable, str(HERE / "gnn_predict.py"), "--inputs", str(inputs),
                            "--out", str(output)], check=True, capture_output=True)
            return np.load(output)
