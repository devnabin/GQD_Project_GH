<!-- Created date: 2026-11-11 (America/Chicago) -->

# Stage 2d: Can the LLM write GQDs as hexagon coordinates?

## What this stage does

This stage measures how well the agent's LLM designs valid GQDs when it writes **hexagon positions** instead of SMILES, and improves that rate. Stage 3 (the evolution loop) depends on it. Nothing is saved to `accepted_gqds/`; this is a measurement only.

`llm_hexagon_test.py` sends independent requests to the same Azure deployment, `build_gqd_from_hexagons` tool and validation checks as `studio/agent.py`. Each request asks for a random size (20–40 hexagons) and one of 8 shapes. When a design fails, the rejection message goes back to the LLM, which may retry up to 2 times. Valid designs are then checked for novelty (against the 91k dataset), holes, point symmetry, and predicted gap (Stage 2 predictor).

## The problem found in the first run (50 requests, `results/run1_basic-plain_2026-11-10/`)

- **Pass rates:** 46% on the first try, 64% after retries.
- **Cause:** 66 of 67 failures were **open-shell** structures.
  - The carbon atoms of a hexagon flake form two alternating sets (sublattices A and B), and every bond joins an A atom to a B atom.
  - A closed-shell structure (one with a full set of alternating double bonds) needs #A = #B.
  - Triangular parts, L-shaped corners and long zigzag edges leave extra atoms on one side, so the structure must be a radical (Lieb's theorem).
  - The LLM can't see this from coordinates, and the message "no Kekulé form" didn't tell it what to change.

## The improvements

1. **Actionable feedback** (`Stage1/gqd_hex.py`: `sublattice_counts`, `is_closed_shell`, `open_shell_fixes`, `open_shell_feedback`). The rejection now:
   - states the imbalance (e.g. "33 vs 28, 5 unpaired atoms"),
   - lists single-hexagon edits that each make the structure closed-shell,
   - or, if none exists, gives the shortest edit sequence found by a beam search (up to 8 edits, size kept within 20–40, about 0.1–0.5 s).

   All suggestions are checked to be closed-shell, and the sublattice rule agrees with all 2,000 dataset structures tested. The LLM still chooses what to do.
2. **The rule in the prompt** (`HEXAGON_RULES` in `studio/agent.py`). The prompt explains the closed-shell rule and gives a simple way to satisfy it: a **point-symmetric** shape (for every [q, r], include [a−q, b−r]) always has #A = #B.

## Ablation results (2026-11-11, 80 requests per condition, same sizes and shapes)

| Metric | basic prompt, plain message | basic + fixes | rule + plain | **rule + fixes (agent now)** |
|---|---|---|---|---|
| First-try pass rate | 34% | 36% | 56% | **57%** |
| **Pass rate after ≤2 retries** | 52% | 90% | 82% | **99%** (79/80) |
| Mean attempts | 2.21 | 1.83 | 1.66 | **1.53** |
| Open-shell failed attempts | 131 | 67 | 63 | **39** |
| Distinct valid designs | 33 | **67** | 45 | 55 |
| Most-repeated design | ×4 | ×2 | ×11 | ×9 |
| New compared with 91k dataset | all | 70/72 | all | all |
| Point-symmetric | 45% | 24% | 58% | 48% |
| Size error (hexagons) | 0.4 | 0.9 | 1.7 | 1.9 |
| Predicted gap range (eV) | 0.05–1.42 | 0.02–1.27 | 0.07–1.40 | 0.01–1.51 |
| With holes | 0 | 0 | 0 | 0 |

What it shows:
- **Both improvements help, and they add up.**
  - The rule in the prompt raises the first-try rate (34% → 57%).
  - The fix feedback makes retries work (52% → 90%).
  - Together they reach **99%**.
- **Shapes that used to fail now succeed.** Under rule + fixes, L-shaped, triangular and irregular requests went from 1/10, 3/10 and 0/10 to 10/10.
- **Cost: less variety.**
  - With the rule prompt, the LLM often falls back on a "safe" standard symmetric shape: one design appeared 9 times in 80 requests.
  - The fix feedback alone keeps the most variety (67 distinct).
  - In the agent, repeats are rejected by the uniqueness check. In Stage 3, variety comes from editing different parents.
  - If variety is still low in Stage 3, the rule text can be softened.
- **Size:** fixes and symmetric designs drift by about 2 hexagons from the requested size, but always stay within 20–40.
- **Remaining failures (8 of 122 failed attempts):** a few duplicate or malformed lists, one size of 19, and the RDKit re-read limit (see below).
- **Run-to-run variation:** the first baseline run gave 46% → 64%, and this rerun of the same condition gave 34% → 52%. Compare conditions within one run.

## Known limitation: RDKit re-read

About **14% of closed-shell random shapes** (and about 3% of LLM designs) have a valid Kekulé structure, but RDKit's own kekulizer can't re-read their SMILES (a backtracking limit). They are rejected with a clear message. A Kekulé-form SMILES can be parsed, but InChIKey and the SA score fail on it too, so a real fix would change how the whole pipeline handles SMILES. Revisit this if it becomes common in Stage 3.

## Files

| File | What it does |
|---|---|
| `llm_hexagon_test.py` | Runs the ablation (`--n 80 --retries 2 --conditions basic-plain,basic-fixes,rule-plain,rule-fixes`). |
| `results/ablation.md` | Comparison table (generated automatically). |
| `results/<condition>/attempts.csv` | One row per LLM attempt: request, attempt, size, shape, hexagons, valid, failed check, reason. |
| `results/<condition>/designs.csv` | One row per request: final outcome, SMILES, InChIKey, in_dataset, symmetric, holes, gap_pred_eV, sigma_eV. |
| `results/<condition>/summary.md` | Pass rates, rejection reasons, results by shape. |
| `results/run1_basic-plain_2026-11-10/` | The first run (50 requests, original prompt and message). |

## How to rerun

```bash
cd Agentic_GQD
.venv/bin/python Stage2d/llm_hexagon_test.py --n 80 --retries 2
```

This needs the Azure settings in `studio/.env`. It makes about 550 LLM calls and takes about 10 minutes. LLM results vary from run to run.
