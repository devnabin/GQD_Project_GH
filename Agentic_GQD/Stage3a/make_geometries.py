# Created date: 2026-11-12 (America/Chicago)
"""xTB geometries (and xTB numbers) for the DFT benchmark.

    .venv/bin/python Stage3a/make_geometries.py OUT_DIR --calibration gqd_18941,gqd_23821 \
        --children llm_s0:g10c004,random_s0:g02c004 [--parallel 3]

For each GQD this runs the full Stage 3a evaluation (all gases, both sites) and keeps every
optimised geometry: OUT_DIR/<name>/gqd/xtbopt.xyz and OUT_DIR/<name>/<gas>_<site>/xtbopt.xyz,
plus OUT_DIR/<name>/xtb.json (descriptors and per-complex xTB numbers). The isolated gases go
to OUT_DIR/refs/<gas>/xtbopt.xyz with their energies in OUT_DIR/refs/energies.json.
dft_gpu.py then runs DFT on exactly these geometries.
"""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from Stage3a.sensing import ANALYTES, GASES, evaluate_gqd, run_xtb  # noqa: E402


def to_jsonable(value):
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--calibration", default="", help="Stage 3a calibration GQD names, comma-separated")
    ap.add_argument("--children", default="", help="run:child_id pairs from Stage3/results, comma-separated")
    ap.add_argument("--parallel", type=int, default=3)
    args = ap.parse_args()

    structures = {}
    if args.calibration:
        hexes = pd.read_csv(ROOT / "Stage1" / "data" / "gqd_hex_dataset.csv", usecols=["Structure_Name", "hexagons"])
        hexes = hexes.set_index("Structure_Name").hexagons
        for name in args.calibration.split(","):
            structures[name] = json.loads(hexes[name])
    for item in filter(None, args.children.split(",")):
        run, child = item.split(":")
        for line in (ROOT / "Stage3" / "results" / run / "children.jsonl").read_text().splitlines():
            rec = json.loads(line)
            if rec["child_id"] == child:
                structures[f"{run}_{child}"] = rec["child_hexagons"]
                break
        else:
            sys.exit(f"{child} not found in {run}")

    refs = args.out_dir / "refs"
    energies = {}
    for gas, (symbols, coords, uhf) in GASES.items():
        energies[gas] = run_xtb(symbols, np.array(coords, float), uhf=uhf, threads=1,
                                keep_dir=refs / gas)["energy_eV"]
    (refs / "energies.json").write_text(json.dumps(energies, indent=1))

    def one(item):
        name, cells = item
        out = args.out_dir / name
        if (out / "xtb.json").exists():
            return name, "already done"
        res = evaluate_gqd(cells, threads=1, workers=6, keep_dir=out, analytes=list(ANALYTES))
        res["hexagons"] = cells
        (out / "xtb.json").write_text(json.dumps(to_jsonable(res), indent=1))
        return name, f"xTB score {res['sensing_score']:.3f}, E_NO2 {res['E_NO2_eV']:+.2f} eV"

    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        for name, text in pool.map(one, structures.items()):
            print(f"{name}: {text}", flush=True)


if __name__ == "__main__":
    main()
