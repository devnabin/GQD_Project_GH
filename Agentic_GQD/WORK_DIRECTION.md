<!-- Created date: 2026-11-10 (America/Chicago) -->

# Work Direction

> Start here when resuming work. Latest session notes: `SESSION_LOG.md` (top entry). Full details: `Final_Planning.md`. Fine-tuning data plan: `AGENTS.MD`.
> Each stage has its own folder (`Stage1/`, `Stage2/`, …) with a `README.md` and its files.
> Update the **Status** column and **Next steps** whenever a stage moves forward.
> Thesis draft: `Report/main.tex`, updated after every new result (rule at the top of `AGENTS.MD`).
> Every fork we faced, with the options not taken: `RESEARCH_OPTIONS.md`.
> Planned agent prototype (diagrams and status): `SYSTEM_ARCHITECTURE.md`.

## Goal

Build an AI agent that designs new graphene quantum dots (GQDs) and improves them for **one application: NO₂ gas sensing** (decided 2026-11-12). The goal comes from the application (strong response, reversible, selective), not from a gap chosen by hand. **The LLM decides what to try, and code decides what's valid and good.**

## Method

LLM-guided evolution on a hexagon grid (Option 2 + Option 5).

- The LLM describes a GQD as **hexagon positions**, not SMILES.
- The LLM suggests **edits** to the best structures (add, remove, move, merge hexagons).
- Code builds the molecule (`cluster_to_mol`), checks it with the **five validation steps**, and scores it (**ML predictor**, then **xTB** for the best).
- This repeats for many generations, and every step is **logged**.

## Roadmap

| Stage | What | Status |
|---|---|---|
| **0. Foundation** | LangGraph agent, software check, five-step validation, save | ✅ Done |
| **1. Hexagon → molecule** | `hex_to_mol` tool (from `cluster_to_mol`) + `mol_to_hex` for existing data | ✅ Done (2026-11-10) |
| **2. Fast gap predictor** | ML predictor of the xTB gap + uncertainty, for scoring in the loop | ✅ Done (2026-11-10) |
| **2d. LLM writes hexagons** | LLM proposes hexagon lists; measure how many pass validation | ✅ Done (2026-11-11) |
| **3a. NO₂ sensing score** | xTB workflow: GQD + NO₂/H₂O/NH₃/CO/O₂ → binding, charge transfer → sensing score; DFT check of xTB | ✅ Done (2026-11-12) |
| **3b. Beyond pure carbon** | LLM also places N/B dopants and edge groups (–OH, –COOH, –NH₂) | Later (after 3) |
| **3. Evolution loop** | score (NO₂ sensing) → select → LLM edits → validate → log → repeat | ✅ Built; pilot done (2026-11-12): LLM 0.340 vs random 0.331 (1 seed, not significant). v2 fixes applied: open-shell repair, family cap 3, gap floor 0.20 eV, 4 LLM rounds |
| **4. Experiments** | Random vs. random mutation vs. LLM-guided, same xTB budget | 🔄 LLM vs random mutation done (2026-11-12, 3 seeds each): best score random 0.351 ± 0.008 vs LLM 0.344 ± 0.004 (no LLM advantage); mean scored LLM 0.186 vs random 0.163 (LLM higher in all 3 pairs). Still to do: GPU DFT benchmark (running), random-generation baseline (E6) |
| **3c. Sensor twin** | Coverage at real concentrations → signal, recovery time, humidity effect (`Stage3c/`) | ✅ v1 (2026-11-12) |
| **3d. Linked carbon** | Graphyne-type units joined by C≡C links; builder, checks, NO₂ scoring (`Stage3d/`) | ✅ L1 and L2 done (2026-11-13); DFT shows triple-bond binding overestimated by xTB |
| **4b. DFT-validated search** | Score v2, N_FOD open-shell filter, DFT of closed-shell candidates, new search runs (`Stage4/`) | 🔄 Running on the server (started 2026-11-13) |
| **5. Fine-tuning** | Build Datasets 1–3 from logs + ~16k xTB data, fine-tune a small open model with LoRA, test it in the same loop | Later |
| **6. Option 6** | SELFIES or graph generative models as an extra comparison | Future work |

