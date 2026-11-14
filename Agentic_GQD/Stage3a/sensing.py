# Created date: 2026-11-12 (America/Chicago)
"""NO2 gas-sensing descriptors for a GQD, computed with xTB (GFN2).

    from Stage3a.sensing import evaluate_gqd
    result = evaluate_gqd([[0, 0], [1, 0], ...])     # hexagon list

For one GQD this:
  1. builds a flat GQD geometry directly from the hexagon grid (C-C 1.42 A, C-H 1.09 A),
  2. optimises it with xTB,
  3. places each gas (NO2, H2O, NH3, CO, O2) 3.1 A above two hexagons (the most
     central one and the most exposed edge one), optimises every complex, and
  4. returns adsorption energies, charge transfer and the derived sensing numbers.

E_ads = E(GQD+gas) - E(GQD) - E(gas)   (eV, negative = binds)
q_gas = sum of xTB partial charges on the gas atoms in the complex (e, negative =
        the gas took electrons from the GQD, which is how NO2 changes conductance)
"""

import math
import os
import re
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
import sys  # noqa: E402

sys.path.insert(0, str(HERE.parent))
from Stage1.gqd_hex import VERT_FNS, check_hexagons, hex_to_mol  # noqa: E402

HARTREE_EV = 27.211386
KT_EV = 0.025693  # 298.15 K
ATTEMPT_FREQ = 1e12  # 1/s, for the desorption (recovery) time

# The Homebrew xtb 6.7.1 crashes (gfortran format bug); the conda-forge build works.
_DEFAULT_XTB = HERE.parent.parent / "AI_GQD" / ".env" / "bin" / "xtb"
XTB = os.environ.get("XTB_BIN", str(_DEFAULT_XTB) if _DEFAULT_XTB.exists() else "xtb")

CC, CH = 1.42, 1.09
HEX_STEP = math.sqrt(3) * CC  # distance between neighbouring hexagon centres
HEIGHT = 3.1  # start height of the lowest gas atom above the GQD plane (A)
JITTER_A = 0.05  # out-of-plane noise on the starting GQD geometry (A)

# Gas molecules: atoms, starting coordinates (lowest atom at z=0, z points away
# from the GQD), and number of unpaired electrons (xTB --uhf).
GASES = {
    "NO2": (["N", "O", "O"], [[0, 0, 0], [1.105, 0, 0.469], [-1.105, 0, 0.469]], 1),      # N down
    "NO2_O": (["O", "N", "O"], [[0, 0, 0], [1.105, 0, 0.469], [2.21, 0, 0]], 1),          # O down
    "H2O": (["O", "H", "H"], [[0, 0, 0.586], [0.757, 0, 0], [-0.757, 0, 0]], 0),          # H down
    "NH3": (["N", "H", "H", "H"], [[0, 0, 0.38], [0.94, 0, 0], [-0.47, 0.81, 0], [-0.47, -0.81, 0]], 0),
    "CO": (["C", "O"], [[0, 0, 0], [0, 0, 1.128]], 0),                                  # C down
    "O2": (["O", "O"], [[0.605, 0, 0], [-0.605, 0, 0]], 2),                              # flat, triplet
}
# Which starting orientations count for each analyte (the best one is kept).
ANALYTES = {"NO2": ["NO2", "NO2_O"], "H2O": ["H2O"], "NH3": ["NH3"], "CO": ["CO"], "O2": ["O2"]}
# O2 is computed but NOT used in the score: on tetracene, GFN2-xTB binds O2 by
# -1.1 to -1.5 eV while DFT (wB97X-V) finds it unbound (+0.5 to +1.1 eV).
INTERFERENTS = ["H2O", "NH3", "CO"]
# Cheaper set for the evolution loop: CO was the strongest interferent for all 50
# calibration GQDs (0.06-0.1 eV above H2O/NH3), so children are scored on NO2 + CO and
# only the final candidates get H2O, NH3 and O2.
LOOP_ANALYTES = ["NO2", "CO"]
BOND_A = 1.9  # gas-GQD contact shorter than this = a covalent bond formed (chemisorption)

