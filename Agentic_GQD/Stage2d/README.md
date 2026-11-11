<!-- Created date: 2026-11-11 (America/Chicago) -->

# Stage 2d: Can the LLM write GQDs as hexagon coordinates?

## What this stage does

This stage measures how well the agent's LLM designs valid GQDs when it writes **hexagon positions** instead of SMILES. That is the basis of the evolution loop (Stage 3). Nothing is saved to `accepted_gqds/`; this is a measurement only.

`llm_hexagon_test.py` sends **50 independent requests** to the same Azure deployment, `build_gqd_from_hexagons` tool and validation checks as `studio/agent.py`. Each request asks for a random size (20–40 hexagons) and one of 8 shapes. When a design fails, the rejection message goes back to the LLM, which may retry up to 2 times. Valid designs are then checked for novelty (against the 91k dataset), holes, and predicted gap (Stage 2 predictor).

## Results (run 2026-11-10/11, 50 requests, 0.8 min)

| Metric | Result |
|---|---|
| **First-try pass rate** | **46%** (23/50) |
| **Pass rate after up to 2 retries** | **64%** (32/50) |
| Size accuracy (requested vs built) | off by 0.2 hexagons on average |
| New compared with the 91k dataset | **32/32** |
| Unique among themselves | 28/32 |
| With holes | 0/32 |
| Predicted gap of valid designs | 0.01–1.58 eV (median 0.40) |

Pass rate by requested shape:

| Shape | Valid |
|---|---|
| Round | 7/7 |
| Armchair edges | 6/6 |
| Elongated ribbon | 6/7 |
| Rectangular | 5/6 |
| Zigzag edges | 4/6 |
| Irregular | 3/6 |
| Triangular | 1/6 |
| L-shaped | 0/6 |

### Why designs fail: one cause

- **66 of 67 failed attempts** are "no Kekulé form (open-shell)".
- **All 66** have a **sublattice imbalance**: the honeycomb has two alternating sets of carbon atoms (A and B), and these shapes have 1–7 more of one than the other. A closed-shell structure (one with a full set of alternating double bonds) needs equal numbers, so these structures must be radicals (Lieb's theorem). Triangular and L-shaped pieces and zigzag corners create this imbalance.
- The 1 other failure is the known RDKit re-read limit from Stage 1.
- No design failed on ring count, sp², SA score, connectivity, or duplicates. The LLM handles those rules well.

**Retries help only a little (46% → 64%).** The message "no Kekulé form" doesn't tell the LLM *what* to change, and it can't count sublattices by looking at coordinates.

## Suggested fix (before Stage 3)

Make the rejection **actionable**. When a structure is open-shell, the code should:
1. Report the imbalance, for example "7 more A atoms than B".
2. Test single-hexagon edits (add one neighbour, or remove one edge hexagon) and list the ones that make it closed-shell, for example "Fix options: ADD [3,-1], ADD [0,4], REMOVE [5,0]".

The LLM still makes the choice, and the code only supplies facts, which is the project rule. This also matters for Stage 3, where the LLM's edits will often create open-shell children. The failed attempt and its fix would be logged as fine-tuning data.

## Files

| File | What it does |
|---|---|
| `llm_hexagon_test.py` | Runs the test (`--n 50 --retries 2 --concurrency 5 --seed 0`). |
| `results/attempts.csv` | One row per LLM attempt: request, attempt, target size, shape, hexagons, valid, failed check, reason. |
| `results/designs.csv` | One row per request: final outcome, SMILES, InChIKey, in_dataset, holes, gap_pred_eV, sigma_eV. |
| `results/summary.md` | Pass rates and rejection reasons, generated automatically. |

## How to rerun

```bash
cd Agentic_GQD
.venv/bin/python Stage2d/llm_hexagon_test.py --n 50 --retries 2
```

This needs the Azure settings in `studio/.env`. It makes about 100 LLM calls and takes about 1 minute. Results vary from run to run, because the LLM is not deterministic.
