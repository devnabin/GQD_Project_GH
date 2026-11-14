# Created date: 2026-11-12 (America/Chicago)
"""DFT check of the xTB sensing numbers on the GPU (GPU4PySCF), for many GQDs.

    CUDA_VISIBLE_DEVICES=0 python Stage3a/dft_gpu.py BENCH_DIR [--df] [--summary-only]

BENCH_DIR comes from make_geometries.py: one folder per GQD with the xTB geometries of the
GQD and of every GQD+gas complex, plus refs/ with the isolated gases. At exactly those
geometries this computes wB97X-V/def2-SVP single points (same method as dft_check.py) and

    E_ads(DFT) = E(complex) - E(GQD) - E(gas)    (no counterpoise; SVP overbinds ~0.1 eV)

with the meta-Lowdin charge on the gas. Every finished SCF is appended to
BENCH_DIR/dft_results.jsonl, so a stopped run resumes where it left off. At the end it writes
BENCH_DIR/<gqd>/dft.csv (per complex, xTB next to DFT) and BENCH_DIR/summary.csv (per GQD:
the sensing descriptors and score from xTB and from DFT).
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from Stage3a.sensing import ANALYTES, BOND_A, GASES, HARTREE_EV, _read_xyz, sensing_numbers  # noqa: E402

XC, NLC, BASIS = "wb97x_v", "vv10", "def2-svp"
# Order of work, so the most useful answers come first (about 10-14 h for 12 GQDs on one A100):
#   1. GQD + NO2 + CO   -> ranking check of the sensing score
#   2. O2               -> air stability (xTB is known to be wrong for O2)
#   3. H2O, NH3         -> the remaining interferents
PHASES = [["NO2", "NO2_O", "CO"], ["O2"], ["H2O", "NH3"]]
GAS_TO_ANALYTE = {gas: analyte for analyte, gases in ANALYTES.items() for gas in gases}


def scf(symbols, coords, spin, density_fit):
    import cupy
    from gpu4pyscf import dft
    from pyscf import gto
    from pyscf.scf import hf as cpu_hf

    mol = gto.M(atom=[(s, tuple(c)) for s, c in zip(symbols, coords)], basis=BASIS, spin=spin, verbose=0)
    mf = (dft.UKS if spin else dft.RKS)(mol, xc=XC)
    mf.nlc, mf.conv_tol, mf.max_cycle = NLC, 1e-8, 200
    mf.grids.level, mf.nlcgrids.level = 3, 1
    if density_fit:
        mf = mf.density_fit()
    energy = mf.kernel()
    if not mf.converged:
        try:  # second-order SCF as a fallback
            mf = mf.newton()
            energy = mf.kernel()
        except Exception as error:
            print(f"    newton fallback failed: {error!r}", flush=True)
    dm = mf.make_rdm1()
    dm = cupy.asnumpy(dm) if isinstance(dm, cupy.ndarray) else np.asarray(dm)
    if dm.ndim == 3:
        dm = dm[0] + dm[1]
    _, charges = cpu_hf.mulliken_meta(mol, dm, verbose=0)
    del mf
    cupy.get_default_memory_pool().free_all_blocks()
    return float(energy) * HARTREE_EV, bool(np.isfinite(energy)), np.asarray(charges)


def tasks(bench, names):
    """(key, xyz path, spin, n_gqd) for every SCF: gas references, then PHASES over all GQDs."""
    out = [(f"refs/{gas}", bench / "refs" / gas / "xtbopt.xyz", GASES[gas][2], 0) for gas in GASES]
    n_atoms = {name: len(_read_xyz(bench / name / "gqd" / "xtbopt.xyz")[0]) for name in names}
    out += [(f"{name}/gqd", bench / name / "gqd" / "xtbopt.xyz", 0, n_atoms[name]) for name in names]
    for phase in PHASES:
        for name in names:
            for path in sorted((bench / name).glob("*_*/xtbopt.xyz")):
                gas = path.parent.name.rsplit("_", 1)[0]
                if gas in phase:
                    out.append((f"{name}/{path.parent.name}", path, GASES[gas][2], n_atoms[name]))
    return out


def summarise(bench, names, done):
    rows = []
    for name in names:
        xtb = json.loads((bench / name / "xtb.json").read_text())
        xtb_rows = {f"{r['orientation']}_{r['site']}": r for r in xtb["details"]}
        gqd = done.get(f"{name}/gqd")
        per_complex = []
        for cx, r in xtb_rows.items():
            gas = r["orientation"]
            res, ref = done.get(f"{name}/{cx}"), done.get(f"refs/{gas}")
            if not (gqd and res and ref):
                continue
            per_complex.append({
                "complex": cx, "analyte": GAS_TO_ANALYTE[gas], "site": r["site"], "d_min_A": r["d_min_A"],
                "E_ads_xTB_eV": r["E_ads_eV"], "E_ads_DFT_eV": res["energy_eV"] - gqd["energy_eV"] - ref["energy_eV"],
                "q_gas_xTB_e": r["q_gas_e"], "q_gas_DFT_e": res["q_gas_e"],
                "converged": res["converged"] and gqd["converged"] and ref["converged"]})
        if not per_complex:
            continue
        table = pd.DataFrame(per_complex)
        # use an analyte only when all its complexes (both sites, both NO2 orientations) are done
        expected = pd.Series([GAS_TO_ANALYTE[r["orientation"]] for r in xtb_rows.values()]).value_counts()
        complete = [a for a, n in table.analyte.value_counts().items() if n == expected[a]]
        table = table[table.analyte.isin(complete)]
        if "NO2" not in complete or not {"H2O", "NH3", "CO"} & set(complete):
            continue  # not enough for a sensing score yet
        table.to_csv(bench / name / "dft.csv", index=False)
        dft = {}
        for analyte, group in table.groupby("analyte"):
            best = group.loc[group.E_ads_DFT_eV.idxmin()]
            dft |= {f"E_{analyte}_eV": best.E_ads_DFT_eV, f"q_{analyte}_e": best.q_gas_DFT_e,
                    f"dmin_{analyte}_A": best.d_min_A}
        dft |= sensing_numbers(dft)
        row = {"name": name, "n_hex": xtb["n_hex"], "gap_xTB_eV": xtb["gqd_gap_eV"],
               "analytes_DFT": ",".join(sorted(complete)), "all_converged_DFT": bool(table.converged.all())}
        for key in ["E_NO2_eV", "q_NO2_e", "E_CO_eV", "E_H2O_eV", "E_NH3_eV", "E_O2_eV", "selectivity_margin_eV",
                    "charge_to_NO2_e", "reversibility", "sensing_score", "strongest_interferent"]:
            row[f"{key}_xTB"], row[f"{key}_DFT"] = xtb[key], dft.get(key, float("nan"))
        row["NO2_chemisorbed"] = bool(xtb["dmin_NO2_A"] < BOND_A)  # same geometry for both methods
        rows.append(row)
    summary = pd.DataFrame(rows)
    summary.to_csv(bench / "summary.csv", index=False)
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bench", type=Path)
    ap.add_argument("--df", action="store_true", help="density fitting (faster; checked against no-DF)")
    ap.add_argument("--summary-only", action="store_true")
    args = ap.parse_args()

    names = sorted(p.parent.name for p in args.bench.glob("*/xtb.json"))
    cache = args.bench / "dft_results.jsonl"
    done = {}
    if cache.exists():
        for line in cache.read_text().splitlines():
            rec = json.loads(line)
            done[rec["key"]] = rec

    todo = [t for t in tasks(args.bench, names) if t[0] not in done]
    print(f"{len(names)} GQDs, {len(done)} SCFs done, {len(todo)} to do, density fitting {args.df}", flush=True)
    for i, (key, path, spin, n_gqd) in enumerate([] if args.summary_only else todo, 1):
        symbols, coords = _read_xyz(path)
        start = time.time()
        try:
            energy, converged, charges = scf(symbols, coords, spin, args.df)
            error = ""
        except Exception as exc:  # one failed SCF should not stop the rest
            energy, converged, charges, error = float("nan"), False, np.full(len(symbols), np.nan), repr(exc)[:300]
        rec = {"key": key, "energy_eV": energy, "converged": converged, "spin": spin,
               "q_gas_e": float(charges[n_gqd:].sum()) if n_gqd else 0.0, "n_atoms": len(symbols),
               "seconds": round(time.time() - start, 1), "density_fit": args.df, "error": error}
        done[key] = rec
        with cache.open("a") as handle:
            handle.write(json.dumps(rec) + "\n")
        print(f"[{i}/{len(todo)}] {key}: {len(symbols)} atoms, {'UKS' if spin else 'RKS'}, "
              f"converged {converged}, {rec['seconds']:.0f} s {error}", flush=True)

    summary = summarise(args.bench, names, done)
    cols = ["name", "gap_xTB_eV", "E_NO2_eV_xTB", "E_NO2_eV_DFT", "q_NO2_e_xTB", "q_NO2_e_DFT", "E_O2_eV_DFT",
            "sensing_score_xTB", "sensing_score_DFT"]
    if len(summary):
        print(summary[cols].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
