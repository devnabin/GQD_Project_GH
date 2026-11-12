# Created date: 2026-11-10 (America/Chicago)
"""Convert between GQD molecules and hexagon-grid coordinates.

A GQD is a set of fused hexagons on a honeycomb grid. Each hexagon is an axial
coordinate (q, r). Its six neighbours are at the HEX_DIR offsets.

hex_to_mol(hexagons) -> RDKit Mol      (rule-based, from cluster_to_mol in Scripts/01_structure_generation.py)
mol_to_hex(mol)      -> list of (q, r) (inverse; recovers the hexagons from the ring graph)
"""

from collections import deque

from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")

HEX_DIR = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]

# The 6 corners of hexagon (q, r), in cyclic order. A corner is named by the
# three hexagons that meet there, so corners shared between hexagons get the same name.
VERT_FNS = [
    lambda q, r: frozenset([(q, r), (q + 1, r - 1), (q + 1, r)]),
    lambda q, r: frozenset([(q, r), (q + 1, r), (q, r + 1)]),
    lambda q, r: frozenset([(q, r), (q, r + 1), (q - 1, r + 1)]),
    lambda q, r: frozenset([(q, r), (q - 1, r + 1), (q - 1, r)]),
    lambda q, r: frozenset([(q, r), (q - 1, r), (q, r - 1)]),
    lambda q, r: frozenset([(q, r), (q, r - 1), (q + 1, r - 1)]),
]
# The hexagon that shares edge k (between corner k and corner k+1).
EDGE_NEIGHBOR = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]


class HexError(ValueError):
    """Raised when a hexagon list or molecule cannot be converted."""


def check_hexagons(hexagons) -> list[tuple[int, int]]:
    """Validate a hexagon list: integer pairs, no duplicates, all connected."""
    try:
        cells = [(int(q), int(r)) for q, r in hexagons]
    except (TypeError, ValueError) as error:
        raise HexError(f"hexagons must be a list of [q, r] integer pairs ({error})") from None
    if not cells:
        raise HexError("hexagon list is empty")
    if len(set(cells)) != len(cells):
        duplicates = sorted({c for c in cells if cells.count(c) > 1})
        raise HexError(f"duplicate hexagons: {duplicates}")

    cell_set = set(cells)
    seen = {cells[0]}
    queue = deque([cells[0]])
    while queue:
        q, r = queue.popleft()
        for dq, dr in HEX_DIR:
            neighbor = (q + dq, r + dr)
            if neighbor in cell_set and neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    if len(seen) != len(cells):
        raise HexError(f"hexagons are not all connected: {sorted(cell_set - seen)} are separate")
    return cells


def hex_to_mol(hexagons, feedback: bool = True, size_range: tuple[int, int] = (20, 40)) -> Chem.Mol:
    """Build an aromatic all-carbon molecule from hexagon coordinates.

    feedback=True: an open-shell rejection explains the sublattice imbalance and
    lists hexagon edits (within size_range) that make the structure closed-shell.
    """
    cells = check_hexagons(hexagons)

    corner_index: dict[frozenset, int] = {}
    rings = []
    for q, r in cells:
        ring = []
        for corner in VERT_FNS:
            key = corner(q, r)
            ring.append(corner_index.setdefault(key, len(corner_index)))
        rings.append(ring)

    bonds = set()
    for ring in rings:
        for i in range(6):
            bonds.add(tuple(sorted((ring[i], ring[(i + 1) % 6]))))

    # Choose the double bonds ourselves (a perfect matching). RDKit's own
    # kekulization of an all-aromatic graph this size can fail depending on
    # atom order, even when a valid Kekulé structure exists.
    double_bonds = _kekule_double_bonds(len(corner_index), bonds)
    if double_bonds is None:
        raise HexError(open_shell_feedback(cells, size_range) if feedback else OPEN_SHELL)

    mol = Chem.RWMol()
    for _ in corner_index:
        mol.AddAtom(Chem.Atom(6))
    for bond in bonds:
        mol.AddBond(*bond, Chem.BondType.DOUBLE if bond in double_bonds else Chem.BondType.SINGLE)
    mol = mol.GetMol()
    Chem.SanitizeMol(mol)  # adds hydrogens and perceives aromaticity
    # The rest of the pipeline reads SMILES with RDKit. RDKit's kekulizer has a
    # backtracking limit and cannot re-read some large valid structures (~10% of
    # random 20-40 ring shapes), so reject those here with a clear reason.
    reparsed = Chem.MolFromSmiles(Chem.MolToSmiles(mol, canonical=True))
    if reparsed is None:
        raise HexError("valid Kekulé structure, but RDKit cannot re-read its SMILES (RDKit kekulization limit)")
    return reparsed


