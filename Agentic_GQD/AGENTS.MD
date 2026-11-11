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
