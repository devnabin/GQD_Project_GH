<!-- Created date: 2026-11-12 (America/Chicago) -->

# Stage 3d (linked carbon), L1 progress log

Running log, newest at the bottom. Every number here comes from code that was run; outputs are copied, not retyped from memory.

## 2026-11-12 22:23 CST: start

- **Task:** L1 = representation + 3D builder + validity checks for linked carbon (decisions D16/D17 in `RESEARCH_OPTIONS.md`: linked carbon, fused units allowed). No scoring, no loop.
- **Read:** `Stage1/gqd_hex.py` (corner naming `VERT_FNS`, `_kekule_double_bonds`, `open_shell_feedback`, `HexError`) and `Stage3a/sensing.py` (hexagon geometry `_hex_centre`, `run_xtb`). Neither is modified; they are imported.
- **Measured** to choose a size limit: the 50 Stage 3a calibration GQDs have 20 to 37 hexagons, 64 to 118 carbons and 88 to 166 atoms including H.
- **Geometry facts** from the existing code:
  - hexagon centres are at `HEX_STEP*(q + r/2, sqrt(3)/2*r)`, with `HEX_STEP = sqrt(3)*1.42`, so neighbouring centres lie at 0°, 60°, ... 300°;
  - corners (mean of the three meeting hexagon centres) lie at −30°, 30°, 90°, 150°, 210° and 270° from the hexagon centre (pointy-top);
  - an edge carbon's C–H therefore points along one of those six vertex directions.

## 2026-11-12 22:27 CST: builder and tests written; all tests pass

Files: `Stage3d/linked.py` (representation, checks, builder) and `Stage3d/test_linked.py`. The full output is saved in `Stage3d/test_output.txt` (14 tests, 0 failures).

**Design choices** (alternatives not taken in brackets):

1. **Coarse grid = the hexagon grid rotated by 30°.** The six link directions are then 30°, 90°, ... 330°, which are exactly the directions edge C–H bonds point, so ring vertices face each other as in γ-graphyne. [Not taken: the unrotated grid, where link directions would point at ring edges, not atoms.]
2. **Attach carbon:** a link in direction θ uses the unit's outermost edge carbon whose C–H points along θ. Ties go to the carbon closest to the line through the unit centre. That atom loses its H. [Not taken: letting the LLM name the attach carbon, which needs atom labels the LLM would have to track.]
3. **Placement:** units are placed along a spanning tree of the links, so the coarse grid gives only neighbour relations and directions, not fixed positions. Units of any size fit, because each unit is shifted so the link has its ideal straight length. [Not taken: fixed coarse spacing, which cannot hold units of different sizes.]
   - A link that closes a ring must end within 15% of its ideal length and within 15° of its direction, or the structure is rejected.
   - This automatically rejects mixed link lengths around a ring, and rings whose units do not fit.
4. **Bond lengths** of the start geometry: ring C–C 1.42, sp2–sp 1.40, C≡C 1.21, sp–sp 1.35, C–H 1.09 Å. Link lengths between attach carbons are 4.01 Å (n=1) and 6.57 Å (n=2).
5. **Closed-shell rule:** each unit on its own must have a Kekulé structure. The open-shell message and fix edits are reused from Stage 1. Links add triple bonds between sp carbons and do not change the pairing.
6. **Size limit:** 40 to 150 carbon atoms, against 64 to 118 carbons in the current GQDs (measured above). It allows the extra link carbons while keeping DFT size near the current benchmark (up to about 170 atoms). Tests of small molecules switch the limit off.
7. **Clash check:** atoms of different parts (units, links) must be at least 1.6 Å apart. It is not applied inside a unit, where the start geometry is the same as Stage 3a.
8. **Start-geometry noise:** out-of-plane noise with σ = 0.05 Å, seeded by CRC32 of the canonical SMILES. Python's `hash()` of a string changes between runs, so it is not used.

**Test results:**
- Known molecules match RDKit's canonical SMILES and formula:
  - diphenylacetylene `C(#Cc1ccccc1)c1ccccc1` (C14H10);
  - diphenylbutadiyne `C(C#Cc1ccccc1)#Cc1ccccc1` (C16H10).
