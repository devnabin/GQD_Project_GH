<!-- Created date: 2026-11-11 (America/Chicago) -->

# Session Log

> One entry per working session, newest first. Read the top entry + `WORK_DIRECTION.md` to resume.
> Each entry: what was done, decisions made, open questions, and the exact next action.

---

## 2026-11-13 (19:15) — Radical filter set; overnight queue running on the server

- Broken-symmetry DFT done for all 12 benchmark GQDs: 5 closed-shell, 7 open-shell. xTB N_FOD separates them without error, so the threshold is **N_FOD ≤ 2.9**.
- Applied to the top 80 score-v2 candidates: 20 are closed-shell (9 fused, 11 linked).
- Overnight queue (`Stage4/overnight.sh`, log `Stage4/overnight.log`), detached on the server:
  - GPU: DFT of 4 linked and 4 fused candidates, then a broken-symmetry check of all 8;
  - CPU: fused geometries, a smoke test, then 4 score-v2 search runs.
- **Next action (morning):**
  - read `Stage4/overnight.log`;
  - if the smoke test failed, fix it and start the runs;
  - run `dft_gpu.py --summary-only` on `Stage4/dft_linked` and `Stage4/dft_fused`, then compare xTB/score v2 with DFT for the 8 candidates (including triple-bond binding);
  - check the runs' progress.

---

## 2026-11-13 (18:10) — Stage 4 started: 4–5 day DFT-validated search; all compute on the server

**User decisions**
- Do as much as possible in 4–5 days.
- No heavy computing on the MacBook. The professor allows the college server CPU and GPU.
- Agents: fresh general-purpose agents with short prompts; no forks, no waiting agents (memory `agent-usage-preference`).

**Done**
- DFT benchmark analysis finished:
  - score Spearman −0.16;
  - xTB physisorbed NO₂ charge is an artefact;
  - small-gap GQDs are partly open-shell.
  - The rule fixed in advance says the score must change.
- `Stage4/` created: `PLAN.md`, `PROGRESS.md`, `score_v2.py`, `rescore.py`, `fod_screen.py`, `fod_candidates.py`.
- Score v2: bonded NO₂ shifted by +0.176 eV (DFT fit) and physisorbed charge set to 0, scored with the sensor twin. Rescoring 849 existing structures gave 326 with score > 0; the top 25 are all weakly bonded NO₂, and 6 of them are linked carbon.
- The xTB N_FOD screen follows the DFT open-shell lowering for the 5 GQDs checked so far. gqd_13400 is also open-shell (0.27 eV).

**Running on the server**
- `bs_check.py` (GPU 0) on the last 7 benchmark GQDs.
- `fod_candidates.py` (16 CPU cores, nice) on the top 80 candidates.

**Next action**
- Set the N_FOD threshold; pick about 10 closed-shell top candidates (fused + linked).
- Full five-gas xTB with geometries kept (server CPU), then overnight DFT (GPU 0).

---

## 2026-11-13 (17:23) — Stage 3a: broken-symmetry check written up

- Copied `Stage3a/bs_check.py`, `Stage3a/data/dft_benchmark/bs_check.jsonl` and `.log` from lamar-ai. 4 rows, all UKS converged; no `bs_check` process running.
- Result (wB97X-V/def2-SVP, xTB geometry): E(RKS) − E(BS-UKS) = 0.82 / 0.68 / 0.43 / 0.04 eV with <S^2> 1.67 / 1.48 / 1.67 / 0.62 for llm_s0_g10c004 (xTB gap 0.29), random_s0_g02c004 (0.36), gqd_18941 (0.49), gqd_88143 (0.86). Small-gap GQDs are open-shell in DFT despite a Kekulé structure; with the BS reference, DFT NO₂ binding of llm_s0_g10c004 goes from −1.09 to about −0.27 eV. Charge result unaffected.
- Added: section "Broken-symmetry check" in `Stage3a/results/dft_benchmark.md`; thesis Ch. 5 (pending replaced, Table `tab:e4-bs`, new pending for the other 8 GQDs) and Ch. 6 RQ2 paragraph; new open decision D22 in `RESEARCH_OPTIONS.md`. Thesis compiles clean. Nothing committed.
- **Next:** run `bs_check.py` on the other 8 benchmark GQDs to locate the gap limit; then decide D22 together with D7.

---

