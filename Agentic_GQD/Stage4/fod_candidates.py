# Created date: 2026-11-13 (America/Chicago)
"""N_FOD open-shell screen for the top score-v2 candidates. Runs on the server CPU.

    python Stage4/fod_candidates.py --top 80 --workers 16   # -> Stage4/results/fod_candidates.csv

Fused GQDs: the same reproducible start as Stage 3a evaluate_gqd (flat geometry + seeded
out-of-plane noise), GFN2-xTB optimisation, then `xtb --fod` on the optimised geometry.
Linked designs: `xtb --fod` on the stored optimised GQD geometry (Stage3d/data/geometries).
"""

import argparse
import json
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Stage3a.sensing import JITTER_A, _write_xyz, gqd_geometry, run_xtb  # noqa: E402
from Stage4.fod_screen import fod  # noqa: E402

OUT = ROOT / "Stage4" / "results"
GEOM = OUT / "candidate_geometries"


def hexagons_for(row, dataset):
    if isinstance(row.hexagons, str) and row.hexagons:
        return [tuple(h) for h in json.loads(row.hexagons)]
    return [tuple(h) for h in json.loads(dataset[row.id])]


def screen(row, dataset):
    name = row.id.replace("/", "__")
    try:
        if row.kind == "linked":
            xyz = ROOT / "Stage3d" / "data" / "geometries" / row.id.split("/", 1)[1] / "gqd" / "xtbopt.xyz"
        else:
            cells = hexagons_for(row, dataset)
            symbols, coords, _ = gqd_geometry(cells)
            rng = np.random.default_rng(abs(hash(tuple(sorted(cells)))) % 2**32)
            coords = coords + np.column_stack([np.zeros((len(coords), 2)), rng.normal(0, JITTER_A, len(coords))])
            res = run_xtb(symbols, coords, uhf=0, threads=1)
            xyz = GEOM / f"{name}.xyz"
            _write_xyz(xyz, symbols, res["coords"])
        return {"id": row.id} | fod(xyz)
    except Exception as error:  # report, do not stop the batch
        return {"id": row.id, "N_FOD": float("nan"), "error": repr(error)[:200]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=80)
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()
    GEOM.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(OUT / "rescored.csv")
    top = df[df.score_v2 > 0].sort_values("score_v2", ascending=False).head(args.top)
    dataset = pd.read_csv(ROOT / "Stage1" / "data" / "gqd_hex_dataset.csv", usecols=["Structure_Name", "hexagons"])
    dataset = dict(zip(dataset.Structure_Name, dataset.hexagons))
    with ThreadPoolExecutor(args.workers) as pool:
        rows = list(pool.map(lambda r: screen(r, dataset), top.itertuples(index=False)))
    out = top.merge(pd.DataFrame(rows), on="id", how="left")
    out.to_csv(OUT / "fod_candidates.csv", index=False)
    print(out[["id", "kind", "gap", "score_v2", "N_FOD"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
