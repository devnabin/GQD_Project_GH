<!-- Created date: 2026-11-12 (America/Chicago) -->

# Research options and decisions

Every time the project reached a fork, the options are recorded here: the one we took, and the ones we did not, with the reason. Nothing is deleted. When a parked option is picked up later, change its status and add the date.

**Status:** ✅ chosen · ⏸ parked (good, not now) · ❌ rejected (with reason) · ❓ open (needs a decision)

## Index

| # | Decision | Date | Chosen | Other options | Status |
|---|---|---|---|---|---|
| D1 | How the LLM creates structures | 11-10 | Hexagon coordinates + LLM-guided evolution | Parameters-only tool, LLM edits, chemistry models, generative models | ✅ / ⏸ |
| D2 | Who picks double bonds | 11-10 | Our own perfect matching | RDKit kekulizer | ✅ |
| D3 | Gap predictor model | 11-10 | GNN + XGBoost ensemble on Hückel baseline | Boosted trees only, Morgan fingerprints, Mac GPU | ✅ |
| D4 | Fixing LLM validity | 11-11 | Rule prompt + fix-edit feedback | Either one alone; softer rule | ✅ / ⏸ |
| D5 | Uniqueness and holes | 11-11 | New vs 91k; reject holes | Allow repeats; allow holes with forced xTB | ✅ |
| D6 | Design goal | 11-12 | NO₂ sensing score | Target gap; Fe³⁺ sensing; fluorescence probe | ✅ / ⏸ |
| D7 | Sensing score details | 11-12, 11-13 | Charge × reversibility × selectivity, O₂ excluded; **DFT says the response term must change** | HOMO response, DFT charge, learned correction, weak chemisorption target, twin | ❓ |
| D8 | xTB budget in the loop | 11-12 | NO₂ + CO only, 5 children in parallel, gap pre-filter | Surrogate model; fewer children | ✅ / ⏸ |
| D9 | Fixes after the pilot | 11-12 | Repair + family cap + gap floor 0.20 + 4 rounds | More rounds only | ✅ |
| D10 | Where to compute | 11-12 | xTB on Mac, DFT on server GPU | Whole project on server; ORCA; density fitting | ✅ / ⏸ |
| D11 | Order of stages | 11-12 | Stage 4 before 3b | 3b first | ✅ |
| D12 | Experiment design | 11-12 | 3 seeds per mutator; DFT decision rule set in advance | 5 seeds; random-generation baseline | ✅ / ❓ |
| D13 | Thesis framing | 11-12 | Story must not depend on "LLM beats random" | LLM-wins framing | ❓ |
| D14 | Publication plan | 11-12 | Deferred by user | Paper 1 now / workshop / preprint | ⏸ |
| D15 | Next direction after the "Cyber Twin" suggestion | 11-12 | Sensor twin first, then a new structure class | Directly change structures | ✅ (user, 11-12) |
| D16 | Structure class beyond fused hexagons | 11-12 | Linked carbon | Phthalocyanine/MOF, 5/7 rings, dopants, free 3D generation, transport | ✅ (11-12) |
| D17 | Linked carbon: what a unit can be | 11-12 | Fused units allowed | Benzene units only | ✅ (11-12) |
| D18 | Fine-tuning route | 11-10 | Small open model with LoRA | Azure OpenAI fine-tuning | ✅ (later) |
| D19 | Objective of the loop after the sensor twin | 11-12 | ✅ Score v2 (sensor twin + DFT-corrected xTB), chosen 11-13 | Twin score (coverage-aware, favours NO₂ binding near −0.75 to −0.8 eV); a mix | ✅ (11-13) |
| D20 | Linked carbon: how units are placed and joined | 11-12 | Rotated coarse grid for directions only; spanning-tree placement; outermost C–H facing the link | Fixed coarse spacing; LLM names the attach atom; free 2D layout | ✅ (L1 agent) |
| D21 | Linked carbon: the reactive triple bond | 11-13 | Nothing yet: wait for the DFT check of a triple-bond site | Keep all links; limit or shield triple bonds; favour ring-site binders with the twin | ❓ |
| D22 | How to handle open-shell character of small-gap GQDs | 11-13 | ✅ xTB N_FOD screen, threshold 2.9 | Open-shell screen (xTB or DFT); raise the gap floor; UKS/BS reference for scoring; keep as is | ✅ (11-13) |
| D23 | Use a second AI model (Azure GPT) to cross-check our work | 11-13 | ✅ gpt-6.1-sol cross-checks facts and figures during research | Blind review of writing; second opinion on decisions; code review; several LLMs as designers (an experiment); not for checking chemistry facts | ❓ |
| D24 | Where to collect the new GQDs found by the evolution loop | 11-13 | ✅ Separate novel-GQD library (`novel_gqds/`) | Separate novel-GQD library (recommended); append to accepted_gqds; leave in run logs | ✅ (11-13) |
| D25 | Keep `accepted_gqds/` now that `novel_gqds/` exists? | 11-13 | Keep it (recommended) | Delete it; merge it into the library | ❓ |
| D26 | Own repository and licence for the Agentic_GQD work | 11-13 | Not decided (ask the professor first) | New separate repo (recommended); restructure the current repo; keep as is | ❓ |