# Sensing score = response x reversibility x selectivity   (see README "The sensing score")
#   response      charge moved to NO2 (e). Matches DFT when chemisorbed; when physisorbed
#                 xTB inflates it (coronene: 0.04-0.13 e vs DFT <=0.04 e) but it tracks the
#                 GQD HOMO (r = 0.88), so it is used as a ranking, not as a real number.
#   reversibility 1 if E_NO2 >= E_SOFT, falls linearly to 0 at E_HARD. xTB overbinds
#                 chemisorbed NO2 by ~0.1-0.55 eV vs DFT, so E_HARD = -1.0 eV (xTB)
#                 is roughly -0.5 to -0.9 eV in DFT, i.e. recovery of ~0.3 ms to ~30 min.
#   selectivity   1 if NO2 binds at least SEL_MARGIN more strongly than H2O, NH3, CO
E_SOFT, E_HARD, SEL_MARGIN = -0.6, -1.0, 0.10


class XtbError(RuntimeError):
    pass


# ----------------------------------------------------------------------------
# Geometry from the hexagon grid
# ----------------------------------------------------------------------------
def _hex_centre(q, r):
    return np.array([HEX_STEP * (q + r / 2), HEX_STEP * (math.sqrt(3) / 2) * r, 0.0])


def gqd_geometry(hexagons):
    """Flat C/H geometry for a hexagon list. Returns (symbols, coords, rings).

    rings[i] lists the carbon indices of hexagon i (same order as `hexagons`).
    A carbon (a corner shared by up to 3 hexagons) sits at the mean of the
    centres of the 3 hexagons that meet there, so the lattice is exact.
    """
    cells = check_hexagons(hexagons)
    corner_index, corner_pos, rings = {}, [], []
    for q, r in cells:
        ring = []
        for fn in VERT_FNS:
            key = fn(q, r)
            if key not in corner_index:
                corner_index[key] = len(corner_pos)
                corner_pos.append(np.mean([_hex_centre(*h) for h in key], axis=0))
            ring.append(corner_index[key])
        rings.append(ring)
    carbons = np.array(corner_pos)
    neighbours = {i: set() for i in range(len(carbons))}
    for ring in rings:
        for k in range(6):
            a, b = ring[k], ring[(k + 1) % 6]
            neighbours[a].add(b)
            neighbours[b].add(a)
    hydrogens = []
    for i, nb in neighbours.items():
        if len(nb) == 2:  # edge carbon: one H, pointing away from its two neighbours
            out = carbons[i] - carbons[list(nb)].mean(axis=0)
            hydrogens.append(carbons[i] + CH * out / np.linalg.norm(out))
    symbols = ["C"] * len(carbons) + ["H"] * len(hydrogens)
    return symbols, np.vstack([carbons, hydrogens]), rings


def adsorption_sites(hexagons, rings, coords):
    """Two sites: the hexagon nearest the centre, and the most exposed edge hexagon."""
    cells = [tuple(h) for h in hexagons]
    cell_set = set(cells)
    centres = np.array([coords[ring].mean(axis=0) for ring in rings])
    middle = centres.mean(axis=0)
    dist = np.linalg.norm(centres - middle, axis=1)
    n_neigh = [sum((q + dq, r + dr) in cell_set for dq, dr in
                   [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]) for q, r in cells]
    centre_site = int(np.argmin(dist))
    # most exposed = fewest neighbours, ties broken by distance from the middle
    edge_site = int(min(range(len(cells)), key=lambda i: (n_neigh[i], -dist[i])))
    return {"centre": centre_site, "edge": edge_site}


def place_gas(gqd_coords, ring_atoms, gas):
    """Coordinates of `gas` above the centre of one hexagon of an optimised GQD."""
    symbols, local, _ = GASES[gas]
    local = np.array(local, dtype=float)
    plane_centre = gqd_coords.mean(axis=0)
    normal = np.linalg.svd(gqd_coords - plane_centre)[2][2]
    site = gqd_coords[ring_atoms].mean(axis=0)
    # in-plane axes: x along a C-C direction of that ring, y = normal x x
    x_axis = gqd_coords[ring_atoms[0]] - site
    x_axis -= normal * (x_axis @ normal)
    x_axis /= np.linalg.norm(x_axis)
    y_axis = np.cross(normal, x_axis)
    local[:, :2] -= local[:, :2].mean(axis=0)  # centre the gas over the ring
    placed = site + HEIGHT * normal + local @ np.vstack([x_axis, y_axis, normal])
    return symbols, placed


