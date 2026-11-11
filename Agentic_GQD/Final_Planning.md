<!-- Created date: 2026-11-10 20:32:08 CST (America/Chicago) -->

# Final Planning: LLM-Guided Evolution of GQDs on a Hexagon Grid

## 1. The goal in one paragraph

We want an AI agent that **designs new graphene quantum dot (GQD) structures** and improves them toward a target property, such as a chosen HOMO–LUMO gap from xTB. We will not ask the LLM to write long SMILES strings, because it gets them wrong too often. Instead, the LLM describes each GQD as a **list of hexagon positions** and suggests **small changes** to good structures. Plain code turns those positions into a real molecule, and our five-step validation decides whether to keep it.

**Chosen method = Option 2 (hexagon coordinates) + Option 5 (LLM-guided evolution).**
Option 6 (trained generative models) is kept for later.

---

## 2. Idea 1: describe a GQD as hexagon positions (Option 2)

A GQD is a patch of graphene, and graphene is a grid of hexagons. So a GQD can be written as the list of hexagons it contains:

```
[(0,0), (1,0), (0,1), (1,-1), (-1,1), ...]
```

Each pair `(q, r)` is the position of one hexagon on the grid.

**Why this is better than SMILES for an LLM:**

- **Easy to count.** Number of rings = length of the list.
- **Easy to check.** Two hexagons touch if they are grid neighbours.
- **Easy to reason about shape.** "Add a hexagon on the left edge" or "remove a corner" become simple list edits.
- **Always becomes a valid molecule.** The `cluster_to_mol` code turns the hexagons into carbon atoms and aromatic bonds by fixed rules, so it can't produce broken chemistry.

**Division of work:** the LLM is creative (it picks the shape), and the code does the chemistry (it builds the molecule).

---

## 3. Idea 2: improve structures step by step (Option 5)

This works like a genetic algorithm (an "evolution" loop), but the **LLM chooses the mutations** instead of picking them at random.

1. **Start** with a population of accepted GQDs.
2. **Score** each one with xTB, or with our fast ML predictor.
3. **Select** the best ones.
4. **Ask the LLM** to look at the best structures and their scores, and suggest edits: add a ring here, remove a corner, merge two shapes.
5. **Build and check** each edited structure: `cluster_to_mol`, then the five checks.
6. **Save** the ones that pass, score them, and **go back to step 3**.
7. Repeat for N generations.

**Why use an LLM here:** a random mutation is blind. An LLM can see patterns, such as "structures with more zigzag edges have smaller gaps", and suggest changes that are more likely to help.

---

## 4. How it fits into our LangGraph agent

```
seed population (accepted GQDs)
        ↓
score (xTB / ML predictor) → select best ───┐
        ↓                                   │
LLM proposes edits on hex coordinates       │  repeat for N generations
        ↓                                   │
cluster_to_mol → 5 validation checks → save ┘
```

Each box becomes one node in the LangGraph graph. The five validation checks already exist in `studio/agent.py`:

> check molecular graph → check uniqueness → check ring count (20–40) → check sp² fraction (≥ 0.95) → check SA score (≤ 8.0) → accept and save

---

## 5. What we already have vs. what we need to build

### Already have

| Piece | Where |
|---|---|
| Hexagon-growth generator (`grow_cluster`, `cluster_to_mol`) | `Scripts/01_structure_generation.py` |
| Five-step validation + save | `Agentic_GQD/studio/agent.py` |
| LangGraph agent with an LLM (Azure OpenAI) | `Agentic_GQD/studio/agent.py` |
| xTB calculations (5,000 and 11,000 structures) | `Scripts/06_xtb_calculation_5000.py`, `Scripts/10_xtb_calculation_11000.py` |
| xTB on the top 50 candidates | `Scripts/run_xtb_top50.py` |
| Fast ML property predictor | `Scripts/07_ml_model_training.py`, `Scripts/08_predict_and_select_11000.py` |

### Need to build

1. **`hex_to_mol` tool.** Takes a list of hexagon positions and returns a molecule (reusing `cluster_to_mol`). It should first check that the hexagons are connected and not duplicated.
2. **`mol_to_hex` helper.** Turns existing accepted structures back into hexagon positions so they can seed the population. Alternatively, store the hexagon list next to each structure when we generate it.
3. **`score` node.** Uses the ML predictor for fast scoring, and runs real xTB only on the best few.
4. **`select` node.** Keeps the top structures, plus a few random ones to keep variety.
5. **`propose_edits` node (LLM).** Prompt includes the best structures (hexagon lists + scores) and the target property; output is new hexagon lists.
6. **Loop control.** Number of generations, population size, and the xTB budget.
7. **Logging.** For every generation, save parent → edit → child → score. This becomes our dataset for later fine-tuning.

