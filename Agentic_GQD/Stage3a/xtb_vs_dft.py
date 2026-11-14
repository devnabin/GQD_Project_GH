# Created date: 2026-11-12 (America/Chicago)
"""xTB single points on the same geometries used by dft_check.py, merged with its results.

    .venv/bin/python Stage3a/xtb_vs_dft.py GEOM_DIR [GEOM_DIR ...]

Writes GEOM_DIR/xtb_vs_dft.csv and prints a combined table.
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from Stage3a.sensing import GASES, HARTREE_EV, XTB, _read_xyz, _write_xyz, run_xtb  # noqa: E402


def xtb_sp(symbols, coords, uhf):
    with tempfile.TemporaryDirectory() as tmp:
        _write_xyz(Path(tmp) / "in.xyz", symbols, coords)
        out = subprocess.run([XTB, "in.xyz", "--gfn", "2", "--uhf", str(uhf)], cwd=tmp,
                             capture_output=True, text=True, errors="replace", env={"OMP_NUM_THREADS": "2", "PATH": ""}).stdout
        charges = np.loadtxt(Path(tmp) / "charges")
    return float(re.findall(r"TOTAL ENERGY\s+(-?\d+\.\d+)", out)[-1]) * HARTREE_EV, charges


tables = []
for geom_dir in map(Path, sys.argv[1:]):
    dft = pd.read_csv(geom_dir / "dft_check.csv")
    gs, gx = _read_xyz(geom_dir / "gqd" / "xtbopt.xyz")
    e_gqd, _ = xtb_sp(gs, gx, 0)
    rows = []
    for cx in dft.complex:
        gas = cx.rsplit("_", 1)[0]
        symbols, coords, uhf = GASES[gas]
        e_gas = run_xtb(symbols, np.array(coords, float), uhf=uhf, threads=1)["energy_eV"]
        s, x = _read_xyz(geom_dir / cx / "xtbopt.xyz")
        e_cx, q = xtb_sp(s, x, uhf)
        rows.append({"complex": cx, "E_ads_xTB_eV": e_cx - e_gqd - e_gas, "q_gas_xTB_e": q[len(gs):].sum()})
    t = dft.merge(pd.DataFrame(rows), on="complex")
    t.insert(0, "model", geom_dir.name)
    t.to_csv(geom_dir / "xtb_vs_dft.csv", index=False)
    tables.append(t)
print(pd.concat(tables)[["model", "complex", "d_min_A", "E_ads_xTB_eV", "E_ads_DFT_eV", "q_gas_xTB_e",
                         "q_gas_DFT_e", "converged"]].round(3).to_string(index=False))
