<!-- Created date: 2026-11-13 (America/Chicago) -->

# Stage 4: DFT-validated search (4–5 day plan, started 2026-11-13)

**Goal:** a list of GQD (and linked-carbon) designs confirmed by DFT as reversible, selective NO₂ sensors with real charge transfer. They should be found by the AI-guided search with a corrected score.

**Why:** the GPU DFT benchmark (`Stage3a/results/dft_benchmark.md`) showed three problems with the Stage 3a score.
- It ranks GQDs unlike DFT (Spearman −0.16).
- xTB's charge on physisorbed NO₂ is an artefact (DFT about 0).
- Small-gap GQDs are partly open-shell in DFT.

Only weakly chemisorbing GQDs kept a DFT score: gqd_13400 (0.105) and gqd_58903 (0.066).

**Compute rule (user, 2026-11-13):** no heavy computing on the MacBook. xTB runs on the college server CPU (`nice`, ≤ 16 threads); DFT on server GPU 0 (GPU 1 only if idle). The Mac is used only for editing and light scripts (seconds).

## Days

| Day | Work | Where |
|---|---|---|
| 1 (11-13) | (a) Open-shell check: BS-UKS on the other 8 benchmark GQDs, and the xTB FOD (N_FOD) screen calibrated against it. (b) Score v2 (below). (c) Rescore every logged xTB child offline, giving a first candidate list. (d) Overnight: DFT on the top candidates | GPU + CPU |
| 2 | Evolution runs with score v2 (LLM and random), all gases | server CPU |
| 3 | DFT confirmation of the top new candidates; DFT check of 2 linked-carbon designs | server GPU |
| 4 | Analysis, figures, thesis update (results, discussion, abstract) | light |
| 5 | Buffer; summary for the supervisor | light |

## Score v2 (draft; every choice is checked against the DFT benchmark)

- **Binding energy:** xTB E_NO₂ (Spearman 0.74 with DFT). Chemisorbed complexes are shifted by the mean xTB→DFT offset of the bonded complexes in the benchmark.
- **Charge:** xTB charge only when NO₂ is chemisorbed (DFT agrees: 0.22 vs 0.21 e). Physisorbed charge is set to 0 (DFT 0.01 e).
- **Signal:** Stage 3c sensor-twin response at 20 ppb NO₂ and 50% RH, recovery ≤ 5 min.
- **Open-shell filter:** reject GQDs with N_FOD above a threshold calibrated against BS-UKS (or a gap floor if FOD does not separate them).

Progress log: `Stage4/PROGRESS.md`.
