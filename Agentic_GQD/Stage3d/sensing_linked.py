# Created date: 2026-11-12 (America/Chicago)
"""Stage 3d, L2: NO2-sensing descriptors for linked-carbon designs (GFN2-xTB).

    from sensing_linked import evaluate_linked
    result = evaluate_linked({"units": ..., "place": ..., "links": ...})

Same workflow and the same output keys as Stage3a.sensing.evaluate_gqd, so that
Stage3a.sensing.sensing_numbers (the Stage 3a score) and Stage3c/twin.py twin(record) work on the
result unchanged. Reused from Stage 3a without change: run_xtb, gas_reference, place_gas, GASES,
ANALYTES, sensing_numbers. The geometry comes from Stage3d/linked.py build().

Adsorption sites (at most 4 per design):
  centre  the 6-ring nearest the middle of all 6-rings              (as Stage 3a)
  edge    the most exposed 6-ring: fewest fused neighbours, ties -> farthest from the middle (as Stage 3a)
  triple  above the midpoint of the C#C bond nearest the middle      (new; only if the design has links)
  pore    above the centre of the macrocycle (ring formed by links) nearest the middle (new; only if one exists)
With all five gases that is 6 gas orientations x sites = 12 (GQD-like), 18 (with links) or 24 (with a pore)
complexes. For each gas the strongest-binding site and orientation is kept, as in Stage 3a.
A design with one unit and no links is a plain GQD and gets exactly the Stage 3a sites.
"""

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from rdkit import Chem

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from linked import SIZE_RANGE, build, parse  # noqa: E402
from Stage1.gqd_hex import HEX_DIR, VERT_FNS  # noqa: E402
from Stage3a.sensing import ANALYTES, GASES, INTERFERENTS, gas_reference, place_gas, run_xtb, sensing_numbers  # noqa: E402

SITE_TYPE = {"centre": "ring", "edge": "ring", "triple": "triple", "pore": "pore"}


def six_rings(structure):
    """Carbon indices of every hexagon, in build()'s atom order, and each hexagon's number of fused neighbours.

    build() numbers the carbons unit by unit (in the order of "units"), and inside a unit in the order
    hexagons x VERT_FNS, exactly as below; link carbons come after all unit carbons.
    """
    units, _, _ = parse(structure)
    rings, n_neigh, offset = [], [], 0
    for cells in units.values():
        index, cell_set = {}, set(cells)
        for q, r in cells:
            ring = []
            for fn in VERT_FNS:
                ring.append(offset + index.setdefault(fn(q, r), len(index)))
            rings.append(ring)
            n_neigh.append(sum((q + dq, r + dr) in cell_set for dq, dr in HEX_DIR))
        offset += len(index)
    return rings, n_neigh


def adsorption_sites(structure, built, coords, extra_sites=True):
    """Site name -> list of atom indices (the gas is placed above their mean position)."""
    rings, n_neigh = six_rings(structure)
    centres = np.array([coords[ring].mean(axis=0) for ring in rings])
    middle = centres.mean(axis=0)
    dist = np.linalg.norm(centres - middle, axis=1)
    sites = {"centre": rings[int(np.argmin(dist))],
             "edge": rings[int(min(range(len(rings)), key=lambda i: (n_neigh[i], -dist[i])))]}
    if not extra_sites:
        return sites
    triples = [[b.GetBeginAtomIdx(), b.GetEndAtomIdx()] for b in built.mol.GetBonds()
               if b.GetBondType() == Chem.BondType.TRIPLE]
    if triples:
        sites["triple"] = min(triples, key=lambda pair: np.linalg.norm(coords[pair].mean(axis=0) - middle))
    pores = [list(r) for r in built.mol.GetRingInfo().AtomRings() if len(r) > 6]
    if pores:
        sites["pore"] = min(pores, key=lambda ring: np.linalg.norm(coords[ring].mean(axis=0) - middle))
    return sites