---

## 6. Build plan (in order)

| Phase | What we do | Done when |
|---|---|---|
| **1** | Add the `hex_to_mol` tool and connect it to the existing five checks | The agent can turn a hand-written hexagon list into an accepted GQD |
| **2** | Ask the LLM to write hexagon lists directly (Option 2 only) | Most LLM-written structures pass validation |
| **3** | Add score → select → propose edits → validate as a loop (Option 5) | The loop runs for several generations without manual help |
| **4** | Run the comparison experiments (Section 7) | We have plots of score vs. number of xTB runs |
| **5** | Write up results; plan Option 6 / fine-tuning | — |

---

## 7. How we will show it works (paper story)

Compare three methods with the **same xTB budget** (the same number of xTB calculations each):

1. **Random generation:** `grow_cluster` with random sizes (our current baseline).
2. **Random mutation:** the same evolution loop, but the edits are random instead of chosen by the LLM.
3. **LLM-guided evolution:** our method.

**What to measure:**

- Best score reached (e.g. how close to the target gap)
- How many xTB runs it took to get there
- Share of proposed structures that pass validation
- Variety of the final structures (not all the same shape)

**Expected result:** if the LLM-guided method reaches better structures with fewer xTB runs, that shows the LLM adds real value.

Run each method several times with different random seeds, so the result isn't luck.

---

## 8. Is it new? (check before claiming)

- Using LLMs as mutation operators for molecules is recent. **MolLEO (2024)** is one example, but it works on drug-like molecules written as SMILES.
- Applying this to **GQDs**, with the LLM editing **hexagon coordinates**, **xTB** as the score, and an **agent workflow** that validates every step, appears to be a gap.

**To do before writing the paper:** search the literature for

- "LLM evolutionary molecular design"
- "MolLEO"
- "large language model genetic algorithm molecules"
- PAH / GQD generative design, e.g. the **COMPAS** PAH datasets
- hexagon/polyhex-based generation of PAHs and nanographenes

---

## 9. Later: Option 6 and fine-tuning

**Option 6 (dedicated generative models)** stays as future work or as an extra comparison:

- A small transformer/RNN trained on **SELFIES** (strings that always decode to a valid molecule)
- Graph or diffusion models working on the hexagon grid
- Reinforcement learning (REINVENT-style), with validation + xTB as the reward

**Fine-tuning an LLM** makes sense only **after** the evolution runs:

- Fine-tuning on structures alone just copies the generator, so it's not worth it.
- Fine-tuning on **property → structure** pairs, or on **edit → improvement** records from our logs, is worth it.
- Use hexagon coordinates or SELFIES as the format, not SMILES.
- A small open model is enough for this narrow task.

Phase A: run the evolution loop with a normal LLM (GPT)
         → every edit, result and score is logged
                    ↓
Phase B: turn the logs (+ your existing xTB data) into training data
         → fine-tune a model
                    ↓
Phase C: swap the fine-tuned model into the same loop
         → compare: random vs normal LLM vs fine-tuned LLM
                    ↓
(optional) repeat: the fine-tuned model makes better logs → fine-tune again


---

## 10. Things to watch out for

- **LLM mistakes in coordinates:** gaps, repeated hexagons, or a structure split into pieces. The `hex_to_mol` tool must catch these and report them clearly.
- **xTB cost:** score with the ML predictor first, and send only the best few to xTB.
- **Loss of variety:** the population can collapse to one shape. Keep some random picks and reject duplicates (the uniqueness check already does this).
- **Predictor errors:** the ML model may be wrong outside its training data. Always confirm final candidates with real xTB.
- **Validation is the final gate:** nothing is accepted without passing the five checks, whatever the LLM claims.

---

## 11. Simple glossary

| Term | Meaning |
|---|---|
| **GQD** | Graphene quantum dot: a small flake of graphene, made of fused hexagons |
| **Hexagon coordinates `(q, r)`** | Position of one hexagon on the honeycomb grid |
| **`cluster_to_mol`** | Code that turns a set of hexagons into an RDKit molecule |
| **SMILES** | Text format for molecules; long and error-prone for large GQDs |
| **SELFIES** | Text format where every string is a valid molecule |
| **xTB** | Fast quantum-chemistry method used to compute properties like the HOMO–LUMO gap |
| **Genetic algorithm / evolution** | Repeat: score → keep the best → change them → score again |
| **Mutation operator** | The rule that changes a structure; here, the LLM |
| **SA score** | Synthetic accessibility score: lower = easier to make |
| **sp² fraction** | Share of atoms that are sp² carbons; graphene-like structures are close to 1.0 |
| **Fine-tuning** | Further training of an existing model on our own data |
