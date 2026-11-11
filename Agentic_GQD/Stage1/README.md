<!-- Created date: 2026-11-10 (America/Chicago) -->

# Stage 1: Hexagon ↔ Molecule

**Status:** ✅ Done (2026-11-10)
**Part of:** LLM-guided evolution of GQDs (see `../WORK_DIRECTION.md` and `../Final_Planning.md`)

## What this stage does

In later stages the LLM will design GQDs by writing **hexagon coordinates**, not SMILES. Stage 1 builds the bridge between the two:

1. **Hexagons → molecule** (`hex_to_mol`): turns a list of hexagon positions into a valid RDKit molecule, so anything the LLM writes can be checked by the five validation steps.
2. **Molecule → hexagons** (`mol_to_hex`): turns an existing GQD (SMILES) back into hexagon positions, so our existing data can be used as starting structures and as fine-tuning data.
3. **Converts the full dataset**: all 91,174 generated GQDs, with xTB gaps attached where available.

## The hexagon coordinate system

A GQD is a set of fused hexagons on a honeycomb grid. Each hexagon has an **axial coordinate** `(q, r)`:

```
The 6 neighbours of hexagon (q, r):
   (q+1, r)   (q-1, r)
   (q, r+1)   (q, r-1)
   (q+1, r-1) (q-1, r+1)
```

Examples:

| Hexagons | Molecule |
|---|---|
| `[[0,0]]` | benzene |
| `[[0,0],[1,0]]` | naphthalene |
| `[[0,0],[1,0],[-1,0],[0,1],[0,-1],[1,-1],[-1,1]]` | coronene |

The coordinate system and corner rules are the same as in `Scripts/01_structure_generation.py` (`grow_cluster` / `cluster_to_mol`), which originally generated the dataset.

## Files

```
Stage1/
├── README.md               this file
├── gqd_hex.py              conversion module (imported by studio/agent.py)
├── build_hex_dataset.py    one-off script: converts the full dataset
└── data/
    ├── gqd_hex_dataset.csv         output: 91,174 structures with hexagon coordinates
    └── xtb_ids_without_smiles.txt  output: xTB IDs that have no SMILES
```

---

### `gqd_hex.py`: the conversion module

**Main functions**

| Function | Input | Output |
|---|---|---|
| `hex_to_mol(hexagons)` | `[[q, r], ...]` | RDKit `Mol` |
| `hex_to_smiles(hexagons)` | `[[q, r], ...]` | canonical SMILES |
| `mol_to_hex(mol)` | RDKit `Mol` | sorted list of `(q, r)` |
| `smiles_to_hex(smiles)` | SMILES | sorted list of `(q, r)` |
| `check_hexagons(hexagons)` | `[[q, r], ...]` | cleaned list, or raises `HexError` |

Any problem raises **`HexError`** with a plain-language reason. The agent passes that reason back to the LLM.

**How `hex_to_mol` works**

1. **Check the list** (`check_hexagons`): integer pairs, no duplicates, all hexagons connected.
2. **Make atoms:** each hexagon has 6 corners. A corner is named by the 3 hexagons that meet there, so a corner shared by neighbouring hexagons becomes **one** carbon atom.
3. **Make bonds:** each hexagon edge becomes a C–C bond.
4. **Choose double bonds ourselves:** we find a pattern where every carbon has exactly one double bond (a *perfect matching*; the honeycomb lattice is bipartite, so a simple augmenting-path algorithm works). If no such pattern exists, the GQD is **open-shell (radical)** and is rejected.
   - *Why not let RDKit do it?* RDKit's kekulizer gave up on some large GQDs **depending on atom order**: the same structure passed or failed when the hexagons were listed in a different order. The reference generator has this weakness too.
5. **Sanitize** with RDKit (adds hydrogens, marks aromaticity).
6. **Re-read check:** the SMILES is written and read back. RDKit cannot re-read about 10% of valid random 20–40 ring shapes (an internal backtracking limit). These are rejected, because every later step reads SMILES with RDKit. None of the 91k existing structures are affected.

**How `mol_to_hex` works**

1. Find all 6-membered rings in the molecule.
2. Place the first ring at `(0, 0)` and give its 6 atoms corner names.
3. Walk across shared bonds: a ring sharing edge *k* of a placed hexagon must sit at the neighbouring grid position for edge *k*. Its orientation comes from the **shared bond**, and its atoms inherit corner names.
4. Repeat until every ring is placed, then check that nothing overlaps and everything is connected. Otherwise it raises `HexError` (e.g. not a flat graphene-like molecule).