---

## D1. How the LLM creates structures (2026-11-10)
Source: `AGENTS.MD` "Better approaches", `Final_Planning.md`.
- ✅ **Option 2: the LLM writes hexagon coordinates** instead of SMILES. Easy to count, check and edit.
- ✅ **Option 5: LLM-guided evolution.** Score, select, let the LLM edit, validate, repeat.
- ⏸ Option 1: the LLM only picks parameters (ring count, shape, seed) and code grows the structure. Safe, but little LLM creativity. Could be a baseline.
- ⏸ Option 3: the LLM edits existing structures. This became part of Option 5.
- ⏸ Option 4/6: dedicated generative models (SELFIES models, graph or diffusion models on the hexagon grid, REINVENT-style RL). Kept as future work and as extra baselines for a paper.

## D2. Who picks the double bonds (2026-11-10)
- ✅ Our own perfect matching in `Stage1/gqd_hex.py`.
- ❌ RDKit's kekulizer: it failed on some large GQDs depending on atom order.
- Open issue: RDKit cannot re-read about 10 to 14% of valid closed-shell shapes. Revisit if it becomes common.

## D3. Gap predictor (2026-11-10)
- ✅ Hückel baseline, plus a 0.85 GNN + 0.15 XGBoost ensemble predicting the correction, with an uncertainty model. MAE 0.023 eV.
- ❌ Morgan fingerprints: R² 0.36 alone.
- ❌ Mac GPU (MPS): 12× slower than CPU for these graphs.
- ⏸ Drop the GNN to keep one process: costs about 30% accuracy.

## D4. Fixing LLM validity (2026-11-11)
- ✅ Both aids: the closed-shell rule in the prompt and fix edits in the feedback, giving 99% valid.
- ⏸ Fix feedback alone: 90% valid but the most variety. Use it if variety becomes a problem.
- ⏸ Soften the rule text if the LLM keeps repeating safe symmetric shapes.

## D5. Uniqueness and holes (2026-11-11)
- ✅ Children must be new compared with the 91k dataset.
- ✅ Holes are rejected: the predictor is 4× worse on them.
- ⏸ Allow holes with a forced xTB check. Both choices can be changed with flags.

## D6. Design goal (2026-11-12)
- ✅ **One application: NO₂ gas sensing.** The goal comes from what a sensor must do.
- ❌ Hand-picked target gap (minimise, maximise or hit X eV): no physical reason for the number.
- ⏸ Fe³⁺ sensing and fluorescence probes: these need charged-ion or excited-state physics beyond xTB. Possible with TDDFT later.

## D7. Sensing score details (2026-11-12)
- ✅ Score = charge to NO₂ × reversibility (−0.6 to −1.0 eV window) × selectivity (≥ 0.10 eV over H₂O, NH₃, CO).
- ✅ O₂ excluded from the score, because xTB is wrong for O₂; checked with DFT instead.
- ❓ **Replace the response term (now required).** The DFT benchmark (2026-11-13, `Stage3a/results/dft_benchmark.md`) gave Spearman ρ = −0.16 for the score, below the 0.4 threshold of the pre-set rule, so the score must change.
  - Physisorbed NO₂ takes 0.01 e in DFT, against 0.23 e in xTB, so the xTB response is an artefact; DFT scores of all physisorbing GQDs are about 0.
  - xTB still ranks binding (NO₂ ρ 0.74, H₂O 0.85, NH₃ 0.95) and the selectivity margin (0.86) well.
  - Options:
    - (a) **HOMO-based / orbital-alignment response** (GQD HOMO vs NO₂ SOMO). For: cheap; the xTB charge followed the HOMO (r = 0.88), so the physics trend is there. Against: DFT says that trend gives almost no actual charge for physisorption, so a HOMO term would rank a response that may not exist.
    - (b) **DFT charge, final candidates only.** Accurate but too slow for the loop.
    - (c) **A correction learned from DFT data.** Needs more DFT points.
    - (d) **Move the target to weak, reversible chemisorption** (bond at about −0.3 to −0.6 eV), which in DFT keeps about 0.2 e. The only two GQDs with a non-zero DFT score are of this kind.
    - (e) **Sensor-twin response** (carrier change of the film).
  - Recommendation: (d) plus water-aware selectivity as the new loop objective, with the DFT response (b) for final candidates. Keep (a) as a cheap feature, not as the score. Not decided.
