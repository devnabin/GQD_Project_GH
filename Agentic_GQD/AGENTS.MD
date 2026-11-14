## Standing rules for every session (read first)

Added 2026-11-12 at the user's request. These apply in every session, without being asked.

### 1. Session records

- At the start of a session, read the top entry of `SESSION_LOG.md` and `WORK_DIRECTION.md`, and resume from the "Next action".
- At each milestone and before the session ends, add a short entry at the top of `SESSION_LOG.md`: done, decisions, uncommitted work, open questions, next action. Update the Status column of `WORK_DIRECTION.md` when a stage moves forward.

### 2. Keep the thesis up to date (`Report/`)

The thesis draft is `Report/main.tex`, with one file per chapter in `Report/chapters/`, references in `Report/references.bib` and figures in `Report/figures/`. After every new experiment, result, finding or change of method, update the thesis in the same session, together with `SESSION_LOG.md`:

| What happened | Update |
|---|---|
| A method, setting or threshold changed | Chapter 3 (`03_methods.tex`); for loop settings also Table `tab:loop-versions`. Keep the old value too. |
| A new experiment was started or planned | Chapter 4 (`04_experimental_design.tex`): a section with question, design and measures, plus a row and status in Table `tab:experiments` |
| A result came in | Chapter 5 (`05_results.tex`): numbers and tables, with the source file as a LaTeX comment; copy or create the figure in `Report/figures/` |
| The meaning or a limitation changed | Chapter 6 (`06_discussion.tex`) |
| A main number or the answer to a research question changed | the abstract (`00_abstract.tex`) and Chapter 7 (`07_conclusion.tex`) |
| New commands, prompts or logged fields | Appendix C, A or B |

Rules for these updates:

- **Numbers come from the result files, never from memory.** Put the source path in a comment above each table.
- **Results that are not in yet are marked with `\pending{...}`.** Replace a pending item when its result arrives; never delete one without filling it.
- **References must be real.** Add them to `references.bib` only after checking them; mark anything written from memory with `% check`.
- **Writing style:** simple academic English, and none of the patterns on Wikipedia's "Signs of AI writing" list:
  - no em dashes; en dashes only for number ranges in tables;
  - none of the overused words (crucial, pivotal, delve, showcase, underscore, highlight, landscape, robust, comprehensive, notably, additionally, furthermore, moreover, leverage);
  - no rule-of-three padding, no trailing "-ing" clauses, no promotional tone;
  - sentence-case headings;
  - state limitations plainly.
- **Compile check after every update:** `cd Report && latexmk -pdf -interaction=nonstopmode main.tex` must finish with no errors and no undefined references.
- **Commit and push only with the user's OK.**

### 3. Record every option, not only the chosen one (`RESEARCH_OPTIONS.md`)

Whenever the conversation reaches a fork, add it to `RESEARCH_OPTIONS.md` in the same session. A fork can be a decision, alternative methods, a research direction, or a suggestion from the user or advisor. Do this even if no choice is made yet.
- Record **all** options with one line each on why, and mark each one ✅ chosen, ⏸ parked, ❌ rejected (with the reason) or ❓ open.
- Add a row to the index table.
- Never delete an option. When a parked or open option is picked up or decided, update its status and date.

### 4. Log every task with an exact timestamp per entry

Added 2026-11-13 at the user's request: every task we do gets logged, so work is easy to pick up later.
- **Timestamp each log entry, not each line.** Use the time from the computer clock, never an estimate: `date '+%Y-%m-%d %H:%M %Z'` locally, or the server's `date` for server jobs. This applies to `SESSION_LOG.md`, `RESEARCH_OPTIONS.md` entries and stage `PROGRESS.md` files.
- **New files** get a header with date and time from the clock, for example `Created: 2026-11-13 19:25 CST`. When a file changes in a meaningful way, add an `Updated:` line.
- **Scripts that run long jobs** (server queues, loops) write one timestamped line per step to a log file, as `Stage4/overnight.sh` does.
- **Every task is logged.** Each piece of work (a run, an analysis, a decision, a fix) gets a short entry in the stage's `PROGRESS.md`, and a summary in `SESSION_LOG.md` at milestones: what was done, where the outputs are, and what is still running.


### 5. Cross-check important results with a second AI model

Added 2026-11-13 at the user's request (decision D23). Before important numbers, interpretations or claims go into the thesis, a report or slides:
1. Recompute the numbers from the result files with code.
2. Send the key claims to `gpt-6.1-sol` with `tools/crosscheck.py` (logged in `tools/crosscheck_log.md`).
3. Report and investigate any disagreement.

Agreement is a second opinion, not proof. Never paste keys or send confidential material.
---

