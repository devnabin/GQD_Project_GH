# Stage 4 progress log

Each entry records what was run and what was seen. Commands ran on the server unless stated.

## 2026-11-13 17:35 — Day 1 started

- Server: load about 3 of 32 cores; GPU 0 idle (other users hold memory but use no compute); GPU 1 busy (other user).
- Started `Stage3a/bs_check.py` on GPU 0 for the 8 benchmark GQDs not yet checked (log: `Stage3a/data/dft_benchmark/bs_check.log`).

## 2026-11-13 17:45 — xTB FOD screen calibration (first 4)

`Stage4/fod_screen.py` on the 12 benchmark GQDs → `Stage4/results/fod_benchmark.csv` (server). For the 4 GQDs with a BS-UKS result, N_FOD orders them the same way as the DFT open-shell lowering:

| GQD | BS lowering (eV) | <S²> | N_FOD |
|---|---|---|---|
| llm_s0_g10c004 | 0.82 | 1.67 | 3.74 |
| random_s0_g02c004 | 0.68 | 1.48 | 3.57 |
| gqd_18941 | 0.43 | 1.67 | 3.28 |
| gqd_88143 | 0.04 | 0.62 | 2.65 |

The threshold waits for the other 8 BS results. Note that gqd_13400 (N_FOD 3.13) and gqd_58903 (3.39), the two GQDs with a nonzero DFT score, are in the uncertain range.

## 2026-11-13 18:00 — Score v2 and rescoring

- `Stage4/score_v2.py`: bonded-NO₂ xTB→DFT shift fitted from the benchmark, **+0.176 eV** (7 complexes). Physisorbed NO₂ charge is set to 0. The Stage 3c twin gives the signal.
  - The mean physisorbed offset (+0.217 eV, 41 complexes) is not used. It includes 7 DFT solutions that converged to a charge-separated state.
- `Stage4/rescore.py` → `Stage4/results/rescored.csv` and `rescore_summary.md` (server).
  - 849 structures: 828 fused, 21 linked. 326 have score v2 > 0.
  - For 738 loop children, H₂O and NH₃ were filled with calibration medians (flagged).
- **Top 25:** all have bonded NO₂ at xTB −0.96 to −1.03 eV (about −0.79 to −0.85 after the correction), with predicted recovery 15–276 s. 6 are linked designs, with gaps of 1.7–2.5 eV.
- **Caveats:**
  - The selection sits at the edge of the 5-min recovery spec, so it is sensitive to the 0.18 eV correction: 0.1 eV is about a factor of 50 in recovery time.
  - The correction comes from C–N bonds at GQD rings. Bonds at linked-carbon triple bonds are not in the benchmark.
  - DFT confirmation is required.

## 2026-11-13 18:00 — Open-shell check: 6 of 12 done

| GQD | BS lowering (eV) | <S²> | N_FOD |
|---|---|---|---|
| gqd_13400 | 0.27 | 1.36 | 3.13 |
| gqd_58903 | 0.26 | 1.45 | 3.39 |

- Both GQDs that kept a nonzero DFT score in the benchmark are partly open-shell.
- So far the onset lies between N_FOD 2.65 (gqd_88143, closed-shell) and 3.13 (gqd_13400, open-shell). The threshold waits for the last 6.
- Caveat: the +0.176 eV bonded-NO₂ correction was fitted with closed-shell (RKS) references, partly on these open-shell GQDs. It may be biased; revisit after the threshold is set.

## 2026-11-13 18:05 — Loop supports score v2

- `Stage3/evolve.py`: new options `--score v2 --fod-max X`. The default stays v1, so old runs are unchanged and resumable. Backup of the previous version is in the session scratchpad.
- `Stage4/v2_loop.py`, per child:
  - xTB for NO₂, CO and H₂O (NH₃ filled with the calibration median);
  - N_FOD on the optimised GQD;
  - score v2, set to 0 if N_FOD > fod_max;
  - all geometries kept under `results/<run>/geometries/`, ready for DFT.
- New LLM system prompt for v2, describing the target (weak NO₂ bond at about −0.9 to −1.05 eV in xTB, recovery ≤ 5 min, closed-shell).
- The professor allows as much server CPU as we can use. Running 26 xTB jobs (top-80 FOD screen and calibration FOD), load about 30/32.

## 2026-11-13 19:05 — Open-shell threshold set; closed-shell candidate list

Broken-symmetry check finished for all 12 benchmark GQDs (`Stage3a/data/dft_benchmark/bs_check.jsonl`).
- Closed-shell (BS lowering ≤ 0.07 eV): gqd_26676, gqd_16232, gqd_48745 (0.00), gqd_23775 (0.07), gqd_88143 (0.04). Their N_FOD is 1.68–2.65.
- Open-shell (lowering 0.13–0.82 eV): gqd_23821, gqd_13400, gqd_58903, gqd_18941, random_s0_g02c004, llm_s0_g10c004, gqd_10544. Their N_FOD is 3.13–4.15.
- **N_FOD separates the two groups without error on all 12. Threshold set to N_FOD ≤ 2.9** (between 2.65 and 3.13).
  - Small sample. N_FOD also grows with size; check it on larger structures later.