- ⏸ **Concentration-aware selectivity** (part of the sensor twin, D15). Rough estimate: at 50% humidity, water may outcompete NO₂ unless NO₂ binds about 0.35 eV more strongly.

## D8. xTB budget in the loop (2026-11-12)
- ✅ Children are scored on NO₂ + CO only (same score on all 50 calibration GQDs), 5 children in parallel, plus the free gap pre-filter.
- ⏸ A surrogate model of the sensing score, trained on the logs once there are enough.
- ❌ Fewer children per generation: fewer data and slower progress.

## D9. Fixes after the pilot (2026-11-12)
- ✅ Code repairs open-shell children; family cap of 3; gap floor 0.30 → 0.20 eV; 4 LLM rounds instead of 3.
- ❌ Only more LLM rounds: did not address duplicates or diversity.

## D10. Where to compute (2026-11-12)
- ✅ Hybrid: the xTB loop on the Mac (the shared server CPU is 6× slower), DFT on server GPU 0 (GPU4PySCF).
- ⏸ Move the whole project to the server: revisit at Stage 5 (fine-tuning needs the GPU).
- ❌ ORCA: not installed; `/usr/bin/orca` on the server is a screen reader.
- ❌ Density fitting on the A100: slower than exact integrals at this size.
- ⏸ Use git as the source of truth for syncing to the server.

## D11. Order of stages (2026-11-12)
- ✅ Stage 4 (LLM vs random on pure carbon) before Stage 3b (dopants), so the comparison is clean and gives a baseline.
- ⏸ Stage 3b: dopants (N, B) and edge groups (–OH, –COOH, –NH₂). The best place for the LLM's chemistry knowledge to beat random.

## D12. Experiment design (2026-11-12)
- ✅ 3 seeds per mutator. With 3 vs 3, a rank test cannot go below p = 0.05, so judge by size and consistency.
- ✅ DFT decision rule fixed in advance: ρ ≥ 0.7 accept xTB; 0.4 to 0.7 re-rank the top GQDs with DFT; < 0.4 change the score.
- ❓ 5 seeds per mutator for a paper.
- ❓ E6: random-generation baseline (no evolution) at the same budget.
- Result (11-12, `Stage3/results/compare_v2.md`): best score random 0.351 ± 0.008 vs LLM 0.344 ± 0.004; mean scored LLM 0.186 vs random 0.163 (LLM higher in all 3 pairs). The differences are small against the run-to-run spread, so the 5-seed option matters more for a paper.

## D13. Thesis framing (2026-11-12)
- ❓ Recommended: present the thesis as a reliable, validated design workflow. LLM vs random is one honest experiment, not the main claim. Waiting for the user's OK to rework the abstract, introduction and hypotheses.
- Evidence (11-12): the Stage 4 result does not support "the LLM finds better GQDs than random" (random found the best GQD in 2 of 3 seed pairs). It does support "LLM edits are better on average". This strengthens the case for the recommended framing; still the user's decision.

## D14. Publication plan (2026-11-12)
- ⏸ Deferred by the user ("we will come to the paper part later").
- Options discussed:
  - **Paper 1:** the pipeline and NO₂ results, for *Digital Discovery* or *J. Chem. Inf. Model.*;
  - a short workshop version of the 99% validity result;
  - a preprint after the DFT results;
  - **Paper 2:** dopants or linked carbon.