# ----------------------------------------------------------------------------
# xTB
# ----------------------------------------------------------------------------
def _write_xyz(path, symbols, coords):
    lines = [str(len(symbols)), ""] + [f"{s} {x:.6f} {y:.6f} {z:.6f}" for s, (x, y, z) in zip(symbols, coords)]
    Path(path).write_text("\n".join(lines) + "\n")


def _read_xyz(path):
    lines = Path(path).read_text().splitlines()
    n = int(lines[0])
    rows = [line.split() for line in lines[2:2 + n]]
    return [r[0] for r in rows], np.array([[float(v) for v in r[1:4]] for r in rows])


def run_xtb(symbols, coords, uhf=0, threads=2, keep_dir=None):
    """Optimise with GFN2-xTB. Returns dict(energy_eV, gap_eV, coords, charges, converged)."""
    work = Path(tempfile.mkdtemp(prefix="xtb_"))
    try:
        _write_xyz(work / "in.xyz", symbols, coords)
        env = {**os.environ, "OMP_NUM_THREADS": str(threads), "OMP_STACKSIZE": "1G"}
        proc = subprocess.run([XTB, "in.xyz", "--opt", "--gfn", "2", "--uhf", str(uhf), "--chrg", "0"],
                              cwd=work, capture_output=True, text=True, errors="replace", env=env, timeout=3600)
        out = proc.stdout
        energies = re.findall(r"TOTAL ENERGY\s+(-?\d+\.\d+)", out)
        gaps = re.findall(r"HOMO-LUMO GAP\s+(-?\d+\.\d+)", out)
        if not energies or not (work / "xtbopt.xyz").exists():
            raise XtbError(f"xtb failed (exit {proc.returncode}): {(proc.stderr or out)[-400:]}")
        _, opt = _read_xyz(work / "xtbopt.xyz")
        charges = np.loadtxt(work / "charges") if (work / "charges").exists() else np.full(len(symbols), np.nan)
        result = {"energy_eV": float(energies[-1]) * HARTREE_EV, "gap_eV": float(gaps[-1]) if gaps else np.nan,
                  "coords": opt, "charges": np.atleast_1d(charges),
                  "converged": "GEOMETRY OPTIMIZATION CONVERGED" in out and not (work / "NOT_CONVERGED").exists()}
        if keep_dir is not None:
            Path(keep_dir).mkdir(parents=True, exist_ok=True)
            _write_xyz(Path(keep_dir) / "xtbopt.xyz", symbols, opt)
        return result
    finally:
        shutil.rmtree(work, ignore_errors=True)


@lru_cache(maxsize=None)
def gas_reference(gas):
    """Optimised energy of an isolated gas molecule (cached)."""
    symbols, coords, uhf = GASES[gas]
    return run_xtb(symbols, np.array(coords, dtype=float), uhf=uhf, threads=1)["energy_eV"]