def _kekule_double_bonds(n_atoms: int, bonds: set[tuple[int, int]]) -> set[tuple[int, int]] | None:
    """Return a set of bonds giving every atom exactly one double bond, or None.

    The honeycomb lattice is bipartite, so this is a bipartite perfect matching
    (augmenting-path / Kuhn's algorithm).
    """
    neighbors: list[list[int]] = [[] for _ in range(n_atoms)]
    for a, b in bonds:
        neighbors[a].append(b)
        neighbors[b].append(a)

    # Split atoms into the two sublattices.
    side = [-1] * n_atoms
    for start in range(n_atoms):
        if side[start] != -1:
            continue
        side[start] = 0
        queue = deque([start])
        while queue:
            atom = queue.popleft()
            for other in neighbors[atom]:
                if side[other] == -1:
                    side[other] = 1 - side[atom]
                    queue.append(other)
    left = [atom for atom in range(n_atoms) if side[atom] == 0]
    if 2 * len(left) != n_atoms:
        return None  # unequal sublattices: no perfect matching possible

    partner = [-1] * n_atoms

    def augment(atom: int, visited: set[int]) -> bool:
        for other in neighbors[atom]:
            if other in visited:
                continue
            visited.add(other)
            if partner[other] == -1 or augment(partner[other], visited):
                partner[other] = atom
                partner[atom] = other
                return True
        return False

    for atom in left:
        if not augment(atom, set()):
            return None
    return {tuple(sorted((atom, partner[atom]))) for atom in left}


# ---------------------------------------------------------------------------
# Open-shell diagnosis and repair suggestions
#
# The carbon atoms of a hexagon flake form two alternating sets (sublattices
# A and B): every bond joins an A atom to a B atom. A closed-shell structure
# pairs every atom with a neighbour by a double bond, which needs #A == #B
# (and, rarely, a bit more). Shapes such as triangles and L-shapes have extra
# atoms on one sublattice, so they must be radicals (Lieb's theorem).
# Corner {h1, h2, h3} is on sublattice A when sum(q + r) over its hexagons is 1 (mod 3).
# Point inversion [q, r] -> [a - q, b - r] swaps A and B, so point-symmetric
# shapes always have #A == #B.
# ---------------------------------------------------------------------------
OPEN_SHELL = "structure has no Kekulé form (open-shell / radical GQD)"


def sublattice_counts(hexagons) -> tuple[int, int]:
    """Number of carbon atoms on sublattice A and on sublattice B."""
    corners = {corner(q, r) for q, r in hexagons for corner in VERT_FNS}
    n_a = sum(sum(q + r for q, r in corner) % 3 == 1 for corner in corners)
    return n_a, len(corners) - n_a


def is_closed_shell(hexagons) -> bool:
    """True if the hexagon set has a Kekulé structure (assumes a valid, connected set)."""
    n_a, n_b = sublattice_counts(hexagons)
    if n_a != n_b:
        return False
    corner_index: dict[frozenset, int] = {}
    bonds = set()
    for q, r in hexagons:
        ring = [corner_index.setdefault(corner(q, r), len(corner_index)) for corner in VERT_FNS]
        bonds |= {tuple(sorted((ring[i], ring[(i + 1) % 6]))) for i in range(6)}
    return _kekule_double_bonds(len(corner_index), bonds) is not None


