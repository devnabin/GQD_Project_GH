# Created date: 2026-11-13 (America/Chicago)
"""Score-v2 support for the Stage 3 evolution loop (Stage3/evolve.py --score v2).

A child is evaluated with xTB for NO2, CO and H2O (NH3 filled with the calibration median; it was
never the deciding gas), its bare-GQD geometry gets an xTB N_FOD open-shell check, and it is scored
with score v2 (Stage4/score_v2.py). Open-shell children (N_FOD > fod_max) score 0. All optimised
geometries are kept, so the best children can go straight to DFT.
"""

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Stage3a.sensing import JITTER_A, _write_xyz, evaluate_gqd, gqd_geometry, run_xtb  # noqa: E402
from Stage4.fod_screen import fod  # noqa: E402
from Stage4.score_v2 import fill_interferents, score_v2  # noqa: E402

V2_ANALYTES = ["NO2", "CO", "H2O"]
CAL = ROOT / "Stage3a" / "data" / "calibration.csv"
FOD_CAL = ROOT / "Stage4" / "results" / "fod_calibration.csv"


def medians() -> dict:
    cal = pd.read_csv(CAL)
    return {k: float(cal[k].median()) for k in ["E_H2O_eV", "q_H2O_e", "E_NH3_eV", "q_NH3_e"]}


def apply_v2(res: dict, n_fod: float, fod_max: float) -> dict:
    """Add score-v2 fields to an evaluate_gqd result; sensing_score becomes the v2 score."""
    out = dict(res)
    out["score_stage3a"] = res.get("sensing_score")
    out |= score_v2(fill_interferents(res, medians()))
    out["N_FOD"] = n_fod
    out["open_shell"] = bool(n_fod > fod_max)
    out["sensing_score"] = 0.0 if out["open_shell"] else out["score_v2"]
    return out


def evaluate_v2(hexagons, threads, workers, keep_dir, fod_max) -> dict:
    res = evaluate_gqd(hexagons, threads=threads, workers=workers, analytes=V2_ANALYTES, keep_dir=keep_dir)
    n_fod = fod(Path(keep_dir) / "gqd" / "xtbopt.xyz")["N_FOD"]
    return apply_v2(res, n_fod, fod_max)


def bare_fod(hexagons, out_xyz: Path) -> float:
    """Optimise the bare GQD with the Stage 3a start (seeded noise) and return N_FOD."""
    cells = [tuple(h) for h in hexagons]
    symbols, coords, _ = gqd_geometry(cells)
    rng = np.random.default_rng(abs(hash(tuple(sorted(cells)))) % 2**32)
    coords = coords + np.column_stack([np.zeros((len(coords), 2)), rng.normal(0, JITTER_A, len(coords))])
    res = run_xtb(symbols, coords, uhf=0, threads=1)
    out_xyz.parent.mkdir(parents=True, exist_ok=True)
    _write_xyz(out_xyz, symbols, res["coords"])
    return fod(out_xyz)["N_FOD"]


def calibration_fod(hexagons_by_name: dict, workers: int = 16) -> dict:
    """N_FOD of the 50 calibration GQDs (the starting pool), cached in Stage4/results/fod_calibration.csv."""
    if FOD_CAL.exists():
        cached = pd.read_csv(FOD_CAL)
        return dict(zip(cached.name, cached.N_FOD))
    geom = FOD_CAL.parent / "calibration_geometries"
    names = sorted(hexagons_by_name)
    with ThreadPoolExecutor(workers) as pool:
        values = list(pool.map(lambda n: bare_fod(hexagons_by_name[n], geom / f"{n}.xyz"), names))
    pd.DataFrame({"name": names, "N_FOD": values}).to_csv(FOD_CAL, index=False)
    return dict(zip(names, values))