def evaluate_linked(design, analytes=None, threads=1, workers=6, keep_dir=None, size_range=SIZE_RANGE,
                    extra_sites=True, start_coords=None):
    """All adsorption calculations for one linked-carbon design. Returns a flat dict (Stage 3a keys + extras)."""
    analytes = list(ANALYTES) if analytes is None else list(analytes)
    if "NO2" not in analytes or not set(analytes) & set(INTERFERENTS):
        raise ValueError("analytes must include NO2 and at least one of " + ", ".join(INTERFERENTS))
    built = build(design, size_range=size_range, feedback=False)  # raises LinkError if invalid
    symbols, n_host = built.symbols, len(built.symbols)
    # start_coords: only for tests (e.g. the Stage 3a start geometry of the same GQD)
    host = run_xtb(symbols, built.coords if start_coords is None else start_coords, uhf=0, threads=threads * workers // 2 or 1,
                   keep_dir=None if keep_dir is None else Path(keep_dir) / "gqd")
    sites = adsorption_sites(design, built, host["coords"], extra_sites)

    jobs = [(analyte, gas, site) for analyte in analytes for gas in ANALYTES[analyte] for site in sites]
    refs = {gas: gas_reference(gas) for _, gas, _ in jobs}

    def one(job):
        analyte, gas, site = job
        gas_symbols, gas_coords = place_gas(host["coords"], sites[site], gas)
        res = run_xtb(symbols + gas_symbols, np.vstack([host["coords"], gas_coords]), uhf=GASES[gas][2],
                      threads=threads, keep_dir=None if keep_dir is None else Path(keep_dir) / f"{gas}_{site}")
        gas_xyz, host_xyz = res["coords"][n_host:], res["coords"][:n_host]
        d_min = float(np.min(np.linalg.norm(gas_xyz[:, None, :] - host_xyz[None, :, :], axis=2)))
        return {"analyte": analyte, "orientation": gas, "site": site, "site_type": SITE_TYPE[site],
                "E_ads_eV": res["energy_eV"] - host["energy_eV"] - refs[gas],
                "q_gas_e": float(np.sum(res["charges"][n_host:])), "gap_complex_eV": res["gap_eV"],
                "d_min_A": d_min, "converged": res["converged"]}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(one, jobs))

    centred = host["coords"] - host["coords"].mean(0)
    planarity = float(np.abs(centred @ np.linalg.svd(centred)[2][2]).max())
    rings, _ = six_rings(design)
    out = {"n_hex": len(rings), "n_atoms": n_host, "n_carbon": built.n_carbon, "formula": built.formula,
           "smiles": built.smiles, "n_units": built.info["n_units"], "n_links": built.info["n_links"],
           "n_triple_bonds": built.info["triple_bonds"], "has_pore": "pore" in sites,
           "gqd_gap_eV": host["gap_eV"], "gqd_max_out_of_plane_A": planarity, "analytes": ",".join(analytes),
           "sites": ",".join(sites), "gqd_converged": host["converged"],
           "all_converged": host["converged"] and all(r["converged"] for r in rows)}
    for analyte in analytes:
        best = min((r for r in rows if r["analyte"] == analyte), key=lambda r: r["E_ads_eV"])
        out[f"E_{analyte}_eV"] = best["E_ads_eV"]
        out[f"q_{analyte}_e"] = best["q_gas_e"]
        out[f"site_{analyte}"] = f"{best['site']}/{best['orientation']}"
        out[f"dmin_{analyte}_A"] = best["d_min_A"]
        if analyte == "NO2":
            out["gap_NO2_complex_eV"] = best["gap_complex_eV"]
    out.update(sensing_numbers(out))
    # extras: the strongest NO2 binding at each site type (ring / triple bond / pore)
    for kind in ("ring", "triple", "pore"):
        sub = [r for r in rows if r["analyte"] == "NO2" and r["site_type"] == kind]
        best = min(sub, key=lambda r: r["E_ads_eV"]) if sub else None
        out[f"E_NO2_{kind}_eV"] = best["E_ads_eV"] if best else float("nan")
        out[f"q_NO2_{kind}_e"] = best["q_gas_e"] if best else float("nan")
        out[f"dmin_NO2_{kind}_A"] = best["d_min_A"] if best else float("nan")
    out["details"] = rows
    return out