- Literature check (web, 11-12): no prior LLM-guided design of GQDs, nanographenes or PAHs found. Neighbours are MolLEO, My Chemical Harness, MatLLMSearch, LLEMA, El Agente, GaUDI and GQD TDDFT/BO studies (see the thesis Chapter 2). A database search is still needed.

## D15. Next direction after the "Cyber Twin" suggestion (2026-11-12)
- The suggestion: start from the application's required functions, turn them into energy, electron and information flow with a "Cyber Twin", and let the AI generate structures that satisfy them, not ring or fusion based.
- ✅ **Build a sensor twin first** (user agreed 2026-11-12: "yes, we can run it if we are free"; built in `Stage3c/`). Molecule (binding, charge) → film (coverage with real concentrations, humidity, kinetics) → device (resistance change, response and recovery time). Then run it backwards: required sensor behaviour → required molecular properties → generator. It is feasible in days and works for GQDs and any new structure class.
- ⏸ Generate directly from targets ("function → structure", Dataset 3 in `AGENTS.MD`).
- ⏸ Quantum-transport conductance change (true electron flow): a big project, future work.

## D16. Structure class beyond fused hexagons (2026-11-12)
- ✅ **Linked carbon (graphyne/graphdiyne fragments and GQD–graphyne hybrids).** Chosen 2026-11-12. The user delegated the choice, asking for the most optimal and accurate option. Accuracy decides it: pure carbon stays in the range where xTB and our DFT checks are reliable, while metal centres (Pc/MOF) have spin states that xTB handles poorly.
  - Most novel per unit of effort; reuses our pipeline.
  - NO₂ sensing on graphyne is shown experimentally, but no design search exists.
  - A 2026 LLM–carbon preprint (Hao et al., APL) does bulk crystals for thermal properties: no overlap.
- ⏸ **Phthalocyanine/MOF building blocks.**
  - Highest application impact, and the most likely place for the LLM to beat random.
  - But it needs metal chemistry, heavy DFT and ideally an experimental partner.
  - Pick this if a partner lab is available.
- ⏸ Non-hexagonal rings (5- and 7-membered): breaks the two-sublattice rule; needs an atom-level representation.
- ⏸ Dopants and edge groups (Stage 3b).
- ⏸ Free atom-level 3D generation: closest to "no rings at all", but a large project.

## D17. Linked carbon: what a unit can be (2026-11-12)
- ✅ Allow fused units (small GQDs) as well as benzene rings. Chosen 2026-11-12, delegated by the user. That covers the whole range from fused to linked, so we can ask "does linking beat fusing for NO₂ sensing?", with our GQD results as the fused baseline.
- ⏸ Benzene units only: pure graphyne/graphdiyne fragments; simpler but narrower.

## D18. Fine-tuning route (2026-11-10)
- ✅ (later, Stage 5) A small open model (7 to 8B) with LoRA, and DPO on better/worse edit pairs. Cheap, controllable and shareable.
- ❌ Azure OpenAI fine-tuning: more cost, less control, and the weights cannot be shared.

## D19. Objective of the loop after the sensor twin (2026-11-12)
- First twin result (`Stage3c/README.md`): at 20 ppb the current best GQDs (NO₂ physisorbed at −0.43 to −0.52 eV) have tiny NO₂ coverage. Humidity swings can mimic about 32 ppb NO₂ for a typical physisorbing GQD. The twin prefers binding near −0.75 to −0.82 eV (xTB), with recovery under about a minute and a signal about 10⁴ times larger. Rank correlation with the Stage 3a score: 0.62.
- ❓ **Switch the loop objective to the twin score.** Decide only after DFT energies: xTB overbinds chemisorbed NO₂ by 0.1 to 0.55 eV, so the window may move.
- ⏸ Keep the Stage 3a score (current choice; all runs so far used it).
- ⏸ A mix: twin signal with a DFT-calibrated binding energy, or a correction of xTB E_NO₂ learned from the GPU benchmark.

## D20. Linked carbon: how units are placed and joined (2026-11-12, Stage 3d L1)
Details and test outputs: `Stage3d/PROGRESS.md`.
- ✅ **The coarse grid gives only neighbours and directions.**
  - Units are placed along a spanning tree of the links, each shifted so the link is straight at its ideal length (4.01 Å for n=1, 6.57 Å for n=2 between attach carbons).
  - Units of any size fit this way.
  - Ring-closing links must fit within 15% / 15°, which also rejects mixed link lengths around a ring.
