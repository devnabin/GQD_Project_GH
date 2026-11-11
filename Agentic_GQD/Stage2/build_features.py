# Created date: 2026-11-10 (America/Chicago)
"""Compute features for every xTB-labelled GQD and save them for training.

Input : ../Stage1/data/gqd_hex_dataset.csv  (rows with xtb_gap_eV)
Output: data/features_labelled.parquet       one row per structure:
        Structure_Name, SMILES, hexagons, xtb_gap_eV, xtb_homo_eV, xtb_lumo_eV,
        n_hex, <physics features from features.py>, morgan_* (2048-bit, radius 2)

Usage (from Agentic_GQD/):  .venv/bin/python Stage2/build_features.py
"""

import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem
from rdkit.Chem import rdFingerprintGenerator

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from features import compute_features  # noqa: E402

SOURCE = HERE.parent / "Stage1" / "data" / "gqd_hex_dataset.csv"
OUT = HERE / "data" / "features_labelled.parquet"
MORGAN_BITS = 2048


def featurize(args):
    smiles, hexagons_json = args
    mol = Chem.MolFromSmiles(smiles)
    physics = compute_features(mol, json.loads(hexagons_json))
    generator = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=MORGAN_BITS)
    morgan = generator.GetFingerprintAsNumPy(mol).astype(np.uint8)
    return physics, morgan


def main():
    data = pd.read_csv(SOURCE)
    data = data[data["xtb_gap_eV"].notna() & (data["hex_status"] == "ok")].reset_index(drop=True)
    print(f"{len(data):,} labelled structures")

    start = time.time()
    with Pool() as pool:
        results = pool.map(featurize, zip(data["SMILES"], data["hexagons"]), chunksize=50)
    print(f"features computed in {time.time() - start:.0f}s")

    physics = pd.DataFrame([r[0] for r in results])
    morgan = pd.DataFrame(np.stack([r[1] for r in results]),
                          columns=[f"morgan_{i}" for i in range(MORGAN_BITS)])
    keep = ["Structure_Name", "SMILES", "hexagons", "n_hex", "xtb_gap_eV", "xtb_homo_eV", "xtb_lumo_eV", "xtb_source"]
    table = pd.concat([data[keep], physics, morgan], axis=1)

    OUT.parent.mkdir(exist_ok=True)
    table.to_parquet(OUT, index=False)
    print(f"saved {table.shape} -> {OUT}")


if __name__ == "__main__":
    main()
