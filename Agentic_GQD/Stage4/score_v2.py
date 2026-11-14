# Created date: 2026-11-13 (America/Chicago)
"""Score v2: the NO2 sensing score corrected with the GPU DFT benchmark (Stage3a/data/dft_benchmark).

What the benchmark showed (Stage3a/results/dft_benchmark.md):
  - xTB E_NO2 ranks like DFT (Spearman 0.74), but bonded (chemisorbed) NO2 is overbound in xTB;
  - the charge on physisorbed NO2 is an xTB artefact (DFT ~0.01 e); on bonded NO2 xTB and DFT agree.
So score v2 (a) shifts bonded-NO2 energies by the benchmark's mean xTB->DFT offset, (b) keeps the xTB
charge only for bonded NO2 and sets physisorbed charge to 0, and (c) scores the resulting molecule
with the Stage 3c sensor twin (20 ppb NO2, 50% RH, recovery <= 5 min). An open-shell (N_FOD) filter
is applied separately once it is calibrated.

    python Stage4/score_v2.py          # prints the fitted corrections
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Stage3c.twin import twin  # noqa: E402

BENCH = ROOT / "Stage3a" / "data" / "dft_benchmark"
BOND_A = 1.9
# Interferent defaults for records that only have NO2 + CO (evolution-loop children):
# medians of the 50 Stage 3a calibration GQDs (filled in by fill_interferents).
FILL = ["H2O", "NH3"]


def benchmark_offsets() -> dict:
    """Mean DFT - xTB adsorption energy of NO2 complexes, bonded and physisorbed, from all dft.csv."""
    rows = pd.concat([pd.read_csv(p) for p in sorted(BENCH.glob("*/dft.csv"))], ignore_index=True)
    no2 = rows[rows.analyte == "NO2"].copy()
    no2["bonded"] = no2.d_min_A < BOND_A
    diff = no2.E_ads_DFT_eV - no2.E_ads_xTB_eV
    return {"bonded": float(diff[no2.bonded].mean()), "n_bonded": int(no2.bonded.sum()),
            "physisorbed": float(diff[~no2.bonded].mean()), "n_physisorbed": int((~no2.bonded).sum()),
            "q_dft_bonded": float(no2.q_gas_DFT_e[no2.bonded].mean()),
            "q_dft_phys": float(no2.q_gas_DFT_e[~no2.bonded].mean())}


OFFSETS = benchmark_offsets() if BENCH.exists() else None


def fill_interferents(record: dict, defaults: dict) -> dict:
    out = dict(record)
    for gas in FILL:
        for key in (f"E_{gas}_eV", f"q_{gas}_e"):
            if key not in out or out[key] is None or (isinstance(out[key], float) and np.isnan(out[key])):
                out[key] = defaults[key]
                out["interferents_filled"] = True
    return out


def corrected(record: dict) -> dict:
    """xTB descriptors -> DFT-corrected descriptors (NO2 only; other gases unchanged)."""
    out = dict(record)
    bonded = record["dmin_NO2_A"] < BOND_A
    if bonded:
        out["E_NO2_eV"] = record["E_NO2_eV"] + OFFSETS["bonded"]
    else:
        out["q_NO2_e"] = 0.0  # DFT: no charge on physisorbed NO2
    out["NO2_bonded"] = bonded
    return out


def score_v2(record: dict) -> dict:
    res = twin(corrected(record))
    return {"score_v2": res["twin_score"], "v2_response_e": res["response_20ppb_RH50_e"],
            "v2_recovery_s": res["recovery_s"], "v2_meets_spec": res["meets_recovery_spec"],
            "v2_humidity_equiv_ppb": res["humidity_equiv_ppb"]}


if __name__ == "__main__":
    print(OFFSETS)