- ✅ **The grid is rotated by 30° from the hexagon grid.** Link directions then equal the directions edge C–H bonds point, so ring vertices face each other as in γ-graphyne.
- ✅ **Attach carbon:** the outermost edge carbon whose C–H points along the link; ties go to the carbon closest to the unit's centre line.
- ⏸ Fixed coarse spacing: simpler, but cannot hold units of different sizes.
- ⏸ The LLM names the attach atom itself: more freedom, but it needs atom labels the LLM must track, which is error-prone (as with SMILES).
- ⏸ Free 2D layout (any angle): it leaves the grid the LLM reasons on well.
- ⏸ Mixed link lengths in a ring, with strained start geometries left for xTB to relax: rejected for now in L1; revisit if needed.

## D21. Linked carbon: the reactive triple bond (2026-11-13, Stage 3d L2)
- Finding (xTB, 21 designs, `Stage3d/results/summary.md`): 15 of 21 C≡C sites chemisorb NO₂ (median −0.95 eV), so 19 of 21 designs chemisorb. Linked designs score lower on the Stage 3a score (best 0.197 vs 0.322 for fused GQDs). On the twin, the best two designs bind at a fused-unit ring (−0.74 to −0.77 eV), not at a triple bond.
- ❓ **First check with DFT** whether triple-bond chemisorption is as strong as xTB says (bundle ready in `Stage3d/data/dft_check/`, `gdy_rhomb4`). xTB overbinds ring chemisorption by 0.1 to 0.55 eV; the same shift would put many triple-bond sites near the twin's −0.75 eV window.
- ⏸ Keep all link types and let the score decide (current).
- ⏸ Limit or shield triple bonds: fewer links, n=1 only, or links between larger fused units.
- ⏸ Treat triple bonds as the intended binding site and tune their strength (link length, neighbouring units); depends on D19 (which score).


## D22. How to handle open-shell character of small-gap GQDs (2026-11-13, Stage 3a)
- Finding (`Stage3a/results/dft_benchmark.md`, "Broken-symmetry check"; data `Stage3a/data/dft_benchmark/bs_check.jsonl`): at wB97X-V/def2-SVP on the xTB geometry, the three checked GQDs with xTB gap below 0.5 eV have a broken-symmetry UKS solution 0.43 to 0.82 eV below RKS with <S^2> 1.5 to 1.7; gqd_88143 (gap 0.86 eV) is lowered by only 0.04 eV. All have Kekulé structures, so our closed-shell rule does not catch this. With the BS reference, DFT NO₂ binding of llm_s0_g10c004 goes from −1.09 to about −0.27 eV. Only 4 of 12 GQDs checked.
- ❓ **Add an open-shell screen** (e.g. an xTB spin-polarised or fractional-occupation check in the loop, or a BS-UKS DFT check for final candidates): catches the problem directly, at extra cost per child or per candidate.
- ❓ **Raise the gap floor** of the pre-filter (now 0.20 eV) to where the lowering becomes small (between 0.49 and 0.86 eV in the four data points): cheap and fits the existing filter, but the limit is not yet known and it removes the GQDs the loops currently rank highest.
- ❓ **Use a UKS / broken-symmetry reference for the bare GQD when scoring** (xTB and DFT): keeps small-gap GQDs but gives adsorption energies against the lowest state; more calculations, and spin contamination makes energies approximate.
- ❓ **Keep as is** and state it as a limitation: no cost, but the top of the ranking stays tied to a questionable closed-shell reference.
- First step for any option: run the check on the other 8 benchmark GQDs to locate the gap limit.

## D23. A second AI model to cross-check our work (2026-11-13 19:21 CST)
- User's idea: host a recent GPT model on the user's Azure account and call it through the API to cross-check the research.
  - The project already has an Azure GPT-5.4 deployment (`studio/.env`), so the same deployment can be used.
  - Keys stay in `.env`; never pasted in chat, never printed.
