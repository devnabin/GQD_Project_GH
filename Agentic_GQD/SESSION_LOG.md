<!-- Created date: 2026-11-11 (America/Chicago) -->

# Session Log

> One entry per working session, newest first. Read the top entry + `WORK_DIRECTION.md` to resume.
> Each entry: what was done, decisions made, open questions, and the exact next action.

---

## 2026-11-12 — Application chosen: NO₂ gas sensing

**Decided**
- The project is built around **one application: NO₂ gas sensing** (the GQD should bind NO₂ more strongly than H₂O, NH₃, CO and O₂, show a clear electronic response, and not bind so strongly that it never releases it). The design goal is set by the application, not just a target gap.
- Fe³⁺ sensing and fluorescence probes are set aside: they need charged-ion or excited-state physics beyond xTB.

**Feasibility test (scratchpad, not in the repo)**
- Homebrew `xtb` 6.7.1 crashes (gfortran format bug). Use the conda-forge build at `../AI_GQD/.env/bin/xtb`.
- One accepted GQD (21 hex), GFN2, analyte placed 3.2 Å above the centre, both optimised: E_ads NO₂ −0.35, CO −0.20, H₂O −0.12, NH₃ −0.11 eV. Only NO₂ changes the gap (0.85 → 0.63 eV). That's about 35 s per GQD for 4 analytes.

**Next action**
- Plan Stage 3a (xTB adsorption workflow + sensing score) and Stage 3b (dopants / edge groups), then the evolution loop with the sensing score. The commit OK and the Studio test rows are still open.

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
