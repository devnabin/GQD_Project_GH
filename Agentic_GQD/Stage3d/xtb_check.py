# Created date: 2026-11-12 (America/Chicago)
"""Stage 3d L1: GFN2-xTB optimisation of a few built structures, to check the start geometries.

    .venv/bin/python Stage3d/xtb_check.py      # -> results/xtb_check.md and results/<name>.xyz
"""

import sys
from pathlib import Path

import numpy as np
from rdkit import Chem

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from linked import build, write_xyz  # noqa: E402
from Stage3a.sensing import XTB, run_xtb  # noqa: E402

BENZ = [[0, 0]]
TRI = {"units": {"A": BENZ, "B": BENZ, "C": BENZ}, "place": {"A": [0, 0], "B": [1, 0], "C": [0, 1]}}
CORONENE = [[0, 0], [1, 0], [0, 1], [1, -1], [-1, 1], [-1, 0], [0, -1]]
STRUCTURES = {
    "triangle_n1": (TRI | {"links": [["A", "B", 1], ["A", "C", 1], ["B", "C", 1]]}, (1, 1000)),
    "triangle_n2": (TRI | {"links": [["A", "B", 2], ["A", "C", 2], ["B", "C", 2]]}, (1, 1000)),
    "coronene_2benz_n2": ({"units": {"A": CORONENE, "B": BENZ, "C": BENZ}, "place": {"A": [0, 0], "B": [1, 0], "C": [0, 1]},
                           "links": [["A", "B", 2], ["A", "C", 2]]}, (40, 150)),
}


def geometry_report(mol, coords):
    pos = coords[: mol.GetNumAtoms()]
    dist = lambda a, b: float(np.linalg.norm(pos[a] - pos[b]))
    triples = [dist(b.GetBeginAtomIdx(), b.GetEndAtomIdx()) for b in mol.GetBonds()
               if b.GetBondType() == Chem.BondType.TRIPLE]
    angles = []
    for atom in mol.GetAtoms():
        if any(b.GetBondType() == Chem.BondType.TRIPLE for b in atom.GetBonds()):
            i, (j, k) = atom.GetIdx(), [n.GetIdx() for n in atom.GetNeighbors()]
            v1, v2 = pos[j] - pos[i], pos[k] - pos[i]
            angles.append(float(np.degrees(np.arccos(np.clip(np.dot(v1, v2) / np.linalg.norm(v1) / np.linalg.norm(v2), -1, 1)))))
    ring6 = [dist(b.GetBeginAtomIdx(), b.GetEndAtomIdx()) for b in mol.GetBonds()
             if b.IsInRingSize(6)]
    out_of_plane = float(np.ptp((pos - pos.mean(0)) @ np.linalg.svd(pos - pos.mean(0))[2][2]))
    return triples, angles, ring6, out_of_plane


def main():
    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    lines = ["# Stage 3d L1: GFN2-xTB check of built structures", "", f"xtb binary: `{XTB}`, 4 threads, `--opt --gfn 2`.", "",
             "| structure | formula | converged | gap (eV) | C≡C (Å) | angle at sp C (deg) | 6-ring C–C (Å) | out-of-plane span (Å) |",
             "|---|---|---|---|---|---|---|---|"]
    for name, (structure, size) in STRUCTURES.items():
        built = build(structure, size_range=size)
        start = geometry_report(built.mol, built.coords)
        res = run_xtb(built.symbols, built.coords, uhf=0, threads=4)
        write_xyz(out_dir / f"{name}.xyz", built.symbols, res["coords"])
        t, a, r6, oop = geometry_report(built.mol, res["coords"])
        print(f"{name}: {built.formula}, converged {res['converged']}, gap {res['gap_eV']:.3f} eV; "
              f"start C#C {min(start[0]):.3f}-{max(start[0]):.3f}; opt C#C {min(t):.3f}-{max(t):.3f}, "
              f"sp angles {min(a):.1f}-{max(a):.1f}, ring C-C {min(r6):.3f}-{max(r6):.3f}, out-of-plane {oop:.2f}", flush=True)
        lines.append(f"| {name} | {built.formula} | {res['converged']} | {res['gap_eV']:.3f} | {min(t):.3f}–{max(t):.3f} | "
                     f"{min(a):.1f}–{max(a):.1f} | {min(r6):.3f}–{max(r6):.3f} | {oop:.2f} |")
    (out_dir / "xtb_check.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