- ❓ **Blind reviewer of the thesis and reports:** catches overclaims and gaps. Recommended as the first use.
- ❓ Second opinion on research decisions (e.g. score v2, open-shell filter).
- ❓ Code review of the scripts.
- ⏸ **Several LLMs as the designer in the evolution loop:** a real experiment and a possible paper result.
- ❌ Checking chemistry numbers or facts: two AIs agreeing is not evidence. Ground truth stays DFT, verified literature and experiments. Suggested references must still be verified.
- Watch: Azure cost for long documents; never send confidential material (e.g. the proposal).
- ✅ 2026-11-13 19:42 CST: user deployed **gpt-6.1-sol** (version `gpt-6.1-sol-2026-09-29`) on the existing Azure resource.
  - Main use, as the user explained it: during research, Claude asks this model to cross-check facts and figures.
  - Acceptance test passed: a correct calculation confirmed, a planted error caught, a fake reference refused.
  - Tool: `tools/crosscheck.py`; log: `tools/crosscheck_log.md`. Numbers are still recomputed from the result files first.

### Status update 2026-11-13 22:30 CST
- **D19 ✅ score v2** (`Stage4/score_v2.py`), chosen 2026-11-13 when the user approved the Stage 4 plan.
  - Bonded NO₂ is shifted +0.176 eV; physisorbed charge is set to 0; the signal comes from the sensor twin.
  - Linked-carbon DFT (2026-11-13) shows the shift is far too small for triple bonds (about 0.78 eV), so score v2 needs a separate triple-bond correction before it is used on linked carbon.
- **D22 ✅ xTB N_FOD ≤ 2.9 open-shell screen.** It separates all 12 benchmark GQDs exactly as broken-symmetry DFT does (`Stage4/PROGRESS.md`). Small sample, so it stays under check.

## D24. Where to collect the new GQDs found by the evolution loop (2026-11-13 22:30 CST)
- The user noticed that `accepted_gqds/` holds only 4 GQDs. It is written only by the Studio agent (`save_gqd`); the evolution loop logs its children to `Stage3/results/<run>/children.jsonl`.
- Count at 2026-11-13 22:30 CST: **1,183 unique valid GQDs that are not in the 91k dataset**, from the 8 Mac runs; 696 of them were scored by xTB. The server runs add more.
- ❓ **A separate novel-GQD library**, e.g. `novel_gqds/library.csv`. Recommended.
  - One row per unique structure: SMILES, InChIKey, hexagons, source run and child id, valid, scores (v1 and v2), N_FOD, DFT status.
  - Rebuilt by a script from the logs, so it is always complete.
  - Keeps the agent's own saved list separate.
- ⏸ Append them to `accepted_gqds/accepted_gqds.csv`. That mixes two sources. The agent's uniqueness check would then reject all of them; that may be wanted, but its behaviour changes.
- ❌ Leave them only in the run logs: hard to find, and duplicates across runs are not merged.
- ✅ 2026-11-13 22:39 CST: user chose option A. Built `novel_gqds/library.csv`: 1,183 unique new GQDs.

## D25. Keep `accepted_gqds/` now that `novel_gqds/` exists? (2026-11-13 22:41 CST)
- `studio/agent.py` uses it: `save_gqd` writes accepted designs there, and `check_uniqueness` reads its InChIKeys to reject repeats. It is in git (4 Studio-test GQDs from 2026-11-11, the Stage 0 record).
- ❓ **Keep it** (recommended). It is the Studio agent's working output and tiny. Optionally add its 4 rows to the novel library with source "agent".
- ❌ Delete it: the agent would recreate it on the next save, and the Stage 0 test record would be lost.
- ⏸ Merge: make the agent save into the novel library instead. Possible when the agent is connected to the full workflow (one user-facing tool).

## D26. Own repository and licence for the Agentic_GQD work (2026-11-13 22:53 CST)
- The user's idea: make Agentic_GQD the main experiment and move the previous research (by Nagmani, the parent folder) into a `previous_research/` subfolder with credit, under the user's own repo and licence.
- ❓ **A. A new separate repo** containing only Agentic_GQD, with its git history extracted (subdirectory filter). Recommended.
  - The previous research stays in its own repo and is cited (README, `CITATION.cff`, acknowledgements).
  - One licence, covering only the user's work.
- ⏸ B. Restructure the current repo (`previous_research/` plus Agentic_GQD at the top). It mixes two authors' work, and the user cannot relicense the other author's code without permission.
- ⏸ C. Keep as is and only add a top-level README explaining authorship.
- Before any choice:
  - ask the professor about university/lab IP rules, licence, public vs private (unpublished work, external collaborators);
  - get permission to redistribute the previous author's 91k dataset and xTB data, or document how to obtain them.
- Technical: parent-folder paths (xtb binary, source dataset for `Stage1/build_hex_dataset.py`) must become settings in a new repo.

