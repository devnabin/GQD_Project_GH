# Created date: 2026-11-10 (America/Chicago)
"""Physics-based features for predicting the xTB HOMO-LUMO gap of a GQD.

All features come from the carbon skeleton (and hexagon coordinates when given),
so they work for any new GQD built by Stage1.gqd_hex.

Feature groups
  huckel_*   Hückel (tight-binding) π spectrum of the carbon graph
  orb_*      where the Hückel HOMO / LUMO live (edges vs. interior, spread)
  kekule_*   number of Kekulé structures (|det| of the bipartite adjacency)
  clar_*     Clar number: max. number of disjoint aromatic sextets (small ILP)
  edge_*     edge C-H patterns: solo / duo / trio / quarto hydrogens
  perim_*    outer edge motifs: fissure / bay / cove / fjord / lagoon
  hole_*     internal holes (pores); their inner C-H point at each other
  shape_*    size and shape of the hexagon cluster
"""

import numpy as np
from rdkit import Chem
from scipy.optimize import Bounds, LinearConstraint, milp

FEATURE_NAMES: list[str] = []  # filled on first call to compute_features


def compute_features(mol: Chem.Mol, hexagons=None) -> dict[str, float]:
    """Return a dict of named features for one all-carbon fused-hexagon molecule."""
    adjacency = Chem.GetAdjacencyMatrix(mol).astype(float)
    n_atoms = adjacency.shape[0]
    degree = adjacency.sum(axis=1)
    features: dict[str, float] = {}

    features |= _huckel(adjacency, degree)
    features |= _kekule(adjacency)
    features |= _clar(mol)
    features |= _edge_hydrogens(adjacency, degree)
    features |= _perimeter_and_holes(mol)

    rings = [ring for ring in mol.GetRingInfo().AtomRings() if len(ring) == 6]
    features["shape_n_hex"] = len(rings)
    features["shape_n_C"] = n_atoms
    features["shape_n_H"] = float((degree == 2).sum())
    features["shape_frac_internal_C"] = float((degree == 3).sum()) / n_atoms
    features |= _shape(hexagons) if hexagons is not None else {}

    if not FEATURE_NAMES:
        FEATURE_NAMES.extend(features)
    return features


# ---------------------------------------------------------------------------
# Hückel spectrum: eigenvalues of the adjacency matrix (units of |β|).
# Half the orbitals are occupied; HOMO is the lowest occupied in these units
# because a bonding orbital has a positive adjacency eigenvalue.
# ---------------------------------------------------------------------------
def _huckel(adjacency: np.ndarray, degree: np.ndarray) -> dict[str, float]:
    values, vectors = np.linalg.eigh(adjacency)
    order = np.argsort(values)[::-1]  # most bonding first
    values, vectors = values[order], vectors[:, order]
    n_occ = len(values) // 2
    homo, lumo = values[n_occ - 1], values[n_occ]
    homo_vec, lumo_vec = vectors[:, n_occ - 1], vectors[:, n_occ]
    edge = degree == 2

    f = {
        "huckel_gap": homo - lumo,
        "huckel_homo": homo,
        "huckel_lumo": lumo,
        "huckel_gap_homo1_lumo1": values[n_occ - 2] - values[n_occ + 1],
        "huckel_homo_homo1": values[n_occ - 2] - homo,
        "huckel_lumo_lumo1": lumo - values[n_occ + 1],
        "huckel_pi_energy_per_atom": 2 * values[:n_occ].sum() / len(values),
        "huckel_n_near_zero_005": float((np.abs(values) < 0.05).sum()),
        "huckel_n_near_zero_025": float((np.abs(values) < 0.25).sum()),
        "huckel_n_near_zero_050": float((np.abs(values) < 0.50).sum()),
        # inverse participation ratio: high = orbital localised on few atoms
        "orb_homo_ipr": float((homo_vec ** 4).sum()),
        "orb_lumo_ipr": float((lumo_vec ** 4).sum()),
        # share of the frontier orbital on edge (C-H) atoms
        "orb_homo_edge_weight": float((homo_vec[edge] ** 2).sum()),
        "orb_lumo_edge_weight": float((lumo_vec[edge] ** 2).sum()),
    }
    return {k: float(v) for k, v in f.items()}


