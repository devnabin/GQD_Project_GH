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


def hex_to_mol(hexagons) -> Chem.Mol:
    """Build an aromatic all-carbon molecule from hexagon coordinates."""
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
        raise HexError("structure has no Kekulé form (open-shell / radical GQD)")

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


def hex_to_smiles(hexagons) -> str:
    return Chem.MolToSmiles(hex_to_mol(hexagons), canonical=True)
