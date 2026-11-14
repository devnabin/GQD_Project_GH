# Created date: 2026-11-12 (America/Chicago)
"""L2 consistency test: a one-unit design with no links is a plain GQD, so evaluate_linked must
reproduce the stored Stage 3a calibration numbers (within xTB noise; the start-geometry noise differs).

    .venv/bin/python Stage3d/consistency_test.py [--n 2] [--workers 4]
"""

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
from sensing_linked import evaluate_linked  # noqa: E402
import numpy as np  # noqa: E402
from Stage3a.sensing import JITTER_A, check_hexagons, gqd_geometry, sensing_numbers  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=2)
ap.add_argument("--workers", type=int, default=4)
ap.add_argument("--same-start", action="store_true", help="use the exact Stage 3a start geometry (its jitter seed)")
args = ap.parse_args()

cal = pd.read_csv(ROOT / "Stage3a" / "data" / "calibration.csv")
cal = cal[cal.all_converged & cal.n_hex.between(20, 25)].sort_values("n_hex")
phys = cal[cal.dmin_NO2_A >= 1.9].head(args.n - args.n // 2)   # one physisorbing ...
chem = cal[cal.dmin_NO2_A < 1.9].head(args.n // 2)             # ... and one chemisorbing GQD
picked = pd.concat([phys, chem])
hexes = pd.read_csv(ROOT / "Stage1" / "data" / "gqd_hex_dataset.csv", usecols=["Structure_Name", "hexagons"])
hexes = hexes.set_index("Structure_Name").hexagons

rows = []
for rec in picked.to_dict("records"):
    cells = json.loads(hexes[rec["Structure_Name"]])
    design = {"units": {"A": cells}, "place": {"A": [0, 0]}, "links": []}
    start = time.time()
    start_coords = None
    if args.same_start:  # Stage 3a's own start: same lattice, jitter seeded by hash of the hexagon list
        hx = [tuple(h) for h in check_hexagons(cells)]
        _, start_coords, _ = gqd_geometry(hx)
        rng = np.random.default_rng(abs(hash(tuple(sorted(hx)))) % 2**32)
        start_coords = start_coords + np.column_stack([np.zeros((len(start_coords), 2)),
                                                       rng.normal(0, JITTER_A, len(start_coords))])
    new = evaluate_linked(design, workers=args.workers, threads=1, extra_sites=False, start_coords=start_coords)
    old_score = sensing_numbers(rec)["sensing_score"]
    row = {"name": rec["Structure_Name"], "n_hex": rec["n_hex"], "seconds": round(time.time() - start),
           "sites": new["sites"], "converged": new["all_converged"]}
    for key in ["gqd_gap_eV", "E_NO2_eV", "q_NO2_e", "dmin_NO2_A", "E_CO_eV", "E_H2O_eV", "E_NH3_eV", "E_O2_eV"]:
        row[f"{key}_stage3a"], row[f"{key}_linked"] = rec[key], new[key]
        row[f"{key}_diff"] = new[key] - rec[key]
    row |= {"site_NO2_stage3a": rec["site_NO2"], "site_NO2_linked": new["site_NO2"],
            "score_stage3a": old_score, "score_linked": new["sensing_score"],
            "score_diff": new["sensing_score"] - old_score}
    rows.append(row)
    print(f"{row['name']} ({row['n_hex']} hex, {row['seconds']} s, converged {row['converged']}):")
    for key in ["gqd_gap_eV", "E_NO2_eV", "q_NO2_e", "dmin_NO2_A", "E_CO_eV", "E_H2O_eV", "E_NH3_eV", "E_O2_eV"]:
        print(f"  {key:12s} stage3a {row[key + '_stage3a']:+.4f}  linked {row[key + '_linked']:+.4f}  "
              f"diff {row[key + '_diff']:+.4f}")
    print(f"  NO2 site     stage3a {row['site_NO2_stage3a']}  linked {row['site_NO2_linked']}")
    print(f"  score        stage3a {old_score:.4f}  linked {new['sensing_score']:.4f}  diff {row['score_diff']:+.4f}",
          flush=True)
(HERE / "results").mkdir(exist_ok=True)
pd.DataFrame(rows).to_csv(HERE / "results" / ("consistency_test_same_start.csv" if args.same_start else "consistency_test.csv"), index=False)
