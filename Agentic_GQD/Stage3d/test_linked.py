# Created date: 2026-11-12 (America/Chicago)
"""Tests for Stage 3d L1 (linked carbon). Run: .venv/bin/python Stage3d/test_linked.py

Prints one line per test with the computed result; exits non-zero if any test fails.
"""

import sys
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import rdMolDescriptors

sys.path.insert(0, str(Path(__file__).resolve().parent))
from linked import LinkError, build  # noqa: E402

ANY = (1, 10_000)  # size limit off for small test molecules
failures = []


def check(name, ok, detail):
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")
    if not ok:
        failures.append(name)


def same_molecule(built, known_smiles):
    return built.smiles == Chem.MolToSmiles(Chem.MolFromSmiles(known_smiles))


def formula(smiles):
    return rdMolDescriptors.CalcMolFormula(Chem.MolFromSmiles(smiles))


BENZ = [[0, 0]]
CASES = {
    "diphenylacetylene": ({"units": {"A": BENZ, "B": BENZ}, "place": {"A": [0, 0], "B": [1, 0]},
                           "links": [["A", "B", 1]]}, "c1ccc(C#Cc2ccccc2)cc1"),
    "diphenylbutadiyne": ({"units": {"A": BENZ, "B": BENZ}, "place": {"A": [0, 0], "B": [1, 0]},
                           "links": [["A", "B", 2]]}, "c1ccc(C#CC#Cc2ccccc2)cc1"),
}
for name, (structure, known) in CASES.items():
    built = build(structure, size_range=ANY)
    check(name, same_molecule(built, known) and built.formula == formula(known),
          f"built {built.smiles} ({built.formula}); known {Chem.MolToSmiles(Chem.MolFromSmiles(known))} "
          f"({formula(known)})")

triangle = {"units": {"A": BENZ, "B": BENZ, "C": BENZ}, "place": {"A": [0, 0], "B": [1, 0], "C": [0, 1]}}
for n, expected in [(1, "C24H12"), (2, "C30H12")]:
    built = build(triangle | {"links": [["A", "B", n], ["A", "C", n], ["B", "C", n]]}, size_range=ANY)
    ring_sizes = sorted(len(r) for r in built.mol.GetRingInfo().AtomRings())
    check(f"benzene triangle, n={n}", built.formula == expected,
          f"{built.formula} (expected {expected}); rings {ring_sizes}; ring closure {built.info['ring_closures']}; "
          f"SMILES {built.smiles}")

hybrid = {"units": {"N": [[0, 0], [1, 0]], "B": BENZ}, "place": {"N": [0, 0], "B": [1, 0]}, "links": [["N", "B", 1]]}
built = build(hybrid, size_range=ANY)
check("naphthalene unit + benzene, n=1", built.formula == formula(built.smiles) and built.info["triple_bonds"] == 1,
      f"{built.smiles} ({built.formula}), {built.n_carbon} C, triple bonds {built.info['triple_bonds']}")

big = {"units": {"A": [[0, 0], [1, 0], [0, 1], [1, -1], [-1, 1], [-1, 0], [0, -1]], "B": BENZ, "C": BENZ},
       "place": {"A": [0, 0], "B": [1, 0], "C": [0, 1]}, "links": [["A", "B", 2], ["A", "C", 2]]}
built = build(big)
check("coronene unit + two benzenes (n=2), default size limit", 40 <= built.n_carbon <= 150,
      f"{built.formula}, {built.n_carbon} C, SMILES {built.smiles}")

INVALID = {
    "units not neighbours": {"units": {"A": BENZ, "B": BENZ}, "place": {"A": [0, 0], "B": [2, 0]},
                             "links": [["A", "B", 1]]},
    "bad link length": {"units": {"A": BENZ, "B": BENZ}, "place": {"A": [0, 0], "B": [1, 0]},
                        "links": [["A", "B", 3]]},
    "unit not linked": {"units": {"A": BENZ, "B": BENZ, "C": BENZ}, "place": {"A": [0, 0], "B": [1, 0], "C": [0, 1]},
                        "links": [["A", "B", 1]]},
    "two units one place": {"units": {"A": BENZ, "B": BENZ}, "place": {"A": [0, 0], "B": [0, 0]},
                            "links": [["A", "B", 1]]},
    "open-shell unit (phenalenyl)": {"units": {"A": [[0, 0], [1, 0], [0, 1]], "B": BENZ},
                                     "place": {"A": [0, 0], "B": [1, 0]}, "links": [["A", "B", 1]]},
    "mixed link lengths around a ring": triangle | {"links": [["A", "B", 1], ["A", "C", 1], ["B", "C", 2]]},
    "too small for the default size limit": CASES["diphenylacetylene"][0],
    # found by a search over small designs: the 4-ring row C sits above A and reaches over B
    "parts overlap (row unit reaches over a neighbour)": {
        "units": {"A": BENZ, "B": BENZ, "C": [[0, 0], [1, 0], [2, 0], [3, 0]]},
        "place": {"A": [0, 0], "B": [1, 0], "C": [0, 1]}, "links": [["A", "B", 1], ["A", "C", 1]]},
}
for name, structure in INVALID.items():
    try:
        built = build(structure)
        check(f"reject: {name}", False, f"was accepted ({built.formula})")
    except LinkError as error:
        check(f"reject: {name}", True, str(error)[:230])

print(f"\n{len(failures)} failure(s)" + (f": {failures}" if failures else ""))
sys.exit(1 if failures else 0)
