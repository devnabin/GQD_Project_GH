<!-- Created date: 2026-11-10 16:24:30 CST -->
<!-- update date: 2026-11-10 16:28:34 CST -->

# Agentic GQD: first LangGraph setup

The `studio/` folder contains existing LangGraph learning examples and the new GQD graph, `studio/gqd_graph.py`. The GQD graph is registered as `gqd_workflow` in `studio/langgraph.json` for Studio. It has three nodes: find a candidate in the Step 3 pilot CSV, read its recorded graph-check label, and suggest the next step. It does **not** generate molecules, recompute RDKit checks, or run xTB/DFT. A graph-checked label is not proof of a stable GQD.

## Run one candidate

From `Agentic_GQD`:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-gqd.txt
.venv/bin/python run_gqd.py gqd_41091
```

The existing `.venv` can be reused if it already contains LangGraph. To use a different CSV, add `--dataset /path/to/pilot.csv`. The output is a read-only plan, not a new validation result. For candidates already processed in Steps 4–8, consult their latest run folders rather than treating the generic Step 4 suggestion as current status.

## View in LangGraph Studio

From `Agentic_GQD/studio`, run `../.venv/bin/langgraph dev` and open the local Studio URL shown in the terminal. Select `gqd_workflow` and supply input such as `{"candidate_id": "gqd_41091"}`. This local graph reads the pilot CSV from the sibling `AI_GQD` folder.

## Next integrations

1. Add a generator adapter for the author's lattice generator, keeping its outputs separate from the original library.
2. Add deterministic RDKit graph checks and duplicate detection for newly generated SMILES.
3. Read existing Steps 4–8 run manifests and status files, then route each candidate to the first unfinished check.
4. Only after those evidence links work, add optional LLM proposal/review nodes. Scientific pass/fail gates remain code-based.

Local credential files are ignored by `.gitignore`. Do not copy credentials into code or run output.