## 2026-11-13 (11:15) — Stage 3d L2: linked-carbon NO₂ scoring (L2 agent)

- `Stage3d/sensing_linked.py`: `evaluate_linked()`, the Stage 3a workflow for linked designs. It adds triple-bond and pore sites, uses the same output keys, and both scores work unchanged.
- **Consistency test:** with the same start geometry, one-unit designs reproduce Stage 3a within 0.0003 eV. A different start noise moves the energies by up to 0.09 eV through twisted conformers. That is conformer noise, which Stage 3a also has.
- **Calibration of 21 designs (xTB, all converged):**
  - the C≡C bond is the reactive site, chemisorbing NO₂ at 15 of 21 sites (median −0.95 eV);
  - 19 of 21 designs chemisorb;
  - Stage 3a score best 0.197, against 0.322 for fused GQDs;
  - on the twin, the best designs are ring-site hybrids: `naph_row4_n1` (−0.77 eV, 11 s, 0.115 e per site) and `pyrene_row3_n1`.
- A DFT bundle for `gdy_rhomb4` and `naph_row4_n1` is ready (50 SCFs). Not run, because the VPN is down.
- New open decision D21 (the triple bond). Details: `Stage3d/README.md`, `PROGRESS.md`.
- **Next:** DFT check of the triple-bond site when the server is reachable; then decide D19 and D21 before L3/L4.

---

## 2026-11-12 (22:45) — Stage 4 comparison finished (done by the E5b agent)

- All six v2 runs finished; `Stage3/compare.py ... --name v2` → `Stage3/results/compare_v2.md` and `.png`.
- Result:
  - best score: random 0.351 ± 0.008 (0.356, 0.354, 0.341) vs LLM 0.344 ± 0.004 (0.342, 0.343, 0.348); random won 2 of 3 seed pairs;
  - mean scored: LLM 0.186 ± 0.012 vs random 0.163 ± 0.013; LLM higher in all 3 pairs; Mann-Whitney p = 0.004 (children not independent);
  - H3 is supported for the mean score and not for the best score.
- Full checks: loop vs full score within 0.003 for 30 GQDs. All 40 fully checked GQDs physisorb NO₂ with both score factors at 1, so the score equals the xTB charge.
- Thesis updated and compiled (71 pages, no errors): §5.7 (final tables and figure), §5.9 best GQDs (40), discussion RQ3 and RQ4 numbers, abstract, conclusion, E5b status. Also `Stage3/README.md`, `WORK_DIRECTION.md`, `RESEARCH_OPTIONS.md` (D12, D13 notes), `Report/README.md`.
- Left for the DFT agent: the RQ2 discussion still says "all 25 best GQDs"; it should say 40.
- **Next action:** E4 (DFT benchmark) results into the thesis; E6 baseline; user decision on D13.

---

## 2026-11-12 (22:28) — Stage 3d L1: linked-carbon builder (done by the L1 agent)

- Built `Stage3d/linked.py`:
  - representation: units (hexagon lists), place (coarse grid) and links (n = 1 or 2);
  - checks with plain-language `LinkError` messages;
  - RDKit molecule, canonical SMILES and a 3D start geometry.
- `test_linked.py`: **14 of 14 pass.**
  - Diphenylacetylene and diphenylbutadiyne match the known molecules.
  - The benzene triangles are C24H12 (n=1) and C30H12 (n=2).
  - The naphthalene and coronene hybrids build.
  - All 8 invalid inputs are rejected with clear reasons.
- `xtb_check.py`: three structures optimise with GFN2-xTB, all converged.
  - C≡C 1.21 Å, nearly linear, flat.
  - xTB gaps 2.19, 2.42 and 2.05 eV.
- Design choices: D20 in `RESEARCH_OPTIONS.md`. Full log in `Stage3d/PROGRESS.md`.
- Not in the thesis yet. The main session adds it after the E5b and E4 agents finish.
- **Next (L2):** NO₂ scoring for linked carbon (triple-bond and pore sites; `evaluate_gqd` from built coordinates; a small calibration set).

---

## 2026-11-12 (22:30) — Sensor twin v1 (Stage 3c); two background agents waiting

- User decisions:
  - D15: build the twin;
  - D16 and D17 were delegated to me, and I chose linked carbon with fused units allowed, because it is the most accurate option with xTB and DFT.