## Expected research results

1. **Main result:** LLM-guided evolution finds better GQDs with **fewer xTB runs** than random search.
2. **What helps:** measure which context improves the LLM: coordinates only → + computed properties → + history → + similar structures from our data.
3. **Second result:** a **fine-tuned small model** beats the general LLM in the same loop.

## Rules we follow throughout

- **The LLM suggests; code and xTB decide.** Nothing is accepted without passing the five checks.
- **Log everything** (the fields listed in `AGENTS.MD`), because the logs are the fine-tuning data.
- **Compare fairly:** same xTB budget, several random seeds, and test targets the model wasn't trained on.
- **Check the literature first** (MolLEO, COMPAS, LLM + genetic algorithms) before claiming novelty.

## Stage 1 results (2026-11-10)

All Stage 1 files are in `Stage1/` (see `Stage1/README.md`).

- `Stage1/gqd_hex.py`: `hex_to_mol` / `mol_to_hex` / `hex_to_smiles` / `smiles_to_hex`.
  - `hex_to_mol` picks the double bonds itself (perfect matching), because RDKit's kekulizer fails on some large fused systems depending on atom order.
  - Rejects with a clear `HexError`: duplicates, disconnected hexagons, open-shell shapes (no Kekulé form), and valid shapes whose SMILES RDKit cannot re-read (RDKit kekulization limit; ~10% of random 20–40 ring shapes).
  - A one-hexagon hole is the same molecule as a filled hexagon, so `mol_to_hex` returns it filled.
- `Stage1/build_hex_dataset.py` → `Stage1/data/gqd_hex_dataset.csv`: **91,174 / 91,174** structures converted and round-trip verified; 20–40 hexagons each.
  - **14,674** rows have xTB HOMO/LUMO/gap (4,600 from `initial_5000`, 10,074 from `ml_11000`). xTB gap range in the data: **0.00–2.03 eV**.
  - **1,326** xTB-labelled IDs have no SMILES in `filtered.csv` (listed in `Stage1/data/xtb_ids_without_smiles.txt`); they cannot be used unless their structures are recovered.
- `studio/agent.py`: new tool `build_gqd_from_hexagons` → the same five checks. Bad hexagon lists come back to the LLM as error messages; one tool call per turn.

## Stage 2 results (2026-11-10)

All Stage 2 files are in `Stage2/` (see `Stage2/README.md`).

- `Stage2/predictor.py` → `GapPredictor().predict(hexagons=... | smiles=...)` returns gap_pred_eV + sigma_eV.
- Test set (1,468 held out): **MAE 0.0226 eV, R² 0.981** (no holes: 0.018; with holes: 0.071). Old parent-project model: MAE 0.386.
- Ensemble = 0.85 GNN + 0.15 XGBoost on top of a Hückel linear baseline; the GNN is kept (it cuts the error by ~30%).
- Uncertainty is calibrated: 96.7% of test structures fall inside ±1.96·sigma.
- Rejects inputs outside 20–40 hexagons (otherwise it gives nonsense).

## Stage 2d results (2026-11-11)

All files are in `Stage2d/` (see `Stage2d/README.md`). Stable state before the improvement: git tag `stable-stage2d-2026-11-11` + `snapshots/`.

- First run: only 46% valid on the first try, 64% after retries. Almost every failure was an **open-shell** structure (sublattice imbalance), which the LLM can't see.
- **Improved:** (1) rejections now give the imbalance plus verified fix edits (`Stage1/gqd_hex.py`); (2) the prompt teaches the closed-shell rule + point-symmetry tip (`HEXAGON_RULES` in `studio/agent.py`).
- Ablation (80 requests each): valid after retries **52% (before) → 90% (fixes) → 82% (rule) → 99% (both, now in the agent)**; first try 34% → 57%.
- Trade-off: the rule prompt reduces variety (one design repeated 9×/80). The uniqueness check and Stage 3 parent edits should handle it.

