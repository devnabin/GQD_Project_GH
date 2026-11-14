# Created date: 2026-11-12 (America/Chicago)
"""Stage 3d, L1: linked-carbon structures (graphyne/graphdiyne fragments and GQD-graphyne hybrids).

A structure is written as

    {"units": {"A": [[0,0]], "B": [[0,0],[1,0]]},     # each unit: a hexagon list (Stage 1 format)
     "place": {"A": [0,0], "B": [1,0]},               # each unit on a coarse grid (axial, same neighbour rules)
     "links": [["A", "B", 1]]}                        # 1 = -C#C- (graphyne), 2 = -C#C-C#C- (graphdiyne)

build(structure) -> Linked (RDKit mol, canonical SMILES, 3D start geometry), or raises LinkError
with a plain-language reason. Design choices (see PROGRESS.md / README.md):
  * The coarse grid is the hexagon grid rotated by 30 degrees, so the six coarse directions are the
    six directions in which edge C-H bonds point (as in gamma-graphyne, ring vertices face each other).
  * A link in coarse direction theta leaves unit A from its outermost edge carbon whose C-H points
    along theta, and enters unit B at its outermost edge carbon pointing back (theta + 180).
  * Units are placed along a spanning tree of the links; the coarse grid gives only directions.
    Links that close a ring must then fit within a tolerance, otherwise the structure is rejected.
"""

import json
import math
import zlib
from collections import deque
from dataclasses import dataclass, field

import numpy as np
from rdkit import Chem, RDLogger
from rdkit.Chem import rdMolDescriptors

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Stage1.gqd_hex import HEX_DIR, VERT_FNS, HexError, _kekule_double_bonds, check_hexagons, open_shell_feedback  # noqa: E402

RDLogger.DisableLog("rdApp.*")

CC_RING, CH = 1.42, 1.09            # aromatic C-C and C-H (A)
C_SP2_SP, C_TRIPLE, C_SP_SP = 1.40, 1.21, 1.35
HEX_STEP = math.sqrt(3) * CC_RING   # distance between fused hexagon centres
LINK_BONDS = {1: [C_SP2_SP, C_TRIPLE, C_SP2_SP],
              2: [C_SP2_SP, C_TRIPLE, C_SP_SP, C_TRIPLE, C_SP2_SP]}
SIZE_RANGE = (40, 150)              # carbon atoms; current GQDs have 64-118 (Stage 3a calibration set)
CLOSE_TOL = (0.15, 15.0)            # ring-closing link: relative length error, angle error (degrees)
CLASH_A = 1.6                       # minimum distance between atoms of different parts (A)
JITTER_A = 0.05                     # out-of-plane noise of the start geometry (A), as in Stage 3a


class LinkError(ValueError):
    """Raised when a linked structure is invalid; the message says what to change."""


@dataclass
class Linked:
    mol: Chem.Mol
    smiles: str
    formula: str
    symbols: list
    coords: np.ndarray
    n_carbon: int
    info: dict = field(default_factory=dict)


# ----------------------------------------------------------------------------------------------
# Geometry helpers
# ----------------------------------------------------------------------------------------------
def _hex_centre(q, r):
    return np.array([HEX_STEP * (q + r / 2), HEX_STEP * (math.sqrt(3) / 2) * r])


def coarse_direction(offset) -> float:
    """Angle (degrees) of a coarse-grid neighbour offset: the fine-grid angle rotated by 30."""
    dq, dr = offset
    x, y = dq + dr / 2, math.sqrt(3) / 2 * dr
    return (math.degrees(math.atan2(y, x)) + 30.0) % 360.0


def _unit_atoms(cells):
    """Carbons of one unit: keys, 2D positions, bonds, and Kekule double bonds (or None)."""
    index, pos, rings = {}, [], []
    for q, r in cells:
        ring = []
        for fn in VERT_FNS:
            key = fn(q, r)
            if key not in index:
                index[key] = len(pos)
                pos.append(np.mean([_hex_centre(*h) for h in key], axis=0))
            ring.append(index[key])
        rings.append(ring)
    bonds = {tuple(sorted((ring[k], ring[(k + 1) % 6]))) for ring in rings for k in range(6)}
    return np.array(pos), bonds, _kekule_double_bonds(len(pos), bonds)


