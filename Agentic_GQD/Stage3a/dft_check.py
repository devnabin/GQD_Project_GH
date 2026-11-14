# Created date: 2026-11-12 (America/Chicago)
"""Cross-check xTB adsorption energies with DFT single points (wB97X-V/def2-SVP).

    .venv/bin/python Stage3a/dft_check.py GEOM_DIR [--jobs 6]

GEOM_DIR is a keep_dir written by evaluate_gqd(..., keep_dir=GEOM_DIR): it holds
gqd/xtbopt.xyz and <gas>_<site>/xtbopt.xyz. For every complex this computes, at
the xTB geometries,

    E_ads(DFT) = E(complex) - E(GQD) - E(gas)        (no counterpoise; SVP overbinds ~0.1 eV)

and the meta-Lowdin charge on the gas. Each SCF runs in its own single-threaded
process (the macOS PySCF wheel has no OpenMP). Writes GEOM_DIR/dft_check.csv.
"""

import argparse
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from Stage3a.sensing import GASES, HARTREE_EV, _read_xyz, run_xtb  # noqa: E402

XC, NLC, BASIS = "wb97x_v", "vv10", "def2-svp"


def scf(symbols, coords, spin):
    from pyscf import dft, gto
    mol = gto.M(atom=[(s, tuple(c)) for s, c in zip(symbols, coords)], basis=BASIS, spin=spin, verbose=0)
    # no density fitting: PySCF's DF code crashes (SIGBUS) on macOS for GQD-sized molecules
    mf = dft.UKS(mol) if spin else dft.RKS(mol)
    mf.max_memory = 8000
    mf.xc, mf.nlc, mf.max_cycle, mf.conv_tol = XC, NLC, 200, 1e-8
    mf.grids.level, mf.nlcgrids.level = 3, 1
    energy = mf.kernel()
    if not mf.converged:
        mf = mf.newton()  # second-order SCF as a fallback
        energy = mf.kernel()
    dm = mf.make_rdm1()
    if dm.ndim == 3:
        dm = dm[0] + dm[1]
    _, charges = mf.mulliken_meta(mol, dm, verbose=0)
    return {"energy_eV": energy * HARTREE_EV, "converged": bool(mf.converged), "charges": np.asarray(charges)}


def job(task):
    name, symbols, coords, spin = task
    try:
        return name, scf(symbols, coords, spin)
    except Exception as error:  # one failed SCF should not stop the rest
        print(f"{name}: SCF failed ({error})", flush=True)
        return name, {"energy_eV": np.nan, "converged": False, "charges": np.full(len(symbols), np.nan)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("geom_dir", type=Path)
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--only", default="", help="comma-separated complex names, e.g. NO2_centre,O2_edge")
    args = ap.parse_args()

    gqd_symbols, gqd_coords = _read_xyz(args.geom_dir / "gqd" / "xtbopt.xyz")
    n_gqd = len(gqd_symbols)
    tasks = [("gqd", gqd_symbols, gqd_coords, 0)]
    complexes = sorted(p.parent.name for p in args.geom_dir.glob("*_*/xtbopt.xyz"))
    if args.only:
        complexes = [c for c in complexes if c in args.only.split(",")]
    gases_needed = set()
    for cx in complexes:
        gas = cx.rsplit("_", 1)[0]
        gases_needed.add(gas)
        symbols, coords = _read_xyz(args.geom_dir / cx / "xtbopt.xyz")
        tasks.append((cx, symbols, coords, GASES[gas][2]))
    for gas in sorted(gases_needed):  # isolated gas at its own xTB-optimised geometry
        symbols, coords, spin = GASES[gas]
        opt = run_xtb(symbols, np.array(coords, float), uhf=spin, threads=1)["coords"]
        tasks.append((f"ref_{gas}", symbols, opt, spin))

    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        results = dict(pool.map(job, tasks))

    rows = []
    for cx in complexes:
        gas = cx.rsplit("_", 1)[0]
        _, coords = _read_xyz(args.geom_dir / cx / "xtbopt.xyz")
        d_min = float(np.min(np.linalg.norm(coords[n_gqd:, None] - coords[None, :n_gqd], axis=2)))
        rows.append({"complex": cx, "d_min_A": round(d_min, 3),
                     "E_ads_DFT_eV": results[cx]["energy_eV"] - results["gqd"]["energy_eV"]
                     - results[f"ref_{gas}"]["energy_eV"],
                     "q_gas_DFT_e": float(results[cx]["charges"][n_gqd:].sum()),
                     "converged": results[cx]["converged"] and results["gqd"]["converged"]
                     and results[f"ref_{gas}"]["converged"]})
    table = pd.DataFrame(rows)
    table.to_csv(args.geom_dir / "dft_check.csv", index=False)
    print(table.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