Better approaches
1. LLM chooses, code builds (my recommendation). Give the agent a build_gqd tool based on the hexagonal-growth code from your reference script (grow_cluster + cluster_to_mol). The LLM chooses parameters such as ring count, shape (round or elongated), edge type, or a random seed, and the code always produces a valid connected structure. The LLM does the reasoning and the code does the chemistry. This fits your current graph: just another tool before the same validation steps.

....................
2 (IMP). LLM writes hexagon coordinates instead of SMILES. A GQD on a hexagonal grid is just a set of hexagon positions, e.g. [(0,0), (1,0), (0,1), …]. An LLM handles that far better than SMILES: it's easy to count, check for connections, and reason about shape. cluster_to_mol then turns it into a molecule. This keeps the LLM creative without asking it to write long SMILES.

5 (IMP). C. LLM-guided evolution (genetic algorithm)
Start with a population of accepted structures.
Score each with xTB (or a fast predictor; see D).
Show the LLM the best structures and their scores, and ask it to suggest changes: add a ring here, remove a corner, merge two shapes.
Code applies the changes, the pipeline validates the results, and you repeat.
This is an active research area (LLMs as mutation operators in molecule design). It uses what LLMs are good at, reasoning about why some shapes score better, without making them write SMILES.

6. (IMP). E. Dedicated generative models
Train a small transformer or RNN on SELFIES, a molecule-string format where every string decodes to a valid molecule, using your generated structures as training data.
Graph-based generators or diffusion models that work directly on the hexagon grid.
Reinforcement learning (REINVENT-style), where the reward is your validation checks plus an xTB or predicted property.
---------------

3. LLM edits existing structures. Start from an accepted structure and let the LLM suggest a change, like "add a ring at this edge" or "remove a corner ring". Code applies the change and your pipeline validates it. This is useful later if you want to improve candidates toward a goal, such as a target band gap from xTB.

4. Specialised chemistry models. If you eventually want a learned generator, models trained on molecules work better than a general LLM. Examples are SELFIES-based models (SELFIES strings always decode to a valid molecule) and graph-based generators. That's a much bigger project than you need right now.

---------------

## Fine-tuning datasets (IMPORTANT)

Saved 2026-11-10. The evolution loop is a data factory: its logs (parent → edit → child → score) plus the existing xTB data become the fine-tuning data.

### Dataset 1: "Good edits" (teaches the model to make better changes)

- **Source:** the evolution logs.
- **One record:** a parent structure plus the goal, paired with an edit that improved the score.

```json
{
  "input": "Goal: gap 2.0 eV. Parent: [(0,0),(1,0),...] | 24 hex | zigzag 10 | gap 2.31",
  "output": "ADD (3,-1). Reason: lengthening lowers the gap. Child: [(0,0),...,(3,-1)]"
}
```

- **Filter:** keep only edits where the child was valid and closer to the target.
- **Teaches:** which edits tend to help, so the model becomes a better mutation operator.

### Dataset 2: "Better vs. worse" pairs (teaches it to prefer good edits)

- **Source:** the evolution logs, using two edits on the same parent.

```json
{
  "input":    "Goal: gap 2.0 eV. Parent: ...",
  "chosen":   "ADD (3,-1) → gap 2.12",
  "rejected": "REMOVE (0,2) → gap 2.90"
}
```

- **Method:** preference training (DPO).
- **Teaches:** to rank edits, using failed edits as well as successful ones. Nothing in the log is wasted.

### Dataset 3: "Target → structure" (teaches it to design directly)

- **Source:** the existing ~16,000 xTB-labelled structures, plus all scored children from the logs.

```json
{
  "input":  "Design a GQD with gap 2.0 eV and 25–30 hexagons.",
  "output": "[(0,0),(1,0),(0,1),...]"
}
```

- **Teaches:** to write a good starting structure for a given property, instead of starting from random ones.
- **Note:** part of this can be built now. It only needs code that converts existing structures into hexagon coordinates (`mol_to_hex`, listed in `Final_Planning.md`).

### How much data

| Source | Rough size |
|---|---|
| Existing xTB dataset | ~16,000 structures (Dataset 3) |
| One evolution run (30 gens × 20 children) | ~600 logged edits |
| 10 runs × 3–4 different gap targets | ~20,000 logged edits (Datasets 1 and 2) |

That's enough to fine-tune a small model with LoRA, a cheap method that trains only a small add-on to the model.

### Which model to fine-tune

- **A small open model (about 7–8B parameters, fine-tuned with LoRA):** cheap, fully under our control, and easy to reproduce for a paper.
- **Azure OpenAI fine-tuning:** fits the current setup, but costs more, gives less control, and the model weights can't be shared.

For research, the small open model is usually the better choice.

### Logging requirement (so these datasets can be built)

Every child in the evolution loop must be logged with at least:
`generation, goal, parent_id, parent_hexagons, parent_score, edit, reason, child_hexagons, valid, reject_reason, predicted_gap, xtb_gap`
