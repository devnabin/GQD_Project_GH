# Created date: 2026-11-10 (America/Chicago)
"""GNN part of the gap predictor, run in its own process (PyTorch only).

Called by predictor.py, because PyTorch and LightGBM/XGBoost cannot share one
process on macOS (their OpenMP libraries clash).

Input : --inputs .npz with `smiles` and `globals` (standardised physics features)
Output: --out    .npy with the fold-averaged GNN residual prediction per molecule
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
from rdkit import Chem

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gnn import GapGNN, mol_to_graph, predict_gnn  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    torch.set_num_threads(4)
    config = json.loads((HERE / "models" / "ensemble.json").read_text())
    data = np.load(args.inputs, allow_pickle=True)
    graphs = [mol_to_graph(Chem.MolFromSmiles(s)) for s in data["smiles"]]
    globals_ = data["globals"].astype(np.float32)
    idx = np.arange(len(graphs))

    preds = []
    for k in range(config["folds"]):
        model = GapGNN(globals_.shape[1])
        model.load_state_dict(torch.load(HERE / "models" / f"gnn_fold{k}.pt", weights_only=True))
        preds.append(predict_gnn(model, graphs, globals_, idx))
    np.save(args.out, np.mean(preds, axis=0))


if __name__ == "__main__":
    main()