def _attach_atom(pos, bonds, theta, used):
    """Outermost edge carbon whose C-H points along theta (degrees)."""
    nb = {i: [] for i in range(len(pos))}
    for a, b in bonds:
        nb[a].append(b)
        nb[b].append(a)
    u = np.array([math.cos(math.radians(theta)), math.sin(math.radians(theta))])
    centroid = pos.mean(axis=0)
    best = None
    for i, neighbours in nb.items():
        if len(neighbours) != 2 or i in used:
            continue
        out = pos[i] - pos[neighbours].mean(axis=0)
        out /= np.linalg.norm(out)
        if np.dot(out, u) < math.cos(math.radians(1.0)):
            continue
        rel = pos[i] - centroid
        key = (-round(float(np.dot(rel, u)), 6), round(abs(float(u[0] * rel[1] - u[1] * rel[0])), 6), i)
        best = min(best, key) if best else key
    return None if best is None else best[2]


# ----------------------------------------------------------------------------------------------
# Parsing and checks
# ----------------------------------------------------------------------------------------------
def parse(structure):
    """Normalise and check the JSON-like structure. Returns (units, place, links)."""
    if isinstance(structure, str):
        try:
            structure = json.loads(structure)
        except json.JSONDecodeError as error:
            raise LinkError(f"structure is not valid JSON ({error})") from None
    if not isinstance(structure, dict) or not {"units", "place", "links"} <= set(structure):
        raise LinkError('structure must be an object with "units", "place" and "links"')
    units_in, place_in, links_in = structure["units"], structure["place"], structure["links"]
    if not isinstance(units_in, dict) or not units_in:
        raise LinkError('"units" must be a non-empty object {name: hexagon list}')
    units = {}
    for name, cells in units_in.items():
        try:
            units[str(name)] = check_hexagons(cells)
        except HexError as error:
            raise LinkError(f"unit {name}: {error}") from None
    if set(map(str, place_in)) != set(units):
        missing, extra = set(units) - set(map(str, place_in)), set(map(str, place_in)) - set(units)
        raise LinkError(f'every unit needs exactly one place; missing: {sorted(missing)}, unknown: {sorted(extra)}')
    place = {}
    for name, xy in place_in.items():
        try:
            place[str(name)] = (int(xy[0]), int(xy[1]))
        except (TypeError, ValueError, IndexError):
            raise LinkError(f"place of unit {name} must be [Q, R] integers") from None
    taken = {}
    for name, xy in place.items():
        if xy in taken:
            raise LinkError(f"units {taken[xy]} and {name} are both placed at {list(xy)}; each place holds one unit")
        taken[xy] = name
    links, seen = [], set()
    for link in links_in:
        try:
            a, b, n = str(link[0]), str(link[1]), int(link[2])
        except (TypeError, ValueError, IndexError):
            raise LinkError(f'each link must be [unit, unit, n]; got {link}') from None
        if a not in units or b not in units:
            raise LinkError(f"link {link} names a unit that does not exist")
        if a == b:
            raise LinkError(f"link {link} joins a unit to itself")
        if n not in LINK_BONDS:
            raise LinkError(f"link {link}: n must be 1 (-C#C-) or 2 (-C#C-C#C-), not {n}")
        offset = (place[b][0] - place[a][0], place[b][1] - place[a][1])
        if offset not in HEX_DIR:
            raise LinkError(f"link {a}-{b}: units at {list(place[a])} and {list(place[b])} are not coarse-grid "
                            "neighbours; a link can only join neighbouring places (offsets [1,0], [-1,0], [0,1], "
                            "[0,-1], [1,-1], [-1,1])")
        if frozenset((a, b)) in seen:
            raise LinkError(f"units {a} and {b} are linked twice")
        seen.add(frozenset((a, b)))
        links.append((a, b, n, offset))
    # connectivity over links
    adj = {u: set() for u in units}
    for a, b, _, _ in links:
        adj[a].add(b)
        adj[b].add(a)
    start = next(iter(units))
    reach, queue = {start}, deque([start])
    while queue:
        for v in adj[queue.popleft()]:
            if v not in reach:
                reach.add(v)
                queue.append(v)
    if reach != set(units):
        raise LinkError(f"units {sorted(set(units) - reach)} are not linked to the rest; every unit must be "
                        "connected through links")
    return units, place, links


