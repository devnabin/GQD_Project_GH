<!-- Created: 2026-11-13 22:30 CST -->

# Stage 4: DFT-validated search

**Goal:** GQD and linked-carbon designs confirmed by DFT as reversible, selective NO₂ sensors with real charge transfer, found with a corrected score.

**Why:** the GPU DFT benchmark showed that the Stage 3a score rewards an xTB artefact, and that small-gap GQDs are partly open-shell. Plan: `PLAN.md`. Timestamped log: `PROGRESS.md`.

| File | What it does |
|---|---|
| `score_v2.py` | Score v2: DFT-fitted correction of bonded-NO₂ energies, physisorbed charge set to 0, signal from the Stage 3c sensor twin |
| `rescore.py` | Rescores every existing xTB result with score v2 → `results/rescored.csv` |
| `fod_screen.py` | xTB N_FOD open-shell screen for given geometries |
| `fod_candidates.py` | N_FOD for the top score-v2 candidates → `results/fod_candidates.csv` |
| `v2_loop.py` | Score-v2 support for `Stage3/evolve.py --score v2 --fod-max 2.9` |
| `prepare_linked.py` | Puts linked-carbon geometries into a `Stage3a/dft_gpu.py` folder |
| `overnight.sh` | Overnight server queue: GPU DFT of 8 candidates; CPU smoke test and 4 search runs |

**Where things run:** everything on the college server (`~/Agentic_GQD`). xTB runs on the CPU; DFT on GPU 0.

**Results:** `results/` (copied back from the server). The DFT folders (`dft_linked/`, `dft_fused/`) and the new runs (`Stage3/results/*_sv2_*`) are on the server until they finish.