Applied to the top 80 score-v2 candidates (`Stage4/results/fod_candidates.csv`): **20 are closed-shell (9 fused, 11 linked).**
- Top: random_v2_s2/g02c012 (fused, gap 0.81, score v2 0.247), then linked gdy_row5, gy_hex7, gy_rhomb9, gdy_rhomb4, naph_tri3_n2, gdy_ring6, ovalene_dimer_n1.
- Linked carbon makes up most of the closed-shell list. Its gaps are larger (1.7–2.5 eV) and N_FOD lower (0.9–2.7).
- Of the 50 calibration GQDs (the starting pool), 31 are closed-shell (`Stage4/results/fod_calibration.csv`).
- Caveat: the +0.176 eV correction is untested for NO₂ bonded at triple bonds. The linked candidates need DFT before any claim.

## 2026-11-13 19:10 — Overnight queue started (`Stage4/overnight.sh`, log `Stage4/overnight.log`)

Candidates for DFT were chosen by score v2 among the closed-shell ones (N_FOD ≤ 2.9): 4 linked and 4 fused.
- Linked: gdy_row5, gy_hex7, gy_rhomb9, gdy_rhomb4.
- Fused: random_v2_s2/g02c012, gqd_64256, llm_v2_s3/g01c013, random_s0/g01c009.

What runs:
- **GPU 0:**
  - DFT on the linked set (`Stage4/dft_linked`, 100 SCFs; the small molecules take about 30 s each);
  - then DFT on the fused set (`Stage4/dft_fused`, once its xTB geometries are done);
  - then a broken-symmetry check of all 8.
- **CPU:**
  - xTB geometries of the fused set (`Stage3a/make_geometries.py`, parallel 2);
  - a smoke test of the score-v2 loop (1 generation, 2 children). Only if it scores a child do the runs start: `llm_sv2_s1` with `random_sv2_s1`, then `llm_sv2_s2` with `random_sv2_s2`. Each runs 10 generations × 10 children, `--parallel 2 --workers 6 --fod-max 2.9`.

At 19:11, all three chains were working: GPU DFT 8/100, the smoke-test pool built (50 score-v2 GQDs), fused geometries running.

## 2026-11-13 19:16 CST — Logging rule

The user asked that every task be logged, with an exact clock timestamp per entry (not per line). Added as rule 4 in `AGENTS.MD` and saved in memory. Earlier entry times in this file were written by hand and may be off by a few minutes. From here on, times come from `date`.

## 2026-11-13 22:14 CST — Linked-carbon DFT done (server: `Stage4/dft_linked/summary.csv`, per-complex `*/dft.csv`)

100 SCFs, all converged; finished 20:51 (queue log). For all 4 linked candidates (gdy_rhomb4, gdy_row5, gy_hex7, gy_rhomb9), NO₂ bonds at a triple bond (d about 1.46–1.48 Å):

| | xTB | DFT (ωB97X-V/def2-SVP, single points at xTB geometries) |
|---|---|---|
| NO₂ binding | −0.98 to −1.03 eV | **−0.21 to −0.25 eV** |
| charge to NO₂ | 0.22–0.24 e | **0.17–0.18 e (real)** |
| NO₂ vs strongest interferent | +0.4 to +0.6 eV over CO | **−0.08 to +0.01 eV; H₂O binds as strongly** |
| O₂ binding | — | +0.25 to +0.27 eV (unbound) |

- **xTB overbinds NO₂ at triple bonds by about 0.78 eV.** That is far more than the +0.176 eV ring-bond correction in score v2, so the score-v2 values of the linked candidates are too optimistic.
- The bonded state does carry real charge transfer in DFT.
- Caveat: these are single points at xTB geometries. A DFT-optimised geometry would bind at least as strongly, so −0.23 eV is the weakest the binding can be. One DFT optimisation of a bonded complex is needed before concluding.
- Search runs at 22:13: llm_sv2_s1 at gen 5, best 0.224 (start 0.148); random_sv2_s1 at gen 4, best 0.148.
- DFT on the fused candidates: 30 of 58 SCFs.

## 2026-11-13 22:30 CST — Routine checkup of Agentic_GQD

- **Fixed:**
  - added `Stage4/README.md` and `tools/README.md`;
  - documented the score v2 option in `Stage3/README.md`;
  - added rows 3c, 3d and 4b to `WORK_DIRECTION.md`;
  - marked D19 (score v2) and D22 (N_FOD ≤ 2.9) as chosen in `RESEARCH_OPTIONS.md`;
  - copied `Stage4/results` from the server to the Mac as a backup.
- **Open:**
  - the thesis does not yet cover Stages 3c, 3d and 4 (rule 2); planned for the morning, after the fused DFT results and a cross-check;
  - nothing committed since 04dd140 (needs the user's OK);
  - an exported chat transcript sits untracked in the project root (user to decide);
  - the DFT folders and the new score-v2 runs exist only on the server until they finish.

## 2026-11-13 22:39 CST — Novel GQD library built (D24, option A)

`novel_gqds/build_library.py` → `novel_gqds/library.csv` and `summary.md` (built from the 8 Mac runs).
- **1,183 unique new GQDs**: 374 found first by LLM edits, 809 by random edits.
- 696 scored by xTB; 695 have score v2 (268 above 0); 58 open-shell screened (6 closed-shell); 5 went through GPU DFT.
- 97 have no InChIKey (RDKit InChI kekulisation limit).
- The server score-v2 runs are not included yet: rebuild after they finish and are copied back.
- 2026-11-13 22:47 CST: saved the three architecture diagrams to SYSTEM_ARCHITECTURE.md