- `Stage3c/twin.py` and `README.md`: Langmuir coverage at real concentrations with Campbell–Sellers entropy, a signal per site, recovery time and humidity interference. Results (xTB, 85 GQDs):
  - water does not crowd out NO₂;
  - the current best GQDs have tiny NO₂ coverage at 20 ppb;
  - the twin prefers NO₂ binding near −0.75 to −0.82 eV;
  - rank correlation with the Stage 3a score is 0.62.
  
  Not a conclusion until DFT energies are in. New open decision D19 in `RESEARCH_OPTIONS.md`.
- Two background agents (started 22:10):
  - the E5b agent waits for `random_v2_s3`, then runs the comparison and updates the thesis;
  - the E4 agent waits for DFT phase 1 (90 SCFs), then runs the xTB vs DFT analysis and updates the thesis.
- Not yet in the thesis: Stage 3c. Add it after both agents finish, to avoid edit conflicts:
  - Chapter 4: a new experiment E7;
  - Chapter 5: the twin results;
  - merge the E4 agent's proposed abstract and conclusion sentences.
- **Next:** rerun the twin with DFT energies for the 12 benchmark GQDs.

---

## 2026-11-12 (22:05) — Run interrupted and resumed; options log created

- The Claude Code session ended at about 21:55 and killed the Mac run loop during `random_v2_s3` generation 6.
  - Resumed with `nohup caffeinate` (detached, so it survives the session ending). Same seed, so it redoes generation 6 exactly. ETA about 22:45.
  - Lesson: start long Mac jobs with `nohup ... & disown`, not as a session background task.
- Status:
  - Stage 4: 5 of 6 runs done.
  - Best: LLM 0.342, 0.343 and 0.348; random 0.356 and 0.354 (s3 running).
  - Mean scored: LLM higher in every finished pair.
  - DFT: 80 of 162 SCFs done, all converged; phase 1 (NO₂ + CO) about 10 SCFs from done.
- Added `RESEARCH_OPTIONS.md` (every fork, with the options not taken) and rule 3 in `AGENTS.MD`.
- Open decisions: D13 (thesis framing), D15 (sensor twin first?), D16 (linked carbon vs phthalocyanine/MOF), D17 (fused units in linked carbon).
- **Next action:**
  - when `random_v2_s3` finishes, run `compare.py llm_v2_s1 llm_v2_s2 llm_v2_s3 random_v2_s1 random_v2_s2 random_v2_s3 --name v2` and update thesis §5.7, the abstract and Chapters 6 and 7;
  - when DFT phase 1 finishes, run `dft_gpu.py --summary-only` on the server, rsync, compute Spearman, and update thesis §5.8.

---

## 2026-11-12 (evening) — Thesis draft started; Stage 4 runs and DFT benchmark running

**User requests**
- Write a full thesis report on the Agentic_GQD work (from `studio/agent.py` to now). Simple academic English; no AI-writing patterns (Wikipedia "Signs of AI writing").
- Keep the thesis up to date after every experiment, discovery and progress, and put that rule in the project .md file.

**Done**
- `Report/` created; `main.tex` compiles with no errors (68 pages). Contents:
  - one file per chapter in `chapters/`: abstract, introduction (RQ1 to RQ4, H1 to H4), literature review, methods (4 algorithms, 3 TikZ diagrams), experimental design (E1 to E6), results, discussion, conclusion, appendices A to C;
  - `references.bib` with 75 references, all cited (uncertain ones checked on the web; 8 marked `% check`). A later literature check added 7 close neighbours (MatLLMSearch, LLEMA, My Chemical Harness, El Agente, GaUDI, two GQD design studies); no direct precedent was found for LLM-guided design of GQDs/PAHs;
  - `figures/` and `README.md`.
- Results not in yet are marked `\pending{...}` (orange in the PDF).
- Standing rule added at the top of `AGENTS.MD`: session records plus which thesis chapter to update for what, style rules and a compile check. Memory `session-log-habit` updated.
- Found while writing:
  - For all 25 best GQDs, both score factors are 1, so the score equals the xTB physisorbed charge, the quantity xTB overestimates. This makes the DFT benchmark (E4) decisive.
  - The run logs don't record the LLM model name. It is GPT-5.4 (from `AZURE_OPENAI_MODEL`). Add it to `config.json` in `evolve.py` after the current runs finish; don't edit it while they run.