# ----------------------------------------------------------------------------
# One GQD
# ----------------------------------------------------------------------------
def evaluate_gqd(hexagons, threads=2, workers=6, keep_dir=None, analytes=None):
    """All adsorption calculations for one GQD. Returns a flat dict of descriptors.

    analytes: which gases to compute (default all of ANALYTES; must include NO2).
    """
    analytes = list(ANALYTES) if analytes is None else list(analytes)
    if "NO2" not in analytes or not set(analytes) & set(INTERFERENTS):
        raise ValueError("analytes must include NO2 and at least one of " + ", ".join(INTERFERENTS))
    hexagons = [tuple(h) for h in check_hexagons(hexagons)]
    hex_to_mol(hexagons, feedback=False, size_range=(1, 10_000))  # must be a valid closed-shell GQD
    symbols, coords, rings = gqd_geometry(hexagons)
    # A perfectly flat start has no out-of-plane force, so a GQD with crowded
    # edges (coves/fjords) stays stuck in its strained flat form, and the twist
    # released later in a complex is wrongly counted as binding. A tiny
    # reproducible out-of-plane nudge lets it relax to its true shape.
    rng = np.random.default_rng(abs(hash(tuple(sorted(hexagons)))) % 2**32)
    coords = coords + np.column_stack([np.zeros((len(coords), 2)), rng.normal(0, JITTER_A, len(coords))])
    n_gqd = len(symbols)
    gqd = run_xtb(symbols, coords, uhf=0, threads=threads * workers // 2 or 1,
                  keep_dir=None if keep_dir is None else Path(keep_dir) / "gqd")
    sites = adsorption_sites(hexagons, rings, gqd["coords"])

    jobs = [(analyte, gas, site) for analyte in analytes for gas in ANALYTES[analyte] for site in sites]
    refs = {gas: gas_reference(gas) for _, gas, _ in jobs}

    def one(job):
        analyte, gas, site = job
        gas_symbols, gas_coords = place_gas(gqd["coords"], rings[sites[site]], gas)
        res = run_xtb(symbols + gas_symbols, np.vstack([gqd["coords"], gas_coords]), uhf=GASES[gas][2],
                      threads=threads,
                      keep_dir=None if keep_dir is None else Path(keep_dir) / f"{gas}_{site}")
        gas_xyz, gqd_xyz = res["coords"][n_gqd:], res["coords"][:n_gqd]
        d_min = float(np.min(np.linalg.norm(gas_xyz[:, None, :] - gqd_xyz[None, :, :], axis=2)))
        return {"analyte": analyte, "orientation": gas, "site": site,
                "E_ads_eV": res["energy_eV"] - gqd["energy_eV"] - refs[gas],
                "q_gas_e": float(np.sum(res["charges"][n_gqd:])), "gap_complex_eV": res["gap_eV"],
                "d_min_A": d_min, "converged": res["converged"]}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(one, jobs))

    centred = gqd["coords"] - gqd["coords"].mean(0)
    planarity = float(np.abs(centred @ np.linalg.svd(centred)[2][2]).max())
    out = {"n_hex": len(hexagons), "n_atoms": n_gqd, "gqd_gap_eV": gqd["gap_eV"],
           "gqd_max_out_of_plane_A": planarity, "analytes": ",".join(analytes),
           "site_cells": {name: list(hexagons[i]) for name, i in sites.items()},
           "gqd_converged": gqd["converged"], "all_converged": gqd["converged"] and all(r["converged"] for r in rows)}
    for analyte in analytes:
        best = min((r for r in rows if r["analyte"] == analyte), key=lambda r: r["E_ads_eV"])
        out[f"E_{analyte}_eV"] = best["E_ads_eV"]
        out[f"q_{analyte}_e"] = best["q_gas_e"]
        out[f"site_{analyte}"] = f"{best['site']}/{best['orientation']}"
        out[f"dmin_{analyte}_A"] = best["d_min_A"]
        if analyte == "NO2":
            out["gap_NO2_complex_eV"] = best["gap_complex_eV"]
    out.update(sensing_numbers(out))
    out["details"] = rows
    return out


def sensing_numbers(d):
    """Selectivity, recovery time and the NO2 sensing score from the raw descriptors.

    Uses whichever interferents were computed (all three, or only CO in the evolution loop).
    """
    present = [g for g in INTERFERENTS if _is_number(d.get(f"E_{g}_eV"))]
    strongest = min(present, key=lambda g: d[f"E_{g}_eV"])
    margin = d[f"E_{strongest}_eV"] - d["E_NO2_eV"]  # > 0: NO2 binds more strongly than any interferent
    response = -d["q_NO2_e"]
    reversibility = float(np.clip((d["E_NO2_eV"] - E_HARD) / (E_SOFT - E_HARD), 0, 1))
    selectivity = float(np.clip(margin / SEL_MARGIN, 0, 1))
    return {"strongest_interferent": strongest, "interferents_checked": ",".join(present),
            "selectivity_margin_eV": margin,
            "humidity_margin_eV": d["E_H2O_eV"] - d["E_NO2_eV"] if "H2O" in present else float("nan"),
            "NO2_chemisorbed": bool(d["dmin_NO2_A"] < BOND_A),
            "recovery_time_s": math.exp(-d["E_NO2_eV"] / KT_EV) / ATTEMPT_FREQ,
            "charge_to_NO2_e": response, "reversibility": reversibility, "selectivity": selectivity,
            "sensing_score": response * reversibility * selectivity}


def _is_number(value):
    return value is not None and not (isinstance(value, float) and math.isnan(value))