# ----------------------------------------------------------------------------------------------
# Build
# ----------------------------------------------------------------------------------------------
def build(structure, size_range=SIZE_RANGE, feedback=True) -> Linked:
    units, place, links = parse(structure)

    # 1. every unit on its own must be closed-shell (links attach to carbons that keep their p electron)
    parts = {}
    for name, cells in units.items():
        pos, bonds, doubles = _unit_atoms(cells)
        if doubles is None:
            msg = open_shell_feedback(cells, (1, 40)) if feedback else "no Kekule form (open-shell)"
            raise LinkError(f"unit {name} is open-shell: {msg}")
        parts[name] = {"pos": pos, "bonds": bonds, "doubles": doubles, "used": set()}

    # 2. attach carbons for every link
    plan = []
    for a, b, n, offset in links:
        theta = coarse_direction(offset)
        ia = _attach_atom(parts[a]["pos"], parts[a]["bonds"], theta, parts[a]["used"])
        ib = _attach_atom(parts[b]["pos"], parts[b]["bonds"], (theta + 180) % 360, parts[b]["used"])
        if ia is None or ib is None:
            bad = a if ia is None else b
            raise LinkError(f"link {a}-{b}: unit {bad} has no free edge carbon facing the link direction "
                            f"({theta:.0f} degrees); remove another link from that side or change the unit")
        parts[a]["used"].add(ia)
        parts[b]["used"].add(ib)
        plan.append((a, b, n, theta, ia, ib))

    # 3. place units along a spanning tree (BFS from the first unit), then check ring-closing links
    shift = {next(iter(units)): np.zeros(2)}
    pending = list(plan)
    progress = True
    while pending and progress:
        progress = False
        for item in list(pending):
            a, b, n, theta, ia, ib = item
            length = sum(LINK_BONDS[n])
            u = np.array([math.cos(math.radians(theta)), math.sin(math.radians(theta))])
            if a in shift and b not in shift:
                shift[b] = shift[a] + parts[a]["pos"][ia] + length * u - parts[b]["pos"][ib]
            elif b in shift and a not in shift:
                shift[a] = shift[b] + parts[b]["pos"][ib] - length * u - parts[a]["pos"][ia]
            else:
                continue
            pending.remove(item)
            progress = True
    tree = set(plan) - set(pending)
    closures = []
    for a, b, n, theta, ia, ib in plan:
        if (a, b, n, theta, ia, ib) in tree:
            continue
        start, end = shift[a] + parts[a]["pos"][ia], shift[b] + parts[b]["pos"][ib]
        vec = end - start
        length = sum(LINK_BONDS[n])
        d = float(np.linalg.norm(vec))
        angle = abs((math.degrees(math.atan2(vec[1], vec[0])) - theta + 180) % 360 - 180)
        closures.append({"link": f"{a}-{b}", "length_A": round(d, 3), "ideal_A": round(length, 3),
                         "angle_error_deg": round(angle, 2)})
        if abs(d - length) / length > CLOSE_TOL[0] or angle > CLOSE_TOL[1]:
            raise LinkError(f"link {a}-{b} cannot close the ring: its ends are {d:.2f} A apart and "
                            f"{angle:.0f} degrees off the link direction, but an n={n} link needs {length:.2f} A "
                            "in a straight line. Use the same link length all around a ring, or units whose "
                            "sizes fit the ring")

    # 4. assemble atoms and bonds
    mol = Chem.RWMol()
    xy, owner, offsets = [], [], {}
    for name, part in parts.items():
        offsets[name] = len(xy)
        for p in part["pos"]:
            mol.AddAtom(Chem.Atom(6))
            xy.append(shift[name] + p)
            owner.append(name)
        for i, j in part["bonds"]:
            bt = Chem.BondType.DOUBLE if (i, j) in part["doubles"] else Chem.BondType.SINGLE
            mol.AddBond(offsets[name] + i, offsets[name] + j, bt)
    for a, b, n, theta, ia, ib in plan:
        start, end = offsets[a] + ia, offsets[b] + ib
        p0, p1 = xy[start], xy[end]
        lengths = LINK_BONDS[n]
        cum = np.cumsum(lengths)[:-1] / sum(lengths)
        chain = [start]
        for f in cum:
            mol.AddAtom(Chem.Atom(6))
            xy.append(p0 + f * (p1 - p0))
            owner.append(f"link {a}-{b}")
            chain.append(len(xy) - 1)
        chain.append(end)
        for k in range(len(chain) - 1):
            triple = k % 2 == 1  # sp2-sp single, sp#sp triple, sp-sp single, ...
            mol.AddBond(chain[k], chain[k + 1], Chem.BondType.TRIPLE if triple else Chem.BondType.SINGLE)
    mol = mol.GetMol()
    try:
        Chem.SanitizeMol(mol)
    except Exception as error:  # should not happen for valid input
        raise LinkError(f"RDKit could not sanitise the structure ({error})") from None
    smiles = Chem.MolToSmiles(mol)
    reread = Chem.MolFromSmiles(smiles)
    if reread is None:
        raise LinkError("valid structure, but RDKit cannot re-read its SMILES (RDKit kekulization limit)")
    n_carbon = mol.GetNumAtoms()

    # 5. hydrogens on carbons with two carbon neighbours, then the clash check between parts
    carbons = np.array(xy)
    symbols, coords, part_of = ["C"] * n_carbon, [np.r_[c, 0.0] for c in carbons], list(owner)
    h_parent = []
    for atom in mol.GetAtoms():
        if atom.GetTotalNumHs() == 1:
            i = atom.GetIdx()
            nbr = [x.GetIdx() for x in atom.GetNeighbors()]
            out = carbons[i] - carbons[nbr].mean(axis=0)
            out /= np.linalg.norm(out)
            symbols.append("H")
            coords.append(np.r_[carbons[i] + CH * out, 0.0])
            part_of.append(owner[i])
            h_parent.append(i)
        elif atom.GetTotalNumHs() > 1:
            raise LinkError("internal: a carbon with two hydrogens was produced")
    coords = np.array(coords)
    bonded = {tuple(sorted((b.GetBeginAtomIdx(), b.GetEndAtomIdx()))) for b in mol.GetBonds()}
    bonded |= {tuple(sorted((n_carbon + k, p))) for k, p in enumerate(h_parent)}
    worst = None
    for i in range(len(coords)):
        for j in range(i + 1, len(coords)):
            if part_of[i] == part_of[j] or (i, j) in bonded:
                continue
            d = float(np.linalg.norm(coords[i] - coords[j]))
            if d < CLASH_A and (worst is None or d < worst[0]):
                worst = (d, part_of[i], part_of[j])
    if worst:
        raise LinkError(f"atoms of {worst[1]} and {worst[2]} come {worst[0]:.2f} A apart (minimum {CLASH_A} A); "
                        "the parts overlap. Move a unit to a free place, shorten it, or use a longer link")
    # size last, so a structural problem is reported before a size problem
    if not size_range[0] <= n_carbon <= size_range[1]:
        raise LinkError(f"{n_carbon} carbon atoms; the allowed range is {size_range[0]}-{size_range[1]}. "
                        + ("Add units or use longer links." if n_carbon < size_range[0] else "Remove units or hexagons."))

    # 6. small reproducible out-of-plane noise (seeded by the SMILES, so the same structure gets the same start)
    rng = np.random.default_rng(zlib.crc32(smiles.encode()))
    coords[:, 2] += rng.normal(0.0, JITTER_A, len(coords))
    # mol (not the re-read copy) keeps the atom order of coords: carbons first, then H in parent order
    return Linked(mol=mol, smiles=smiles, formula=rdMolDescriptors.CalcMolFormula(mol), symbols=symbols,
                  coords=coords, n_carbon=n_carbon,
                  info={"n_units": len(units), "n_links": len(plan), "ring_closures": closures,
                        "triple_bonds": sum(b.GetBondType() == Chem.BondType.TRIPLE for b in mol.GetBonds())})


def write_xyz(path, symbols, coords):
    lines = [str(len(symbols)), ""] + [f"{s} {x:.6f} {y:.6f} {z:.6f}" for s, (x, y, z) in zip(symbols, coords)]
    Path(path).write_text("\n".join(lines) + "\n")