**Status at 19:33**
- Stage 4 (Mac): `llm_v2_s1`, `llm_v2_s2` and `random_v2_s1` are finished; `random_v2_s2` is running. Best so far: random 0.356, LLM 0.342 and 0.343.
- DFT benchmark (server): 45 of 162 single points done, all converged.

**Uncommitted:** `Report/`, `AGENTS.MD`, plus everything listed in the entry below.

**Next action**
- When the 6 runs finish:
  - run `compare.py ... --name v2`;
  - in the thesis, replace Table `tab:main-prelim` and the related `\pending` items, and update the abstract and Chapters 6 and 7;
  - then run E6, the random-generation baseline.
- When the DFT benchmark finishes, fill in Section 5.8 (E4) and its discussion.
- Small fixes:
  - add `rdkit` to the `gqd-dft` line in `server/setup_envs.sh`;
  - log the model name in `evolve.py`.

---

## 2026-11-12 (day) — Stage 3 evolution loop built; pilot running

**User answers**
- Budget: "whichever you think is best, run that one". Commit Stage 3a: not yet.
- Asked where the scores are: `Stage3a/results/summary.md` (top 10 + by-gap table), `score_vs_gap.png`, `data/calibration.csv`.

**Done**
- Budget choice: score children on NO₂ + CO only (CO was the strongest interferent for all 50; same score exactly), score 5 children in parallel, free gap pre-filter (0.30–1.60 eV). That's about 3–4 min per 10-child generation, versus about 11 min before. A surrogate comes later, from the logs.
- `Stage3a/sensing.py`:
  - `evaluate_gqd(..., analytes=)`
  - `LOOP_ANALYTES`, `BOND_A`
  - `site_cells`, `NO2_chemisorbed`
  - the score uses whichever interferents were computed. Stage 3a results unchanged (summary.md identical).
- `Stage3/evolve.py`: LLM or random mutator → checks (agent checks + new vs 91k + no holes) → gap pre-filter → xTB → top-8 population. Logs all AGENTS.md fields; resumable; final full check of the top 5.
- `Stage3/compare.py`: runs side by side on the same xTB budget.
- `Stage3/README.md`.
- Uniqueness vs 91k and hole rejection: applied as recommended (flags can change).
- Pilot started in the background (caffeinate): `llm_s0`, then `random_s0`, 10 gen × 10 children each. Logs in `Stage3/results/*.log`.

**Pilot results** (`Stage3/README.md` → Results, `Stage3/results/compare.md`)
- LLM best 0.340 with 80 xTB scores vs random 0.331 with 100 (start 0.322).
- Mean scored 0.211 vs 0.190, p = 0.20 (one seed: not significant).
- The full check confirmed the loop scores (within 0.002); CO was always the strongest interferent.
- Problems:
  - LLM validity 31% (100/300 open-shell, 43 duplicates, about 30 coordinate errors);
  - the LLM population collapsed to one family (`gqd_14650`);
  - the best LLM gaps (0.29–0.33 eV) sit at the 0.30 eV pre-filter floor;
  - xTB E_O₂ is −2.7 to −3.4 eV for the best GQDs (needs a DFT air-stability check).
- `final_check` now runs in parallel (edited before the random run started).

**College server** (user has SSH access; hostname and username are not recorded here)
- Shared Ubuntu 24.04 machine: 2× Xeon Silver 4309Y (16 cores / 32 threads, load about 20), 503 GB RAM, 2× A100 80 GB (GPU 0 free, GPU 1 in use).
- CUDA 12.8, conda (envs in `~/.conda/envs`), internet and Azure reachable, no scheduler.
- `/usr/bin/orca` is the screen reader, not ORCA.
- Plan: the xTB loop stays on the Mac; the server GPU runs DFT (GPU4PySCF).
- The user was given commands to create the `gqd-dft` env and test benzene ωB97X-V/def2-SVP on the GPU. Mac CPU reference: −232.014171 Ha (61 s).

**Server set up (later the same day)**
- Key login from the Mac works (`ssh lamar-ai`), so Claude runs things on the server directly.
- Project copied with rsync to `~/Agentic_GQD` (chmod 700, no secrets). The user OK'd copying only the `AZURE_OPENAI_*` lines to `studio/.env` (chmod 600).
- Envs `gqd` and `gqd-dft` installed (`server/setup_envs.sh`; GPU4PySCF needs `cupy-cuda12x[ctk]`). See `server/README.md`.
- Tests:
  - xTB score for gqd_18941 is identical (0.322) but 6× slower than the Mac (394 s, shared CPU);
  - GPU DFT benzene −232.014171 Ha matches the Mac, 4.5 s vs 61 s;
  - a 134-atom GQD takes 99 s (RKS) and the +NO₂ complex 366 s (UKS) on the A100.