- Benzene triangle:
  - n=1 gives C24H12, with rings [6, 6, 6, 12];
  - n=2 gives C30H12, with rings [6, 6, 6, 18];
  - the ring-closing link B–C is exactly at its ideal length (4.01 and 6.57 Å, 0° off).
- Naphthalene unit + benzene: C18H12, one triple bond.
- Coronene unit + two benzenes (n=2): C44H20, accepted with the default size limit.
- All 8 invalid inputs are rejected, each with its own message:
  - non-neighbour units;
  - n=3;
  - an unlinked unit;
  - two units in one place;
  - an open-shell (phenalenyl) unit, with the Stage 1 fix feedback;
  - mixed link lengths around a ring;
  - too small;
  - overlapping parts.

**Problems found and fixed:**
1. numpy's `cross` refuses 2D vectors, so a scalar 2D cross product is written out instead.
2. My first overlap test (three 4-ring rows) was in fact a valid structure; its parts were 4.01 Å apart. The code was right and the test was wrong.
   - A search over small designs found a real overlap (benzene, benzene, and a 4-ring row above A reaching over B; 0.30 Å), and that is now the test.
3. That test was first rejected by the size check instead of the overlap check. The size check now runs last, so structural errors get their own message.

## 2026-11-12 22:27 CST: xTB check of three built structures

`Stage3d/xtb_check.py` runs GFN2-xTB (`--opt --gfn 2`, 4 threads, conda-forge xtb via `Stage3a.sensing.run_xtb`). Optimised geometries are in `Stage3d/results/*.xyz` and the table in `Stage3d/results/xtb_check.md`. All three finished in 2.6 s of wall time. Output, copied:

```
triangle_n1: C24H12, converged True, gap 2.188 eV; start C#C 1.210-1.219; opt C#C 1.208-1.208, sp angles 179.6-179.9, ring C-C 1.383-1.410, out-of-plane 0.02
triangle_n2: C30H12, converged True, gap 2.416 eV; start C#C 1.210-1.212; opt C#C 1.215-1.215, sp angles 179.0-179.6, ring C-C 1.380-1.413, out-of-plane 0.01
coronene_2benz_n2: C44H20, converged True, gap 2.052 eV; start C#C 1.210-1.225; opt C#C 1.214-1.215, sp angles 179.4-179.7, ring C-C 1.362-1.431, out-of-plane 0.05
```

The start geometries are good enough for xTB:
- every optimisation converged;
- triple bonds stay at about 1.21 Å and nearly linear;
- 6-ring bonds stay aromatic (1.36 to 1.43 Å);
- the structures stay flat (out-of-plane span 0.01 to 0.05 Å).

The start C≡C range of up to 1.225 Å comes from the out-of-plane noise. The gaps above are GFN2-xTB HOMO-LUMO gaps; nothing here is checked against DFT.

## 2026-11-12 22:28 CST: L1 finished

Wrote `Stage3d/README.md`, added D20 to `RESEARCH_OPTIONS.md` and added an entry to `SESSION_LOG.md`. Nothing outside `Stage3d/`, `RESEARCH_OPTIONS.md` and `SESSION_LOG.md` was changed, and nothing was committed.

## 2026-11-12 22:44 CST: L2 started. `sensing_linked.py` written

- `evaluate_linked(design, analytes, threads, workers, keep_dir)` uses `Stage3d/linked.py build()` for the geometry.
- It reuses these unchanged from `Stage3a/sensing.py`: `run_xtb`, `gas_reference`, `place_gas`, `GASES`, `ANALYTES`, `sensing_numbers`. `Stage3a/sensing.py` was not modified, and no Stage 3a helper was copied.
- The output keys are the same as `evaluate_gqd`, plus extras:
  - `smiles`, `formula`, `n_carbon`, `n_units`, `n_links`, `n_triple_bonds`, `has_pore`, `sites`;
  - the best NO₂ result per site type (`E_NO2_ring/triple/pore_eV`, plus `q_` and `dmin_`).
- Sites: `centre` and `edge` (6-rings, Stage 3a rules); `triple` (the C≡C nearest the middle, if the design has links); `pore` (the macrocycle ring of more than 6 atoms nearest the middle, if one exists).
- Complexes per design with all 5 gases: 12 (one unit), 18 (links, no pore) or 24 (with a pore).
- 6-ring atom indices are rebuilt in `build()`'s atom order (unit by unit, hexagons × `VERT_FNS`). A test option `start_coords` lets a test start from a given geometry.

