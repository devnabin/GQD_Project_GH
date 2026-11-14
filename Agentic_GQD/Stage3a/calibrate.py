# Created date: 2026-11-12 (America/Chicago)
"""Run the NO2 sensing calculations on a gap-stratified sample of dataset GQDs.

    .venv/bin/python Stage3a/calibrate.py --n 50          # resumes if interrupted

Picks n GQDs from the 14,674 xTB-labelled structures (equal numbers per xTB-gap
bin over 0-2.03 eV), runs evaluate_gqd on each, and appends to
    data/calibration.csv          one row per GQD (descriptors)
    data/calibration_details.csv  one row per GQD x gas x site x orientation
"""

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from Stage3a.sensing import evaluate_gqd  # noqa: E402

DATA = HERE / "data"
LABELLED = HERE.parent / "Stage2" / "data" / "features_labelled.parquet"


def pick_sample(n, bins=10, seed=0):
    d = pd.read_parquet(LABELLED, columns=["Structure_Name", "SMILES", "hexagons", "n_hex",
                                           "xtb_gap_eV", "xtb_homo_eV", "xtb_lumo_eV"])
    d["gap_bin"] = pd.cut(d.xtb_gap_eV, bins=bins, labels=False)
    per_bin = int(np.ceil(n / bins))
    sample = pd.concat([g.sample(min(per_bin, len(g)), random_state=seed) for _, g in d.groupby("gap_bin")])
    return sample.sort_values("xtb_gap_eV").head(n).reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--threads", type=int, default=2)
    args = ap.parse_args()

    DATA.mkdir(exist_ok=True)
    out_csv, det_csv = DATA / "calibration.csv", DATA / "calibration_details.csv"
    sample = pick_sample(args.n)
    sample.drop(columns=["hexagons"]).to_csv(DATA / "calibration_sample.csv", index=False)
    done = set(pd.read_csv(out_csv).Structure_Name) if out_csv.exists() else set()
    print(f"{len(sample)} GQDs, {len(done)} already done", flush=True)

    for i, row in sample.iterrows():
        if row.Structure_Name in done:
            continue
        t0 = time.time()
        try:
            res = evaluate_gqd(json.loads(row.hexagons), threads=args.threads, workers=args.workers)
        except Exception:  # keep going; record the failure
            print(f"[{i + 1}/{len(sample)}] {row.Structure_Name} FAILED\n{traceback.format_exc()}", flush=True)
            continue
        details = pd.DataFrame(res.pop("details"))
        details.insert(0, "Structure_Name", row.Structure_Name)
        record = {"Structure_Name": row.Structure_Name, "SMILES": row.SMILES,
                  "dataset_gap_eV": row.xtb_gap_eV, "dataset_homo_eV": row.xtb_homo_eV,
                  "dataset_lumo_eV": row.xtb_lumo_eV, **res, "seconds": round(time.time() - t0, 1)}
        pd.DataFrame([record]).to_csv(out_csv, mode="a", header=not out_csv.exists(), index=False)
        details.to_csv(det_csv, mode="a", header=not det_csv.exists(), index=False)
        print(f"[{i + 1}/{len(sample)}] {row.Structure_Name} n_hex={row.n_hex} gap={row.xtb_gap_eV:.2f} "
              f"E_NO2={res['E_NO2_eV']:.2f} q={res['charge_to_NO2_e']:.2f} E_O2={res['E_O2_eV']:.2f} "
              f"({record['seconds']:.0f} s)", flush=True)


if __name__ == "__main__":
    main()