# ---------------------------------------------------------------------------
# Kekulé count: for benzenoids, K = |det(B)| where B is the adjacency block
# between the two sublattices (Dewar–Longuet-Higgins).
# ---------------------------------------------------------------------------
def _sublattices(adjacency: np.ndarray) -> np.ndarray:
    n = adjacency.shape[0]
    side = np.full(n, -1)
    for start in range(n):
        if side[start] != -1:
            continue
        side[start] = 0
        stack = [start]
        while stack:
            atom = stack.pop()
            for other in np.nonzero(adjacency[atom])[0]:
                if side[other] == -1:
                    side[other] = 1 - side[atom]
                    stack.append(other)
    return side


def _kekule(adjacency: np.ndarray) -> dict[str, float]:
    side = _sublattices(adjacency)
    block = adjacency[np.ix_(side == 0, side == 1)]
    if block.shape[0] != block.shape[1]:
        return {"kekule_log10_count": 0.0, "kekule_log10_per_hex": 0.0}
    with np.errstate(all="ignore"):  # macOS Accelerate raises spurious FP warnings here
        sign, logdet = np.linalg.slogdet(block)
    log10_k = logdet / np.log(10) if sign != 0 else 0.0
    n_hex = (adjacency.sum() / 2 - adjacency.shape[0] + 1)  # cycle rank = number of hexagons (no holes)
    return {"kekule_log10_count": float(log10_k), "kekule_log10_per_hex": float(log10_k / max(n_hex, 1))}


# ---------------------------------------------------------------------------
# Clar number: choose the most hexagons as disjoint "sextets" so that every
# remaining carbon is covered by exactly one double bond. Solved as an ILP.
# ---------------------------------------------------------------------------
def _clar(mol: Chem.Mol) -> dict[str, float]:
    rings = [ring for ring in mol.GetRingInfo().AtomRings() if len(ring) == 6]
    bonds = [(b.GetBeginAtomIdx(), b.GetEndAtomIdx()) for b in mol.GetBonds()]
    n_atoms, n_rings, n_bonds = mol.GetNumAtoms(), len(rings), len(bonds)

    # Each atom: (sextets containing it) + (double bonds touching it) == 1
    matrix = np.zeros((n_atoms, n_rings + n_bonds))
    for j, ring in enumerate(rings):
        matrix[list(ring), j] = 1
    for j, (a, b) in enumerate(bonds):
        matrix[[a, b], n_rings + j] = 1
    objective = np.concatenate([-np.ones(n_rings), np.zeros(n_bonds)])
    result = milp(objective, constraints=LinearConstraint(matrix, 1, 1),
                  integrality=np.ones(n_rings + n_bonds), bounds=Bounds(0, 1))
    clar = float(round(-result.fun)) if result.success else 0.0
    return {"clar_number": clar, "clar_per_hex": clar / max(n_rings, 1)}


# ---------------------------------------------------------------------------
# Edge hydrogens: runs of neighbouring C-H carbons along the edge.
# solo = 1 (zigzag-like), duo = 2 (armchair-like), trio = 3, quarto = 4+.
# ---------------------------------------------------------------------------
def _edge_hydrogens(adjacency: np.ndarray, degree: np.ndarray) -> dict[str, float]:
    edge_atoms = set(np.nonzero(degree == 2)[0])
    seen, runs = set(), []
    for start in edge_atoms:
        if start in seen:
            continue
        size, stack = 0, [start]
        seen.add(start)
        while stack:
            atom = stack.pop()
            size += 1
            for other in np.nonzero(adjacency[atom])[0]:
                if other in edge_atoms and other not in seen:
                    seen.add(other)
                    stack.append(other)
        runs.append(size)
    runs = np.array(runs) if runs else np.zeros(0)
    n_h = max(len(edge_atoms), 1)
    f = {
        "edge_solo": float((runs == 1).sum()),
        "edge_duo": float((runs == 2).sum()),
        "edge_trio": float((runs == 3).sum()),
        "edge_quarto_plus": float((runs >= 4).sum()),
    }
    f["edge_frac_H_solo"] = f["edge_solo"] / n_h
    f["edge_frac_H_duo"] = 2 * f["edge_duo"] / n_h
    f["edge_frac_H_trio"] = 3 * f["edge_trio"] / n_h
    f["edge_frac_H_quarto_plus"] = float(runs[runs >= 4].sum()) / n_h
    return f


