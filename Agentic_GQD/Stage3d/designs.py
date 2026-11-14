# Created date: 2026-11-12 (America/Chicago)
"""Hand-made linked-carbon designs for the L2 calibration set. Run to list which ones build:

    .venv/bin/python Stage3d/designs.py
"""

BENZ = [[0, 0]]
NAPH = [[0, 0], [1, 0]]
PYRENE = [[0, 0], [1, 0], [0, 1], [1, 1]]
CORONENE = [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1], [1, -1], [-1, 1]]
OVALENE = [[0, -1], [1, -1], [2, -1], [-1, 0], [0, 0], [1, 0], [2, 0], [-1, 1], [0, 1], [1, 1]]
CIRCUMCORONENE = [[q, r] for q in range(-2, 3) for r in range(-2, 3) if abs(q + r) <= 2]
NEIGH = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]


def lattice(places, unit, n, units=None):
    """Units on the given coarse places, with a link between every pair of neighbouring places."""
    names = {tuple(p): f"U{i}" for i, p in enumerate(places)}
    links = [[names[p], names[(p[0] + d[0], p[1] + d[1])], n] for p in names for d in NEIGH[::2]
             if (p[0] + d[0], p[1] + d[1]) in names]
    return {"units": {name: (units or {}).get(name, unit) for name in names.values()},
            "place": {name: list(p) for p, name in names.items()}, "links": links}


def star(centre_unit, arms, n, arm_unit=BENZ):
    """A central unit with benzene (or other) arms on `arms` of its six sides; no arm-arm links."""
    design = {"units": {"X": centre_unit}, "place": {"X": [0, 0]}, "links": []}
    for i, d in enumerate(NEIGH[:arms] if isinstance(arms, int) else arms):
        design["units"][f"A{i}"] = arm_unit
        design["place"][f"A{i}"] = list(d)
        design["links"].append(["X", f"A{i}", n])
    return design


TRI6 = [(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (0, 2)]
HEX7 = [(0, 0)] + NEIGH
RING6 = NEIGH
ROW = lambda k: [(i, 0) for i in range(k)]  # noqa: E731
RHOMB = lambda k: [(i, j) for i in range(k) for j in range(k)]  # noqa: E731

DESIGNS = {
    # graphyne (n=1) and graphdiyne (n=2) flakes: benzene units only
    "gy_tri6": lattice(TRI6, BENZ, 1),
    "gdy_tri6": lattice(TRI6, BENZ, 2),
    "gy_hex7": lattice(HEX7, BENZ, 1),
    "gdy_hex7": lattice(HEX7, BENZ, 2),
    "gy_ring6": lattice(RING6, BENZ, 1),
    "gdy_ring6": lattice(RING6, BENZ, 2),
    "gy_rhomb9": lattice(RHOMB(3), BENZ, 1),
    "gdy_rhomb4": lattice(RHOMB(2), BENZ, 2),
    "gy_row6": lattice(ROW(6), BENZ, 1),
    "gdy_row5": lattice(ROW(5), BENZ, 2),
    # hybrids: fused units joined by links
    "naph_row4_n1": lattice(ROW(4), NAPH, 1),
    "naph_tri3_n2": lattice([(0, 0), (1, 0), (0, 1)], NAPH, 2),
    "pyrene_row3_n1": lattice(ROW(3), PYRENE, 1),
    "pyrene_tri3_n2": lattice([(0, 0), (1, 0), (0, 1)], PYRENE, 2),
    "coronene_dimer_n1": lattice(ROW(2), CORONENE, 1),
    "coronene_dimer_n2": lattice(ROW(2), CORONENE, 2),
    "coronene_tri3_n1": lattice([(0, 0), (1, 0), (0, 1)], CORONENE, 1),
    "coronene_star6_n1": star(CORONENE, 6, 1),
    "coronene_star3_n2": star(CORONENE, [(1, 0), (-1, 1), (0, -1)], 2),
    "ovalene_dimer_n1": lattice(ROW(2), OVALENE, 1),
    "ovalene_star2_n2": star(OVALENE, [(1, 0), (-1, 0)], 2),
    "circum_star2_n1": star(CIRCUMCORONENE, [(1, 0), (-1, 0)], 1),
    "circum_star6_n2": star(CIRCUMCORONENE, 6, 2),
}

if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from linked import LinkError, build
    for name, design in DESIGNS.items():
        try:
            b = build(design)
            rings = sorted(len(r) for r in b.mol.GetRingInfo().AtomRings() if len(r) > 6)
            print(f"OK   {name:20s} {b.formula:8s} {b.n_carbon:3d} C, units {b.info['n_units']}, links {b.info['n_links']}, "
                  f"macrocycles {rings}")
        except LinkError as error:
            print(f"FAIL {name:20s} {str(error)[:150]}")