## 2026-11-12 22:45 and 2026-11-13 10:58 CST: consistency test (`consistency_test.py`, results/consistency_test*.csv)

Two calibration GQDs with 20 hexagons: `gqd_34862` (physisorbs NO₂) and `gqd_03389` (chemisorbs). Each is evaluated as a one-unit design without links, using ring sites only and all 5 gases.

**Run 1, the linked builder's own start geometry** (jitter seeded by the SMILES). Output, copied:

| GQD | gap diff (eV) | E_NO2 diff | q_NO2 diff | E_CO diff | E_H2O diff | E_NH3 diff | E_O2 diff | NO₂ site | score |
|---|---|---|---|---|---|---|---|---|---|
| gqd_34862 | +0.013 | −0.007 | −0.021 | +0.029 | +0.036 | +0.007 | −0.243 | stage3a edge, linked centre | 0.2048 → 0.2264 |
| gqd_03389 | +0.078 | +0.053 | −0.005 | +0.087 | +0.017 | +0.070 | +0.059 | centre, centre | 0 → 0 |

**Run 2, Stage 3a's own start geometry** (same lattice; jitter seeded by the hash of the hexagon list, as in `evaluate_gqd`; `--same-start`). Output, copied:

- gqd_34862: gap +0.0000; E_NO2 −0.0001; q_NO2 +0.0002; E_CO +0.0001; E_H2O +0.0002; E_NH3 −0.0000; E_O2 −0.0000; site edge = edge; score 0.2048 vs 0.2049.
- gqd_03389: gap −0.0000; E_NO2 −0.0001; q_NO2 +0.0002; E_CO +0.0002; E_H2O −0.0001; E_NH3 +0.0003; E_O2 −0.0001; site centre = centre; score 0 = 0.

The carbon/hydrogen positions of the two builders are identical before the noise (largest xy difference about 1e-15 Å, checked separately).

**Verdict:** the code is consistent. With the same start, every difference is 0.0003 eV or less (xTB convergence level).
- Run 1's larger differences come only from the different random out-of-plane noise.
- Both GQDs are strongly twisted (Stage 3a out-of-plane 3.1 and 4.5 Å). A different start noise lets xTB settle in a different twisted conformer, which moves the GQD gap by up to 0.08 eV and the adsorption energies by up to 0.09 eV (0.24 eV for O₂). For gqd_34862 it even moved the best NO₂ site from edge to centre.
- This is **conformer noise, not a bug**, and Stage 3a has the same noise; it was simply never measured before. It means differences below about 0.05 to 0.1 eV between twisted structures are not meaningful.
- Decision: keep the SMILES-seeded noise in `linked.py`. A structure always gets the same start; no change needed.
- Recorded as a limitation for both Stage 3a and Stage 3d (README).
## 2026-11-13 11:00 CST: calibration set started

- 21 of 23 hand-made designs in `designs.py` build. `pyrene_tri3_n2` and `coronene_tri3_n1` are rejected by L1's ring-closure check, because the unit sizes do not fit the triangle.
- Running `calibrate_linked.py` detached: 2 designs at a time × 6 single-thread xTB jobs = 12, all 5 gases.
- Results go to `results/calibration_linked.jsonl`, the log to `results/calibration_run.log`, and geometries to `data/geometries/`.

## 2026-11-13 11:07 CST: calibration set finished

- All 21 designs finished and every optimisation converged.
- Total xTB time was 761 s summed over designs (12 to 117 s each; 2 designs in parallel × 6 jobs). Each design's line from `results/calibration_run.log` is in `results/summary.md`.
- Sites per design: 3 (centre, edge, triple) for designs with links and no pore, plus a pore site for the 9 designs with macrocycles. That gives 18 or 24 complexes with all 5 gases.

## 2026-11-13 11:08 CST: analysis (`analyze_linked.py`)

Outputs: `results/calibration_linked.csv`, `results/calibration_linked_sites.csv` (the best NO₂ binding at every site), `results/summary.md` and `results/linked_vs_fused.png` (I read the PNG; it is readable).