def _is_connected(cells: frozenset) -> bool:
    if not cells:
        return False
    start = next(iter(cells))
    seen, queue = {start}, deque([start])
    while queue:
        q, r = queue.popleft()
        for dq, dr in HEX_DIR:
            neighbor = (q + dq, r + dr)
            if neighbor in cells and neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    return len(seen) == len(cells)


def _single_edits(cells: frozenset, size_range):
    """Yield (edit_text, new_cells) for every add/remove of one hexagon that keeps a valid shape."""
    low, high = size_range
    if len(cells) + 1 <= high:
        empty = {(q + dq, r + dr) for q, r in cells for dq, dr in HEX_DIR} - cells
        for cell in sorted(empty):
            yield f"ADD [{cell[0]}, {cell[1]}]", cells | {cell}
    if len(cells) - 1 >= low:
        for cell in sorted(cells):
            rest = cells - {cell}
            if _is_connected(rest):
                yield f"REMOVE [{cell[0]}, {cell[1]}]", rest


def open_shell_fixes(hexagons, size_range=(20, 40), max_edits: int = 8, beam: int = 30, max_options: int = 6):
    """Find hexagon edits that make an open-shell structure closed-shell.

    Returns (single, multi):
      single: up to max_options single edits that each give a closed-shell structure
      multi:  if no single edit works, the shortest edit sequence found (beam search
              on |#A - #B|), or [] if none found within max_edits
    """
    cells = frozenset(map(tuple, hexagons))
    size_range = (min(size_range[0], len(cells)), max(size_range[1], len(cells)))

    def imbalance(shape):
        n_a, n_b = sublattice_counts(shape)
        return abs(n_a - n_b)

    single = [text for text, shape in _single_edits(cells, size_range) if is_closed_shell(shape)]
    if single:
        return single[:max_options], []

    frontier, seen = [((), cells)], {cells}
    for _ in range(max_edits):
        candidates = []
        for path, shape in frontier:
            for text, new in _single_edits(shape, size_range):
                if new in seen:
                    continue
                seen.add(new)
                if is_closed_shell(new):
                    return [], list(path) + [text]
                candidates.append((imbalance(new), len(candidates), path + (text,), new))
        candidates.sort(key=lambda item: item[:2])
        frontier = [(path, shape) for _, _, path, shape in candidates[:beam]]
    return [], []


def open_shell_feedback(hexagons, size_range=(20, 40)) -> str:
    """Rejection message for an open-shell structure: the cause plus concrete fixes."""
    cells = [tuple(cell) for cell in hexagons]
    n_a, n_b = sublattice_counts(cells)
    if n_a != n_b:
        cause = (f"its carbon atoms form two alternating sets (sublattices) that must be equal in size, "
                 f"but here they are {max(n_a, n_b)} vs {min(n_a, n_b)} ({abs(n_a - n_b)} unpaired atom(s); "
                 "typical causes: triangular parts, L-shaped corners, long zigzag edges)")
    else:
        cause = "the sublattices are equal in size, but one region of the shape cannot be paired with double bonds"
    single, multi = open_shell_fixes(cells, size_range)
    if single:
        fix = "Single-hexagon edits that each make it closed-shell: " + "; ".join(single) + "."
    elif multi:
        fix = "No single edit fixes it. Shortest fix found: " + " + ".join(multi) + "."
    else:
        fix = "No small fix was found; redesign the shape."
    tip = "Tip: point-symmetric shapes (every [q, r] has a partner [a-q, b-r] for one fixed a, b) are always balanced."
    return f"{OPEN_SHELL}: {cause}. {fix} {tip}"


