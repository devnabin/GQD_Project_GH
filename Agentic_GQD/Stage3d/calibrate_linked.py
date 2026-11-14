# Created date: 2026-11-13 (America/Chicago)
"""L2 calibration: evaluate every design in designs.py that builds, with all five gases.

    nohup .venv/bin/python Stage3d/calibrate_linked.py --parallel 2 --workers 6 > Stage3d/results/calibration_run.log 2>&1 &

Saves after each design to results/calibration_linked.jsonl (resumable) and keeps all xTB geometries
in data/geometries/<design>/ (for a later DFT check).
"""

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from designs import DESIGNS  # noqa: E402
from linked import LinkError, build  # noqa: E402
from sensing_linked import evaluate_linked  # noqa: E402


def jsonable(v):
    if isinstance(v, dict):
        return {k: jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [jsonable(x) for x in v]
    return v.item() if isinstance(v, np.generic) else v


ap = argparse.ArgumentParser()
ap.add_argument("--parallel", type=int, default=2, help="designs at the same time")
ap.add_argument("--workers", type=int, default=6, help="xTB jobs per design")
args = ap.parse_args()
out_path = HERE / "results" / "calibration_linked.jsonl"
out_path.parent.mkdir(exist_ok=True)
done = {json.loads(x)["design"] for x in out_path.read_text().splitlines()} if out_path.exists() else set()
todo = []
for name, design in DESIGNS.items():
    try:
        build(design)
    except LinkError as error:
        print(f"skip {name}: {error}", flush=True)
        continue
    if name not in done:
        todo.append(name)
print(f"{len(todo)} designs to run, {len(done)} done", flush=True)


def one(name):
    start = time.time()
    res = evaluate_linked(DESIGNS[name], threads=1, workers=args.workers, keep_dir=HERE / "data" / "geometries" / name)
    res |= {"design": name, "structure": DESIGNS[name], "seconds": round(time.time() - start, 1)}
    with out_path.open("a") as handle:
        handle.write(json.dumps(jsonable(res)) + "\n")
    print(f"{name}: {res['formula']}, E_NO2 {res['E_NO2_eV']:+.2f} eV at {res['site_NO2']}, "
          f"chem {res['NO2_chemisorbed']}, score {res['sensing_score']:.3f}, converged {res['all_converged']}, "
          f"{res['seconds']:.0f} s", flush=True)


with ThreadPoolExecutor(max_workers=args.parallel) as pool:
    list(pool.map(one, todo))
print("all done", flush=True)
