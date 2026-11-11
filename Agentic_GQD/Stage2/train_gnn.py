# Created date: 2026-11-10 (America/Chicago)
"""Train ONE GNN ensemble member in its own process.

Why a separate process: PyTorch and LightGBM/XGBoost each bundle their own
OpenMP library on macOS; loading both in one Python process segfaults or hangs.
train.py writes the inputs to an .npz file and starts one of these per seed.

Input : --inputs  .npz with smiles, globals, residual, train_idx, val_idx
Output: --model   gnn_seed<k>.pt   (state dict)
        --preds   .npy             residual predictions for every structure
Usage : .venv/bin/python Stage2/train_gnn.py --inputs X.npz --seed 0 --model M.pt --preds P.npy --log L.log
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import torch
from rdkit import Chem

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gnn import mol_to_graph, predict_gnn, train_gnn  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--preds", required=True)
    parser.add_argument("--log", required=True)
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--threads", type=int, default=3)
    args = parser.parse_args()

    torch.set_num_threads(args.threads)
    data = np.load(args.inputs, allow_pickle=True)
    graphs = [mol_to_graph(Chem.MolFromSmiles(s)) for s in data["smiles"]]

    def log(message):
        with open(args.log, "a") as handle:
            handle.write(f"[{time.strftime('%H:%M:%S')}] {message}\n")

    model = train_gnn(graphs, data["globals"], data["residual"], data["train_idx"], data["val_idx"],
                      seed=args.seed, epochs=args.epochs, log=log)
    torch.save(model.state_dict(), args.model)
    np.save(args.preds, predict_gnn(model, graphs, data["globals"], np.arange(len(graphs))))


if __name__ == "__main__":
    main()
