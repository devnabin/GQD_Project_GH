<!-- Created date: 2026-11-10 (America/Chicago) -->

# Work Direction

> Start here when resuming work. Full details: `Final_Planning.md`. Fine-tuning data plan: `AGENTS.MD`.
> Each stage has its own folder (`Stage1/`, `Stage2/`, …) with a `README.md` and its files.
> Update the **Status** column and **Next steps** whenever a stage moves forward.

## Goal

Build an AI agent that designs new graphene quantum dots (GQDs) and improves them toward a target property, such as a chosen HOMO–LUMO gap. **The LLM decides what to try, and code decides what's valid and good.**

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
| **3. Evolution loop** | score → select → LLM edits → validate → log → repeat | To do |
| **4. Experiments** | Random vs. random mutation vs. LLM-guided, same xTB budget | To do |
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

All files are in `Stage2d/` (see `Stage2d/README.md`).

- 50 LLM requests: **46% valid on the first try, 64% after up to 2 retries**. All valid designs are new compared with the 91k dataset; none have holes.
- **Every failure** (except one RDKit re-read case) is an open-shell structure caused by **sublattice imbalance**. Triangular and L-shaped pieces fail most. The LLM handles size, connectivity and the other checks well.
- Retries barely help, because "no Kekulé form" isn't actionable.

## Next steps

1. **Actionable open-shell feedback:** report the A/B imbalance and list single-hexagon edits that make the structure closed-shell; rerun Stage 2d to measure the gain.
2. **Decisions needed before Stage 3:**
   - **Goal:** minimise, maximise, or hit a target gap? (Data spans 0.00–2.03 eV.)
   - **Uniqueness:** must new GQDs also be new compared with the 91k dataset? (Recommended: yes.)
   - **Holes:** reject them with a 6th validation check (recommended; the predictor is 4× worse on them) or allow them with forced xTB verification?
3. **Stage 3:** evolution loop using `GapPredictor` for scoring and xTB for the top candidates, logging all fields from `AGENTS.MD`.

## Current state of the code (as of 2026-11-10)

- `studio/agent.py`: LangGraph agent. Flow: `software_check → assistant ⇄ tools (generate_gqd) → check_molecular_graph → check_uniqueness → check_ring_count → check_sp2 → check_sa_score → save_gqd → assistant`.
- Tools: `generate_gqd` (random SMILES from `pilot.csv`, the original manual path) and `build_gqd_from_hexagons` (Stage 1).
- Accepted structures are saved to `accepted_gqds/accepted_gqds.csv` and `accepted_gqds/mol_files/`.
- Thresholds: 20–40 hexagons, sp² ≥ 0.95, SA ≤ 8.0 (SA scorer from RDKit Contrib).
