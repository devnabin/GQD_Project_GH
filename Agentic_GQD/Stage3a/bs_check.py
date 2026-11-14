# Broken-symmetry check: is the closed-shell (RKS) reference of small-gap GQDs too high?
import json, sys, time
from pathlib import Path
import numpy as np, cupy
from pyscf import gto
from gpu4pyscf import dft

HARTREE_EV = 27.211386
bench = Path(sys.argv[1])
out = bench / "bs_check.jsonl"
for name in sys.argv[2:]:
    lines = (bench / name / "gqd" / "xtbopt.xyz").read_text().splitlines()[2:]
    atoms = [(l.split()[0], tuple(map(float, l.split()[1:4]))) for l in lines if l.strip()]
    mol = gto.M(atom=atoms, basis="def2-svp", spin=0, verbose=0)
    t = time.time()
    rks = dft.RKS(mol, xc="wb97x_v"); rks.nlc = "vv10"; rks.conv_tol = 1e-8; rks.max_cycle = 200
    rks.grids.level, rks.nlcgrids.level = 3, 1
    e_rks = rks.kernel()
    mo = cupy.asarray(rks.mo_coeff); nocc = mol.nelectron // 2
    gap = float((rks.mo_energy[nocc] - rks.mo_energy[nocc - 1])) * HARTREE_EV
    c, s = np.cos(np.pi / 4), np.sin(np.pi / 4)
    ca, cb = mo.copy(), mo.copy()
    ca[:, nocc - 1] = c * mo[:, nocc - 1] + s * mo[:, nocc]
    cb[:, nocc - 1] = c * mo[:, nocc - 1] - s * mo[:, nocc]
    dma = ca[:, :nocc] @ ca[:, :nocc].T; dmb = cb[:, :nocc] @ cb[:, :nocc].T
    uks = dft.UKS(mol, xc="wb97x_v"); uks.nlc = "vv10"; uks.conv_tol = 1e-8; uks.max_cycle = 300
    uks.grids.level, uks.nlcgrids.level = 3, 1
    e_uks = uks.kernel(dm0=cupy.stack([dma, dmb]))
    s2 = float(uks.spin_square()[0])
    rec = {"name": name, "E_RKS_eV": float(e_rks) * HARTREE_EV, "E_UKS_BS_eV": float(e_uks) * HARTREE_EV,
           "lowering_eV": (float(e_rks) - float(e_uks)) * HARTREE_EV, "S2": s2, "gap_RKS_eV": gap,
           "uks_converged": bool(uks.converged), "seconds": round(time.time() - t)}
    with out.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    print(rec, flush=True)
    del rks, uks; cupy.get_default_memory_pool().free_all_blocks()
