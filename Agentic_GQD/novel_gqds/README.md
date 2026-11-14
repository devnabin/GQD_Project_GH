<!-- Created: 2026-11-13 22:39 CST -->

# Novel GQD library

Every **new** GQD found by the evolution loop, in one table. Each one is valid (passed the agent's checks), closed-shell (Kekulé), has no holes, and is **not in the 91k dataset**. Built from all run logs by `build_library.py` (decision D24, option A).

```bash
.venv/bin/python novel_gqds/build_library.py   # rebuild after new runs → library.csv, summary.md
```

- `library.csv`: one row per unique structure (merged across runs). Columns:
  - identity: library id, SMILES, InChIKey, hexagons;
  - provenance: where it was first found and by which mutator, how often, in which runs;
  - xTB numbers;
  - scores and screening: old score v1, score v2, N_FOD open-shell screen, DFT status.
- `summary.md`: counts.
- Do not edit `library.csv` by hand: it is derived from the logs, so rebuild it instead.
- `accepted_gqds/` is separate: it holds only GQDs saved by the Studio agent.

**Caveats:**
- **score_v1** is the old Stage 3a score, which DFT showed rewards an xTB artefact. Use **score_v2** and **N_FOD**.
- The open-shell screen has only been run for the top candidates so far.
- For 97 structures RDKit cannot make an InChIKey (its known kekulisation limit); the SMILES and hexagons are still valid.