## Stage 3a results (2026-11-12)

All files are in `Stage3a/` (see `Stage3a/README.md`).

- `Stage3a/sensing.py` → `evaluate_gqd(hexagons)`: xTB (GFN2) on the GQD + 12 gas complexes (2 sites), about 65 s per GQD. It returns binding energies, charge moved to NO₂, chemisorption flags and the **sensing score = charge to NO₂ × reversibility × selectivity**.
- Fixed a bug: GQDs started flat stayed stuck flat, which inflated binding (up to −6 eV). A tiny out-of-plane nudge fixes it, and the gaps now match the dataset (MAE 0.036 eV).
- Calibration on 50 dataset GQDs:
  - Physisorbed NO₂ is at −0.3 to −0.45 eV, with a charge of 0.17–0.32 e that grows as the gap shrinks.
  - 29 of 50 chemisorb NO₂ (a C–N bond, irreversible), mostly at small gaps.
  - **The best score is at a gap of about 0.35–0.7 eV without chemisorption**, an application-driven target.
- xTB vs DFT (ωB97X-V) on tetracene and coronene:
  - Physisorption energies are close to DFT.
  - xTB overbinds NO₂ chemisorption by 0.1–0.55 eV.
  - Charge to NO₂ is right when chemisorbed but **inflated when physisorbed**; it still tracks the GQD HOMO (r = 0.88), so it is used as a ranking.
  - **O₂ is wrong in xTB** (binds in xTB, unbound in DFT), so it is excluded from the score; final candidates need a DFT air-stability check.

## Next steps

1. **Decisions needed before Stage 3:**
   - **Goal:** ✅ maximise the NO₂ sensing score (Stage 3a).
   - **Uniqueness:** ✅ children must be new vs the 91k dataset (the recommendation, applied in Stage 3; can be changed).
   - **Holes:** ✅ rejected (the recommendation, applied in Stage 3; can be changed).
2. **Stage 3:** ✅ built (`Stage3/evolve.py`, see `Stage3/README.md`).
   - Budget choice: children are scored on NO₂ + CO only (same score as the full set on all 50 calibration GQDs), 5 children in parallel, plus a free gap pre-filter. That's about 3–4 min per 10-child generation. A surrogate comes later, trained on the logs.
   - Pilot (`Stage3/README.md` → Results):
     - LLM best 0.340 (80 xTB scores) vs random 0.331 (100); start 0.322.
     - Mean scored 0.211 vs 0.190 (p = 0.20, one seed).
     - Top 10 confirmed with all gases (within 0.002).
   - Fix before Stage 4:
     - LLM validity 31% (open-shell multi-edits, duplicates, coordinate errors);
     - LLM population collapsed to one family;
     - the gap pre-filter's 0.30 eV floor may cut off the best region (LLM best gaps are 0.29–0.33 eV).
3. **DFT on the college server GPU:** a shared Ubuntu machine with 2× A100 80 GB, no scheduler, and internet access. Use GPU4PySCF for the DFT check (xTB ranking and O₂ air stability of the final candidates). The xTB loop stays on the Mac (the server CPU is slower and shared).

## Current state of the code (as of 2026-11-10)

- `studio/agent.py`: LangGraph agent. Flow: `software_check → assistant ⇄ tools (generate_gqd) → check_molecular_graph → check_uniqueness → check_ring_count → check_sp2 → check_sa_score → save_gqd → assistant`.
- Tools: `generate_gqd` (random SMILES from `pilot.csv`, the original manual path) and `build_gqd_from_hexagons` (Stage 1).
- Accepted structures are saved to `accepted_gqds/accepted_gqds.csv` and `accepted_gqds/mol_files/`.
- Thresholds: 20–40 hexagons, sp² ≥ 0.95, SA ≤ 8.0 (SA scorer from RDKit Contrib).