- Decision: xTB loops stay on the Mac; the server GPU does DFT (and later ML training). The user asked whether to move the whole project: advised not yet (revisit at Stage 5).
- `evolve.py`: placeholder Azure env vars so random runs work without a key; the LLM mutator exits with a clear message if the key is missing.

**Uncommitted:** `Stage3a/`, `Stage3/`, `server/`, WORK_DIRECTION.md, this log.

**Started ~16:15 (the user OK'd both)**
- **DFT benchmark, server GPU 0** (`Stage3a/dft_gpu.py`, log `~/Agentic_GQD/Stage3a/data/dft_benchmark/dft_gpu.log` on the server).
  - 12 GQDs: 10 calibration GQDs across the score range, plus the pilot bests `llm_s0_g10c004` and `random_s0_g02c004`.
  - Geometries from `Stage3a/make_geometries.py` (Mac); the xTB scores reproduced.
  - 162 SCFs, no density fitting: DF was slower on the A100, so the test was stopped.
  - Phases: GQD + NO₂ + CO (~7 h) → O₂ (~3 h) → H₂O/NH₃ (~2 h). The cache is resumable; `--summary-only` gives partial results.
  - The ssh session that launched it stays open as a background task (stdin not detached). Harmless; nohup keeps the job alive.
- **Stage 4 comparison, Mac:** `llm_v2_s1, random_v2_s1, …, random_v2_s3` (10 gen × 10 children, v2 loop), about 6 h.
  - Early sign: LLM gen 1 had 12/15 valid (pilot 31%).

**Next action**
- When the runs finish: `.venv/bin/python Stage3/compare.py llm_v2_s1 llm_v2_s2 llm_v2_s3 random_v2_s1 random_v2_s2 random_v2_s3 --name v2`.
- When DFT phase 1 is done: `rsync` `dft_benchmark` back, run `dft_gpu.py --summary-only` there, and check the xTB vs DFT ranking (Spearman).
- Then write the GPU DFT script: an xTB-vs-DFT ranking check on about 10 GQDs, plus an O₂ check of the final candidates.
- Fix the loop before Stage 4:
  - auto-repair open-shell children with the Stage 1 fixes, or more rounds;
  - a diversity cap per family;
  - lower the gap floor to about 0.2 eV.
- Then run 3–5 seeds per mutator.

---

## 2026-11-12 (night) — Stage 3a: NO₂ sensing score built and calibrated

**Done** (details: `Stage3a/README.md`)
- `Stage3a/sensing.py`: `evaluate_gqd(hexagons)` builds the GQD from the hexagon grid, then runs xTB on the GQD + NO₂ (2 orientations), H₂O, NH₃, CO and O₂ at 2 sites. It returns binding energies, charge to NO₂, chemisorption flags and the sensing score. About 65 s per GQD.
- Bug found and fixed: a flat start left twisted (cove/fjord) GQDs stuck flat, which inflated binding (one GQD showed −6 eV for H₂O). The first run is archived in `Stage3a/data/run1_flat_start/`, and everything was rerun with a small out-of-plane nudge.
- Calibration on 50 gap-stratified dataset GQDs: all converged, gap vs dataset MAE 0.036 eV.
  - Physisorbed NO₂ −0.3 to −0.45 eV.
  - 29 of 50 chemisorb (mostly small gaps).
  - Charge to NO₂ grows as the gap shrinks.
  - Best score at a gap of about 0.35–0.7 eV without chemisorption.
- DFT check (ωB97X-V/def2-SVP, PySCF) on tetracene and coronene:
  - Physisorption energies agree with xTB.
  - NO₂ chemisorption is real, but xTB overbinds it by 0.1–0.55 eV.
  - Charge is right when chemisorbed and inflated when physisorbed (it still tracks the HOMO, r = 0.88).
  - O₂ is wrong in xTB, so it is excluded from the score.
- Installed `matplotlib` in `.venv` (for plots). `pyscf-dispersion` was tried, broke the PySCF import, and was uninstalled; the venv versions match `requirements_freeze.txt` again.

**Score (decided by the data):** charge to NO₂ × reversibility (1 above −0.6 eV, 0 below −1.0 eV, xTB) × selectivity (≥ 0.1 eV over H₂O/NH₃/CO).

**Uncommitted:** all of `Stage3a/`, WORK_DIRECTION.md, this log (needs the user's OK to commit/push).

**Open questions for the user**
- Is the score definition OK (especially leaving out O₂ and the −0.6 / −1.0 eV window)?
- Stage 3 budget: xTB costs about 65 s per child, so 30 generations × 20 children is about 11 h. Use a surrogate, fewer children, or both?

**Next action**
- Commit Stage 3a with the user's OK. Then design Stage 3 (evolution loop with the sensing score; consider a response proxy from the HOMO, since physisorbed xTB charges are inflated).

---

## 2026-11-12 — Application chosen: NO₂ gas sensing

**Decided**
- The project is built around **one application: NO₂ gas sensing** (the GQD should bind NO₂ more strongly than H₂O, NH₃, CO and O₂, show a clear electronic response, and not bind so strongly that it never releases it). The design goal is set by the application, not just a target gap.
- Fe³⁺ sensing and fluorescence probes are set aside: they need charged-ion or excited-state physics beyond xTB.

**Feasibility test (scratchpad, not in the repo)**
- Homebrew `xtb` 6.7.1 crashes (gfortran format bug). Use the conda-forge build at `../AI_GQD/.env/bin/xtb`.
- One accepted GQD (21 hex), GFN2, analyte placed 3.2 Å above the centre, both optimised: E_ads NO₂ −0.35, CO −0.20, H₂O −0.12, NH₃ −0.11 eV. Only NO₂ changes the gap (0.85 → 0.63 eV). That's about 35 s per GQD for 4 analytes.

**Next action**
- Committed and pushed: commit `04dd140`, tag `stable-stage2-final` (branch `agentic-gqd` on GitHub). The Studio test GQDs were kept.
- Plan Stage 3a (xTB adsorption workflow + sensing score) and Stage 3b (dopants / edge groups), then the evolution loop with the sensing score.

---

## 2026-11-11 — Stage 2 improved and tested in Studio

**Done**
- Stage 2d improvement: open-shell rejections now give the sublattice imbalance + verified fix edits (`Stage1/gqd_hex.py`); the prompt teaches the closed-shell rule (`HEXAGON_RULES` in `studio/agent.py`). Ablation, 80 requests each: valid after retries 52% → **99%**.
- The agent now fixes its own rejected design (≤3 attempts) without asking.
- `Stage2/predictor.py` accepts a single structure as well as a list.
- The user tested in Studio: the agent designed, fixed and saved GQDs (`accepted_gqds/` now has 4); checked one, which is new vs 91k, closed-shell, no holes, predicted gap 0.43 ± 0.01 eV.

**Uncommitted work:** all of the above (the last commit is `0d399bb`, tag `stable-stage2d-2026-11-11`, branch `agentic-gqd`).

**Open decisions (needed before Stage 3):** gap goal, uniqueness vs 91k, holes. Also: should the Studio test rows in `accepted_gqds/` be kept?

**Next action**
- With the user's OK, commit as tag `stable-stage2-final`; get the 3 decisions; create `Stage3/` (evolution loop).

---

## 2026-11-11 — Session continuity set up

**Done**
- Reviewed state from `WORK_DIRECTION.md`: Stages 0, 1, 2, 2d done; Stage 3 (evolution loop) is next.
- Created this `SESSION_LOG.md` so each session can be resumed quickly.

**Uncommitted work in the repo**
- Stage 2d results moved into run folders (`Stage2d/results/run1_basic-plain_2026-11-10/`, `basic-fixes/`, `rule-fixes/`, `rule-plain/`, `ablation.md`).
- Edits to `Stage1/gqd_hex.py`, `Stage2/predictor.py`, `Stage2d/*`, `studio/agent.py`, `accepted_gqds/`.

**Open decisions (needed before Stage 3)**
1. Goal: minimise, maximise, or hit a target gap? (data: 0.00–2.03 eV)
2. Uniqueness vs. the 91k dataset? (recommended: yes)
3. Holes: reject with a 6th check (recommended) or allow with forced xTB?

**Next action**
- Get answers to the 3 decisions, commit the Stage 2d work, then create `Stage3/` and build the evolution loop.