Linked (21) vs the fused Stage 3a calibration GQDs (50), same xTB protocol. Numbers copied from `summary.md`:

| | fused | linked |
|---|---|---|
| gap median (eV) | 1.02 | 1.99 |
| strongest E_NO2 median (eV) | −0.642 | −0.967 |
| NO₂ chemisorbed | 29/50 | 19/21 |
| q_NO2 median (e) | −0.212 | −0.228 |
| strongest interferent | CO 50 | CO 20, H2O 1 |
| NO₂ over CO margin median (eV) | 0.384 | 0.756 |
| Stage 3a score > 0 | 38 | 14 |
| score median / max | 0.142 / 0.322 | 0.020 / 0.197 |
| meet the twin's 5-min recovery | 32 | 5 |

NO₂ by site type (best orientation at each site, 72 sites):

| site | n | E_NO2 median | min | max | chemisorbed |
|---|---|---|---|---|---|
| ring | 42 | −0.232 | −0.973 | −0.168 | 11 |
| triple | 21 | −0.951 | −1.19 | −0.192 | 15 |
| pore | 9 | −0.261 | −1.03 | −0.015 | 2 |

- **The triple bond is the reactive site.** 15 of 21 triple-bond sites chemisorb NO₂, at a median of −0.95 eV (xTB). In 15 of the 21 designs the strongest NO₂ site is a triple bond.
- **Pores bind NO₂ weakly.** The median is −0.26 eV.
  - The 2 "pore" sites that chemisorb are `gy_hex7` and `gy_rhomb9`. Their d_min is 1.47 to 1.48 Å, i.e. the NO₂ that started above the pore ended up bonded to a nearby carbon. A site label means where the gas started.
- **Stage 3a score:** linked designs score lower than fused GQDs (best 0.197 for `gy_ring6`, against 0.322). The cause is too-strong binding, which is penalised by the reversibility factor.
- **Twin:** 5 of 21 designs recover within 5 min. The best are `naph_row4_n1` (−0.77 eV at a naphthalene ring, recovery 11 s, response 0.115 e per site) and `pyrene_row3_n1` (−0.74 eV, 3.6 s, 0.063).
  - For comparison, the best fused GQD in the Stage 3c twin is `gqd_83340`, at 0.205.
  - Both best designs bind NO₂ at a ring of a fused unit, not at a triple bond.
- Two physisorbing designs (`gy_row6`, `gy_tri6`) have a small NO₂ over CO margin (0.07 and 0.06 eV), so their selectivity factor is below 1.
- xTB E_O₂ ranges from −2.56 to −0.55 eV (not scored; xTB is known to be wrong for O₂).

**Caveats:**
- These are xTB energies. On rings xTB overbinds chemisorbed NO₂ by 0.1 to 0.55 eV (Stage 3a DFT check); triple-bond chemisorption has **not** been checked with DFT.
- The humidity-equivalent NO₂ hits the lower bound of the twin's bisection (1e-6 ppb) for 15 of 21 designs. It means "negligible" there, not a measured 1e-6.

## 2026-11-13 11:10 CST: DFT input bundle prepared (nothing run on the server)

- `prepare_dft.py gdy_rhomb4 naph_row4_n1` copies the kept xTB geometries plus `xtb.json` and the Stage 3a gas references into `Stage3d/data/dft_check/` (2.1 MB in total for `Stage3d/data`).
- Why these two:
  - `gdy_rhomb4` (C44H14) is the smallest design with triple-bond chemisorption (−0.985 eV); it tests xTB on the new site type;
  - `naph_row4_n1` is the best design by the twin (ring site, −0.77 eV).
- A local dry run of `Stage3a/dft_gpu.py`'s `tasks()` plans **50 SCFs** (6 gas refs, 2 hosts, 42 complexes), and `summarise()` runs on an empty cache.
- The command for the server is in the README; not run.
## 2026-11-13 11:09 CST: L2 finished

- Wrote the README L2 section, `RESEARCH_OPTIONS.md` D21 and a `SESSION_LOG.md` entry.
- Nothing was changed outside `Stage3d/`, `RESEARCH_OPTIONS.md` and `SESSION_LOG.md`.
- No server use, no commit.