def mol_to_hex(mol: Chem.Mol) -> list[tuple[int, int]]:
    """Recover hexagon coordinates from a fused-hexagon (benzenoid) molecule.

    Places the first 6-membered ring at (0, 0), then walks across shared bonds,
    placing each fused ring at the grid position implied by the shared edge.
    Raises HexError if the molecule is not a flat set of fused hexagons.
    """
    if mol is None:
        raise HexError("molecule is None")
    rings = [list(ring) for ring in mol.GetRingInfo().AtomRings() if len(ring) == 6]
    if not rings:
        raise HexError("no 6-membered rings")

    # Which rings share each bond.
    rings_by_bond: dict[tuple[int, int], list[int]] = {}
    for index, ring in enumerate(rings):
        for i in range(6):
            bond = tuple(sorted((ring[i], ring[(i + 1) % 6])))
            rings_by_bond.setdefault(bond, []).append(index)

    position: dict[int, tuple[int, int]] = {0: (0, 0)}
    atom_corner: dict[int, frozenset] = {}
    # Ring 0: its atoms (in ring order) take corners 0..5.
    for slot, atom in enumerate(rings[0]):
        atom_corner[atom] = VERT_FNS[slot](0, 0)

    queue = deque([0])
    while queue:
        index = queue.popleft()
        ring = rings[index]
        q, r = position[index]
        # Slot of each atom of this ring = which corner of (q, r) it sits on.
        corners = [VERT_FNS[k](q, r) for k in range(6)]
        slot_of = {atom: corners.index(atom_corner[atom]) for atom in ring}
        for i in range(6):
            a, b = ring[i], ring[(i + 1) % 6]
            sa, sb = slot_of[a], slot_of[b]
            k = sa if (sa + 1) % 6 == sb else sb  # edge k runs from corner k to k+1
            for other in rings_by_bond[tuple(sorted((a, b)))]:
                if other == index:
                    continue
                dq, dr = EDGE_NEIGHBOR[k]
                target = (q + dq, r + dr)
                if other in position:
                    if position[other] != target:
                        raise HexError("rings do not fit on a flat hexagon grid")
                    continue
                position[other] = target
                _assign_corners(rings[other], target, (a, b), atom_corner)
                queue.append(other)

    if len(position) != len(rings):
        raise HexError("6-membered rings are not all fused together")
    cells = list(position.values())
    if len(set(cells)) != len(cells):
        raise HexError("two rings landed on the same grid position (overlapping)")
    return sorted(cells)


def _assign_corners(ring, cell, shared_bond, atom_corner) -> None:
    """Give each atom of a newly placed ring its corner name, keeping ring order.

    Orientation comes from shared_bond, the bond this ring shares with an
    already placed ring, so both of its atoms already have corner names.
    """
    corners = [VERT_FNS[k](*cell) for k in range(6)]
    a, b = shared_bond
    anchor = ring.index(a)
    start = corners.index(atom_corner[a])
    # Ring order may run with or against the corner order; pick the direction that matches.
    if ring[(anchor + 1) % 6] == b:
        step = 1 if atom_corner[b] == corners[(start + 1) % 6] else -1
    else:  # b comes just before a in ring order
        step = -1 if atom_corner[b] == corners[(start + 1) % 6] else 1
    for offset in range(6):
        atom = ring[(anchor + offset) % 6]
        corner = corners[(start + step * offset) % 6]
        if atom_corner.setdefault(atom, corner) != corner:
            raise HexError("ring atoms do not match a flat hexagon grid")


def smiles_to_hex(smiles: str) -> list[tuple[int, int]]:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise HexError("RDKit could not parse the SMILES")
    return mol_to_hex(mol)


def hex_to_smiles(hexagons, feedback: bool = True) -> str:
    return Chem.MolToSmiles(hex_to_mol(hexagons, feedback=feedback), canonical=True)