# ---------------------------------------------------------------------------
# Perimeter and holes. Boundary bonds belong to exactly one hexagon; they form
# one outer loop plus one loop per hole. Along the outer loop, a run of k
# consecutive carbons without H is a fissure (1), bay (2), cove (3),
# fjord (4) or lagoon (5+). Coves/fjords crowd H atoms and can twist the flake.
# ---------------------------------------------------------------------------
def _perimeter_and_holes(mol: Chem.Mol) -> dict[str, float]:
    hexagons = [ring for ring in mol.GetRingInfo().AtomRings() if len(ring) == 6]
    count: dict[tuple[int, int], int] = {}
    for ring in hexagons:
        for i in range(6):
            bond = tuple(sorted((ring[i], ring[(i + 1) % 6])))
            count[bond] = count.get(bond, 0) + 1
    neighbours: dict[int, list[int]] = {}
    for (a, b), c in count.items():
        if c == 1:
            neighbours.setdefault(a, []).append(b)
            neighbours.setdefault(b, []).append(a)

    loops, seen = [], set()
    for start in neighbours:
        if start in seen:
            continue
        loop, previous, current = [start], None, start
        seen.add(start)
        while True:
            options = [x for x in neighbours[current] if x != previous]
            following = options[0]
            if following == start:
                break
            if following in seen:  # unexpected branching; stop this loop
                break
            loop.append(following)
            seen.add(following)
            previous, current = current, following
        loops.append(loop)

    loops.sort(key=len, reverse=True)
    outer, holes = (loops[0] if loops else []), loops[1:]
    degree = [atom.GetDegree() for atom in mol.GetAtoms()]

    runs, run = [], 0
    if outer:
        degrees = [degree[a] for a in outer]
        start = degrees.index(2) if 2 in degrees else 0
        for d in degrees[start:] + degrees[:start] + [2]:
            if d == 3:
                run += 1
            elif run:
                runs.append(run)
                run = 0
    runs = np.array(runs) if runs else np.zeros(0)
    inner_h = sum(degree[a] == 2 for loop in holes for a in loop)
    return {
        "perim_length": float(len(outer)),
        "perim_fissure": float((runs == 1).sum()),
        "perim_bay": float((runs == 2).sum()),
        "perim_cove": float((runs == 3).sum()),
        "perim_fjord": float((runs == 4).sum()),
        "perim_lagoon": float((runs >= 5).sum()),
        "hole_count": float(len(holes)),
        "hole_total_size": float(sum(len(loop) for loop in holes)),
        "hole_max_size": float(max((len(loop) for loop in holes), default=0)),
        "hole_inner_H": float(inner_h),
    }


# ---------------------------------------------------------------------------
# Shape from hexagon centres.
# ---------------------------------------------------------------------------
def _shape(hexagons) -> dict[str, float]:
    cells = np.array(hexagons, dtype=float)
    centres = np.column_stack([np.sqrt(3) * (cells[:, 0] + cells[:, 1] / 2), 1.5 * cells[:, 1]])
    centred = centres - centres.mean(axis=0)
    eig = np.sort(np.linalg.eigvalsh(np.cov(centred.T) + 1e-9 * np.eye(2)))[::-1]
    cell_set = {tuple(c) for c in cells.astype(int)}
    neighbours = [sum((q + dq, r + dr) in cell_set
                      for dq, dr in [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)])
                  for q, r in cell_set]
    counts = np.bincount(neighbours, minlength=7)
    f = {
        "shape_radius_gyration": float(np.sqrt((centred ** 2).sum(axis=1).mean())),
        "shape_aspect_ratio": float(np.sqrt(eig[0] / eig[1])),
        "shape_max_extent": float(np.max(np.linalg.norm(centred, axis=1))),
    }
    for k in range(1, 7):
        f[f"shape_hex_with_{k}_neighbours"] = float(counts[k])
    return f