Notes:

- The output's position and orientation are arbitrary (it may be rotated or mirrored compared with the original). The **molecule** is identical, which is what matters.
- A **one-hexagon hole** has the same atoms and bonds as a filled hexagon, so it is the same molecule and `mol_to_hex` returns it filled.

**Rejection reasons you may see**

| Message | Meaning |
|---|---|
| `duplicate hexagons: ...` | Same `(q, r)` listed twice |
| `hexagons are not all connected: ...` | Some hexagons don't touch the rest |
| `structure has no Kekulé form (open-shell / radical GQD)` | No valid single/double bond pattern exists |
| `valid Kekulé structure, but RDKit cannot re-read its SMILES` | RDKit limitation (see step 6 above) |
| `rings do not fit on a flat hexagon grid` | Molecule isn't a flat fused-hexagon GQD |

**Usage**

```python
from Stage1.gqd_hex import hex_to_smiles, smiles_to_hex, HexError

hex_to_smiles([[0, 0], [1, 0]])       # 'c1ccc2ccccc2c1'  (naphthalene)
smiles_to_hex("c1ccc2ccccc2c1")       # [(0, 0), (1, 0)]  (position/orientation may differ)
```

**Where it is used:** `studio/agent.py` exposes it to the LLM as the tool `build_gqd_from_hexagons`. Its output goes through the five checks (molecular graph → uniqueness → ring count → sp² → SA score → save).

---

### `build_hex_dataset.py`: the dataset conversion script

**Reads (never modifies):**

| File | What it gives |
|---|---|
| `../../data/bigcsv/filtered.csv` | 91,174 GQDs: `Structure_Name`, `SMILES` |
| `../../GFN2-xTB _results/initial_5000_xtb_results.csv` | xTB HOMO / LUMO / gap (`mol_id = MOL_<n>`) |
| `../../GFN2-xTB _results/ML_xtb_11000_structures.csv` | xTB HOMO / LUMO / gap (`mol_id = MOL_<n>`) |

xTB IDs are matched to structures by number: `MOL_93122` ↔ `gqd_93122`.

**What it does for every structure:**

1. Reads the SMILES and makes it canonical.
2. Converts it to hexagons with `mol_to_hex`.
3. **Verifies** by converting the hexagons back with `hex_to_smiles` and comparing with the original SMILES. `hex_status = ok` only if they are identical.
4. Attaches xTB values if the structure has them.
5. Prints progress every 10,000 rows (about 3 minutes in total).

**Run it** (from `Agentic_GQD/`):

```bash
.venv/bin/python Stage1/build_hex_dataset.py
```

It overwrites `Stage1/data/gqd_hex_dataset.csv` each time.

**Output columns of `data/gqd_hex_dataset.csv`**

| Column | Meaning |
|---|---|
| `Structure_Name` | e.g. `gqd_93122` |
| `SMILES` | canonical SMILES |
| `n_hex` | number of hexagons |
| `hexagons` | JSON list, e.g. `[[0,0],[1,0],[0,1],...]` |
| `xtb_homo_eV`, `xtb_lumo_eV`, `xtb_gap_eV` | xTB values (blank if none) |
| `xtb_source` | `initial_5000` or `ml_11000` (blank if none) |
| `hex_status` | `ok`, `mismatch`, or `error` |
| `hex_error` | reason if not `ok` |

Read the hexagons back with `json.loads(row["hexagons"])`.

---

## Results (run on 2026-11-10)

| | |
|---|---|
| Structures converted | **91,174 / 91,174** (all `ok`, all verified) |
| Hexagons per structure | 20–40 |
| Structures with xTB gap | **14,674** (4,600 `initial_5000` + 10,074 `ml_11000`) |
| xTB gap range | **0.00–2.03 eV** |
| xTB IDs without SMILES | **1,326** (in `data/xtb_ids_without_smiles.txt`; probably removed when `filtered.csv` was made; no `.mol` files for them in the project) |

**Tests done:** 3,000 random hexagon clusters (1–45 rings) and 3,000 dataset structures converted both ways. No mismatches, and the output doesn't depend on hexagon order.

## How later stages use this

- **Stage 2:** the LLM writes hexagon lists → `build_gqd_from_hexagons` → five checks.
- **Stage 3:** the best xTB-labelled structures from `gqd_hex_dataset.csv` become the starting population; edits are applied to hexagon lists.
- **Stage 5 (fine-tuning):** `gqd_hex_dataset.csv` (gap + hexagons) is the source of **Dataset 3** ("target → structure"); see `../AGENTS.MD`.
