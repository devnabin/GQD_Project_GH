# Created date: 2026-11-12 (America/Chicago)
"""Stage 3: evolution loop that improves GQDs for NO2 sensing.

    .venv/bin/python Stage3/evolve.py --run llm_s0 --mutator llm
    .venv/bin/python Stage3/evolve.py --run random_s0 --mutator random     # control, same xTB budget

One generation:
  1. The population is the best GQDs scored so far (start: the top of the Stage 3a calibration set).
  2. The mutator proposes children as hexagon edits (ADD / REMOVE) on a parent:
       llm    - the agent's LLM sees the population with its xTB numbers and last generation's
                results, and gives a reason for each edit; rejected children go back to it with
                the reason (same fix feedback as Stage 2d)
       random - random single-hexagon edits (the control)
  3. Code applies the edits and validates the child: the agent's checks (closed-shell, 20-40
     hexagons, sp2, SA), new in this run, not in the 91k dataset, no holes.
  4. The Stage 2 gap predictor (free) skips children outside GAP_WINDOW.
  5. xTB scores up to --children of them (Stage 3a sensing score, NO2 + CO only).
  6. The next population = the best --population GQDs scored so far.
At the end, the best new GQDs get the full Stage 3a check (+ H2O, NH3, O2): final_check.csv.

Everything is logged to results/<run>/ (children.jsonl has the AGENTS.md fields for every
child, rejected ones too). Restarting with the same --run resumes after the last finished
generation.
"""

import argparse
import gzip
import json
import math
import os
import random
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from rdkit import Chem, RDLogger

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "studio"))
load_dotenv(ROOT / "studio" / ".env")
# The random mutator never calls the LLM. Without studio/.env (e.g. on a server that has no
# key), placeholders let agent.py build its client; real values from .env always win.
NO_KEY = "missing: put the Azure settings in studio/.env"
for _name, _value in [("AZURE_OPENAI_API_KEY", NO_KEY), ("AZURE_OPENAI_DEPLOYMENT_NAME", NO_KEY),
                      ("AZURE_OPENAI_ENDPOINT", "https://missing.invalid")]:
    os.environ.setdefault(_name, _value)

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage  # noqa: E402

import agent  # noqa: E402  (the agent's LLM, hexagon rules and validation checks)
from Stage1.gqd_hex import OPEN_SHELL, HexError, _single_edits, hex_to_mol, open_shell_fixes  # noqa: E402
from Stage2.features import compute_features  # noqa: E402
from Stage2.predictor import GapPredictor  # noqa: E402
from Stage3a.sensing import (ANALYTES, E_HARD, E_SOFT, LOOP_ANALYTES, SEL_MARGIN,  # noqa: E402
                             adsorption_sites, evaluate_gqd, gqd_geometry, sensing_numbers)

RDLogger.DisableLog("rdApp.*")
RESULTS = HERE / "results"
SIZE = (agent.MIN_HEX, agent.MAX_HEX)
# Below ~0.2 eV almost every calibration GQD chemisorbs NO2; above 1.6 eV the charge to NO2 is smallest.
# (Pilot: the floor was 0.30 eV, and the best LLM GQDs sat right on it at 0.29-0.33 eV, so it is now 0.20.)
GAP_WINDOW = (0.20, 1.60)
GOAL = "maximise the NO2 sensing score (charge to NO2 x reversibility x selectivity vs CO)"
KNOWN_CACHE = ROOT / "Stage1" / "data" / "known_canonical_smiles.txt.gz"
MAX_ROUNDS = {"llm": 4, "random": 50}  # proposal rounds per generation (validation is free)
# Score v2 (Stage 4, --score v2): DFT-corrected xTB + sensor twin + open-shell (N_FOD) filter.
GOAL_V2 = ("maximise the predicted NO2 sensor signal (score v2: weak reversible NO2 bond, recovery <= 5 min, "
           "closed-shell only)")

SYSTEM = (
    "You improve graphene quantum dots (GQDs) for an NO2 gas sensor. A GQD is a set of fused hexagons on a "
    "honeycomb grid, written as [q, r] positions. " + agent.HEXAGON_RULES + " "
    "How a GQD is scored (xTB calculations; higher is better): sensing score = charge moved to NO2 (e) "
    f"x reversibility x selectivity. Reversibility is 1 if NO2 binds no more strongly than {E_SOFT} eV (so it "
    f"can leave again) and falls to 0 at {E_HARD} eV (NO2 forms a chemical bond and stays). Selectivity is 1 if "
    f"NO2 binds at least {SEL_MARGIN} eV more strongly than CO, the strongest competing gas. NO2 is tested above "
    "two hexagons of each GQD: the most central one and the most exposed edge one. "
    "You make children by editing a parent: ADD [q, r] puts a new hexagon next to the shape, REMOVE [q, r] takes "
    "one away (the rest must stay connected). Each child is 1-3 edits on one parent. A child must be a new "
    "structure (not made before in this run and not in our 91k-structure dataset), closed-shell, 20-40 hexagons, "
    "without holes. If a child is open-shell, code first tries to repair it by adding or removing one hexagon "
    "(shown in the results as 'code added ...'). If a child is still rejected, any fix edits in the message "
    "apply to the child, so append one to that child's edits. Study how the high-scoring GQDs differ from the low-scoring ones, then propose edits you "
    "expect to raise the score: mostly refinements of the best parents, plus a few bolder changes."
)


class Edit(BaseModel):
    op: Literal["ADD", "REMOVE"]
    q: int
    r: int


class Child(BaseModel):
    parent_id: str = Field(description="id of the parent GQD, exactly as shown")
    edits: list[Edit] = Field(description="1-3 hexagon edits applied to the parent")
    reason: str = Field(description="one sentence: why this change should raise the sensing score")


class Proposals(BaseModel):
    """Children to make from the current population."""
    children: list[Child]


# ----------------------------------------------------------------------------
# Structures
# ----------------------------------------------------------------------------
SYSTEM_V2 = (
    "You improve graphene quantum dots (GQDs) for an NO2 gas sensor. A GQD is a set of fused hexagons on a "
    "honeycomb grid, written as [q, r] positions. " + agent.HEXAGON_RULES + " "
    "How a GQD is scored (score v2, xTB checked against DFT; higher is better): the predicted sensor signal "
    "for 20 ppb NO2 in humid air. A real signal needs NO2 to form a weak chemical bond with the GQD: binding "
    "(xTB) of about -0.9 to -1.05 eV gives real charge transfer and still lets NO2 leave within 5 minutes. "
    "Weaker binding (physisorption) gives almost no signal, and stronger binding never recovers. GQDs with "
    "open-shell (radical) character, measured by N_FOD from xTB, score 0; very small gaps are often open-shell. "
    "NO2 is tested above two hexagons of each GQD: the most central one and the most exposed edge one. "
    "You make children by editing a parent: ADD [q, r] puts a new hexagon next to the shape, REMOVE [q, r] takes "
    "one away (the rest must stay connected). Each child is 1-3 edits on one parent. A child must be a new "
    "structure (not made before in this run and not in our 91k-structure dataset), closed-shell, 20-40 hexagons, "
    "without holes. If a child is open-shell, code first tries to repair it by adding or removing one hexagon "
    "(shown in the results as 'code added ...'). If a child is still rejected, any fix edits in the message "
    "apply to the child, so append one to that child's edits. Study how the high-scoring GQDs differ from the "
    "low-scoring ones, then propose edits you expect to raise the score: mostly refinements of the best "
    "parents, plus a few bolder changes."
)


def known_smiles() -> set[str]:
    """Canonical SMILES of the 91k dataset (cached; the first build takes about 1 min)."""
    if KNOWN_CACHE.exists():
        with gzip.open(KNOWN_CACHE, "rt") as handle:
            return set(handle.read().split())
    smiles = pd.read_csv(ROOT / "Stage1" / "data" / "gqd_hex_dataset.csv", usecols=["SMILES"]).SMILES
    known = {Chem.CanonSmiles(s) for s in smiles}
    with gzip.open(KNOWN_CACHE, "wt") as handle:
        handle.write("\n".join(sorted(known)))
    return known


def apply_edits(cells, edits):
    """Apply [(op, q, r), ...] to a hexagon list. Returns (new_cells, error)."""
    new = [tuple(c) for c in cells]
    for op, q, r in edits:
        cell = (int(q), int(r))
        if op == "ADD":
            if cell in new:
                return None, f"ADD [{q}, {r}]: that hexagon is already in the parent"
            new.append(cell)
        elif op == "REMOVE":
            if cell not in new:
                return None, f"REMOVE [{q}, {r}]: that hexagon is not in the parent"
            new.remove(cell)
        else:
            return None, f"unknown edit {op}"
    return new, ""


def edit_text(edits) -> str:
    return "; ".join(f"{op} [{q}, {r}]" for op, q, r in edits)


def validate(cells, known, seen) -> dict:
    """The agent's checks, plus: new in this run, not in the 91k dataset, no holes."""
    try:
        mol = hex_to_mol(cells, feedback=True, size_range=SIZE)
    except HexError as error:
        return {"valid": False, "reject_reason": f"molecular graph: {error}"}
    smiles = Chem.MolToSmiles(mol)
    state = {"smiles": smiles}
    for check in (agent.check_ring_count, agent.check_sp2, agent.check_sa_score):
        result = check(state)
        state |= result
        if result.get("rejection"):
            return {"valid": False, "reject_reason": result["rejection"], "smiles": smiles}
    if smiles in seen:
        return {"valid": False, "reject_reason": "duplicate: this structure was already made in this run",
                "smiles": smiles}
    if smiles in known:
        return {"valid": False, "reject_reason": "not new: already in the 91k-structure dataset", "smiles": smiles}
    holes = compute_features(mol, cells)["hole_count"]
    if holes:
        return {"valid": False, "reject_reason": f"has {holes:.0f} hole(s) (an empty region enclosed by hexagons)",
                "smiles": smiles}
    return {"valid": True, "reject_reason": "", "smiles": smiles}


def validate_or_repair(cells, known, seen):
    """validate(); if the child is open-shell, code tries the Stage 1 single-hexagon fixes.

    Returns (cells, result, repair): the (possibly repaired) child, the validation result and
    the repair edit ("" if none). The mutator's idea is kept; code only makes it closed-shell.
    """
    result = validate(cells, known, seen)
    if result["valid"] or OPEN_SHELL not in result["reject_reason"]:
        return cells, result, ""
    single, _ = open_shell_fixes(cells, SIZE)
    for fix in single:
        op, position = fix.split(" ", 1)
        fixed, error = apply_edits(cells, [(op, *json.loads(position))])
        if not error:
            repaired = validate(fixed, known, seen)
            if repaired["valid"]:
                return fixed, repaired, fix
    return cells, result, ""


def member(record) -> dict:
    """The fields of a scored GQD that the loop and the LLM use."""
    keys = ["id", "hexagons", "smiles", "n_hex", "xtb_gap", "sensing_score", "E_NO2_eV", "E_CO_eV",
            "NO2_chemisorbed", "NO2_site", "NO2_site_cell", "charge_to_NO2_e", "selectivity_margin_eV",
            "all_converged", "generation", "root", "N_FOD", "v2_recovery_s"]
    return {k: record.get(k) for k in keys}


def initial_pool(score="v1", fod_max=None) -> list[dict]:
    """The 50 Stage 3a calibration GQDs (scored with all gases; CO was always the strongest interferent)."""
    cal = pd.read_csv(ROOT / "Stage3a" / "data" / "calibration.csv")
    hexes = pd.read_csv(ROOT / "Stage1" / "data" / "gqd_hex_dataset.csv", usecols=["Structure_Name", "hexagons"])
    rows = cal.merge(hexes, on="Structure_Name").to_dict("records")
    if score == "v2":
        from Stage4.v2_loop import apply_v2, calibration_fod
        fods = calibration_fod({r["Structure_Name"]: json.loads(r["hexagons"]) for r in rows})
    pool = []
    for row in rows:
        row |= sensing_numbers(row)
        if score == "v2":
            row = apply_v2(row, fods[row["Structure_Name"]], fod_max)
        cells = [tuple(c) for c in json.loads(row["hexagons"])]
        _, coords, rings = gqd_geometry(cells)
        sites = adsorption_sites(cells, rings, coords)
        site = row["site_NO2"].split("/")[0]
        pool.append(member(row | {"id": row["Structure_Name"], "hexagons": [list(c) for c in cells],
                                  "smiles": Chem.CanonSmiles(row["SMILES"]), "xtb_gap": row["gqd_gap_eV"],
                                  "NO2_site": site, "NO2_site_cell": list(cells[sites[site]]), "generation": 0,
                                  "root": row["Structure_Name"]}))
    return pool


def select(pool, size, family_cap=0) -> list[dict]:
    """The best `size` converged GQDs, at most `family_cap` from one starting GQD (0 = no cap).

    The cap keeps the population diverse: in the pilot, all 8 LLM parents ended up descending
    from a single starting GQD.
    """
    ok = sorted((p for p in pool if p["all_converged"] and p["sensing_score"] is not None),
                key=lambda p: -p["sensing_score"])
    chosen, per_family = [], Counter()
    for p in ok:
        family = p.get("root") or p["id"]
        if family_cap and per_family[family] >= family_cap:
            continue
        chosen.append(p)
        per_family[family] += 1
        if len(chosen) == size:
            break
    return chosen


# ----------------------------------------------------------------------------
# Mutators
# ----------------------------------------------------------------------------
def describe(p) -> str:
    bond = "chemisorbed (bonded)" if p["NO2_chemisorbed"] else "physisorbed"
    cells = json.dumps([list(c) for c in p["hexagons"]], separators=(",", ":"))
    if p.get("N_FOD") is not None and p.get("v2_recovery_s") is not None:
        return (f"{p['id']} | score v2 {p['sensing_score']:.3f} | {p['n_hex']} hexagons | gap {p['xtb_gap']:.2f} eV | "
                f"NO2 {p['E_NO2_eV']:+.2f} eV (xTB), {bond}, best at the {p['NO2_site']} hexagon {p['NO2_site_cell']} | "
                f"predicted recovery {p['v2_recovery_s']:.3g} s | N_FOD {p['N_FOD']:.2f}\n  hexagons: {cells}")
    return (f"{p['id']} | score {p['sensing_score']:.3f} | {p['n_hex']} hexagons | gap {p['xtb_gap']:.2f} eV | "
            f"NO2 {p['E_NO2_eV']:+.2f} eV, {bond}, best at the {p['NO2_site']} hexagon {p['NO2_site_cell']}, "
            f"charge {p['charge_to_NO2_e']:.2f} e | NO2 vs CO margin {p['selectivity_margin_eV']:+.2f} eV\n"
            f"  hexagons: {cells}")


def outcome(rec) -> str:
    if rec.get("evaluated"):
        bond = "chemisorbed" if rec["NO2_chemisorbed"] else "physisorbed"
        return (f"score {rec['sensing_score']:.3f} (parent {rec['parent_score']:.3f}); NO2 {rec['E_NO2_eV']:+.2f} eV "
                f"{bond}, gap {rec['xtb_gap']:.2f} eV, charge {rec['charge_to_NO2_e']:.2f} e")
    return "not scored: " + (rec.get("skip_reason") or rec.get("reject_reason") or "")[:220]


class LLMMutator:
    def __init__(self, log_path):
        if os.environ["AZURE_OPENAI_API_KEY"] == NO_KEY:
            sys.exit("the llm mutator needs the Azure key in studio/.env (the random mutator does not)")
        self.llm = agent.llm.with_structured_output(Proposals, method="function_calling")
        self.log_path = log_path
        self.messages = []

    def start(self, generation, population, history):
        text = [f"Generation {generation}. Goal: {GOAL}.", "", "Current population (best first):"]
        text += [describe(p) for p in population]
        if history:
            text += ["", "Last generation's children (parent -> edits -> result):"]
            text += [f"- {r['parent_id']} -> {r['edit']}"
                     + (f" (code added {r['repair']} to make it closed-shell)" if r.get("repair") else "")
                     + f" -> {outcome(r)}" for r in history]
        self.messages = [SystemMessage(content=SYSTEM), HumanMessage(content="\n".join(text))]
        self.generation = generation

    def propose(self, n, round_no, feedback, rng):
        if feedback:
            self.messages.append(HumanMessage(content=feedback + f"\n\nPropose {n} more children "
                                              "(do not repeat rejected ones)."))
        else:
            self.messages[-1] = HumanMessage(content=self.messages[-1].content + f"\n\nPropose {n} children.")
        reply = None
        for attempt in range(3):
            try:
                reply = self.llm.invoke(self.messages)
                break
            except Exception as error:  # rate limit, timeout, malformed tool call
                error_text = repr(error)[:300]
                time.sleep(5 * (attempt + 1))
        with self.log_path.open("a") as handle:
            handle.write(json.dumps({"generation": self.generation, "round": round_no,
                                     "prompt": self.messages[-1].content,
                                     "reply": reply.model_dump() if reply else None,
                                     "error": None if reply else error_text}) + "\n")
        if reply is None:
            return []
        self.messages.append(AIMessage(content=json.dumps(reply.model_dump())))
        return [{"parent_id": c.parent_id, "edits": [(e.op, e.q, e.r) for e in c.edits], "reason": c.reason}
                for c in reply.children]


class RandomMutator:
    def __init__(self, log_path=None):
        pass

    def start(self, generation, population, history):
        self.population = population

    def propose(self, n, round_no, feedback, rng):
        out = []
        for _ in range(n):
            parent = rng.choice(self.population)
            cells, edits = frozenset(map(tuple, parent["hexagons"])), []
            for _ in range(rng.choice([1, 1, 2])):
                text, cells = rng.choice(list(_single_edits(cells, SIZE)))
                op, position = text.split(" ", 1)
                edits.append((op, *json.loads(position)))
            out.append({"parent_id": parent["id"], "edits": edits, "reason": "random edit"})
        return out


# ----------------------------------------------------------------------------
# Loop
# ----------------------------------------------------------------------------
def to_json(record) -> str:
    def default(value):
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, (set, tuple)):
            return list(value)
        raise TypeError(type(value))
    return json.dumps(record, default=default)


def score_child(rec, args) -> None:
    start = time.time()
    try:
        if args.score == "v2":
            from Stage4.v2_loop import evaluate_v2
            res = evaluate_v2(rec["child_hexagons"], threads=args.threads, workers=args.workers,
                              keep_dir=RESULTS / args.run / "geometries" / rec["child_id"], fod_max=args.fod_max)
        else:
            res = evaluate_gqd(rec["child_hexagons"], threads=args.threads, workers=args.workers,
                               analytes=LOOP_ANALYTES)
    except Exception as error:
        rec |= {"evaluated": False, "skip_reason": f"xTB failed: {error!r}"[:300]}
        return
    site = res["site_NO2"].split("/")[0]
    rec |= {k: v for k, v in res.items() if k != "details"}
    rec |= {"evaluated": True, "xtb_gap": res["gqd_gap_eV"], "NO2_site": site,
            "NO2_site_cell": res["site_cells"][site], "xtb_details": res["details"],
            "xtb_seconds": round(time.time() - start, 1)}


def run_generation(gen, population, pool_by_id, mutator, history, ctx, args) -> list[dict]:
    rng = random.Random(f"{args.seed}:{gen}")
    mutator.start(gen, population, history)
    need, chosen, records, feedback = args.children, [], [], ""
    for round_no in range(1, MAX_ROUNDS[args.mutator] + 1):
        missing = need - len(chosen)
        if missing <= 0:
            break
        n_ask = missing + math.ceil(missing / 2) if args.mutator == "llm" else missing * 3
        proposals = mutator.propose(n_ask, round_no, feedback, rng)
        batch, notes = [], []
        for i, prop in enumerate(proposals, 1):
            parent = pool_by_id.get(prop["parent_id"])
            rec = {"run": args.run, "mutator": args.mutator, "generation": gen, "goal": GOAL, "round": round_no,
                   "child_id": f"g{gen:02d}c{len(records) + 1:03d}", "parent_id": prop["parent_id"],
                   "parent_hexagons": parent["hexagons"] if parent else None,
                   "parent_score": parent["sensing_score"] if parent else None,
                   "edit": edit_text(prop["edits"]), "reason": prop["reason"], "child_hexagons": None,
                   "valid": False, "reject_reason": "", "skip_reason": "", "predicted_gap": None,
                   "predicted_gap_sigma": None, "evaluated": False, "xtb_gap": None, "sensing_score": None,
                   "repair": "", "root": parent.get("root") if parent else None}
            records.append(rec)
            if parent is None:
                rec["reject_reason"] = f"unknown parent id {prop['parent_id']}"
            elif not 1 <= len(prop["edits"]) <= 3:
                rec["reject_reason"] = f"{len(prop['edits'])} edits; a child must have 1-3"
            else:
                cells, error = apply_edits(parent["hexagons"], prop["edits"])
                if error:
                    rec["reject_reason"] = error
                else:
                    cells, result, rec["repair"] = validate_or_repair(cells, ctx["known"], ctx["seen"])
                    rec["child_hexagons"] = [list(c) for c in cells]
                    rec["n_hex"] = len(cells)
                    rec |= result
            if rec["valid"]:
                ctx["seen"].add(rec["smiles"])
                batch.append(rec)
            else:
                notes.append(f"- #{i} ({rec['parent_id']}: {rec['edit']}): rejected, {rec['reject_reason']}")
        if batch:  # free gap pre-filter
            predicted = ctx["predictor"].predict(hexagons=[r["child_hexagons"] for r in batch])
            for rec, gap, sigma in zip(batch, predicted.gap_pred_eV, predicted.sigma_eV):
                rec["predicted_gap"], rec["predicted_gap_sigma"] = float(gap), float(sigma)
                if not GAP_WINDOW[0] <= gap <= GAP_WINDOW[1]:
                    rec["skip_reason"] = (f"predicted gap {gap:.2f} eV is outside the useful window "
                                          f"{GAP_WINDOW[0]}-{GAP_WINDOW[1]} eV")
                    notes.append(f"- {rec['parent_id']}: {rec['edit']}: valid, but {rec['skip_reason']}")
                elif len(chosen) < need:
                    chosen.append(rec)
                else:
                    rec["skip_reason"] = "valid, but this generation's xTB budget was already full"
        feedback = (f"Round {round_no}: {len(chosen)} of {need} children accepted so far.\n"
                    + ("Problems:\n" + "\n".join(notes) if notes else ""))
    # xTB barely speeds up with more threads at this size, so score several children at once
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        for k, rec in enumerate(pool.map(lambda r: score_child(r, args) or r, chosen), 1):
            print(f"  gen {gen} child {k}/{len(chosen)} {rec['child_id']} {rec['edit']:<28} "
                  f"{outcome(rec)} ({rec.get('xtb_seconds', 0):.0f} s)", flush=True)
    return records


def write_summary(run_dir, generations, records, args):
    lines = [f"# Stage 3 run `{args.run}` ({args.mutator} mutator)", "",
             f"Goal: {GOAL}. Population {args.population}, up to {args.children} xTB-scored children per "
             f"generation, gap pre-filter {GAP_WINDOW[0]}-{GAP_WINDOW[1]} eV, seed {args.seed}.", "",
             "| gen | proposed | valid | xTB-scored | best this gen | best so far | mean scored | time (min) |",
             "|---|---|---|---|---|---|---|---|"]
    for g in generations:
        lines.append(f"| {g['generation']} | {g['proposed']} | {g['valid']} | {g['evaluated']} | "
                     f"{g['best_this_gen']:.3f} | {g['best_so_far']:.3f} | {g['mean_scored']:.3f} | "
                     f"{g['seconds'] / 60:.1f} |")
    scored = [r for r in records if r.get("evaluated")]
    if scored:
        top = sorted(scored, key=lambda r: -r["sensing_score"])[:10]
        lines += ["", "## Best new GQDs", "",
                  "| id | parent | edit | hex | gap (xTB) | E_NO2 | NO2 | charge | vs CO | score | parent score |",
                  "|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in top:
            lines.append(f"| {r['child_id']} | {r['parent_id']} | {r['edit']} | {r['n_hex']} | {r['xtb_gap']:.2f} | "
                         f"{r['E_NO2_eV']:+.2f} | {'chem' if r['NO2_chemisorbed'] else 'phys'} | "
                         f"{r['charge_to_NO2_e']:.2f} | {r['selectivity_margin_eV']:+.2f} | "
                         f"{r['sensing_score']:.3f} | {r['parent_score']:.3f} |")
    reasons = pd.Series([r["reject_reason"].split(":")[0] for r in records if not r["valid"]], dtype=str)
    if len(reasons):
        lines += ["", "## Why children were rejected (before xTB)", ""]
        lines += [f"- {reason}: {count}" for reason, count in reasons.value_counts().items()]
    (run_dir / "summary.md").write_text("\n".join(lines) + "\n")


def final_check(run_dir, records, args):
    """Full Stage 3a evaluation (all gases) of the best new GQDs."""
    path = run_dir / "final_check.csv"
    if path.exists() or args.final_check <= 0:
        return
    scored = [r for r in records if r.get("evaluated") and r.get("all_converged")]
    top = sorted(scored, key=lambda r: -r["sensing_score"])[:args.final_check]

    def full(r):
        return evaluate_gqd(r["child_hexagons"], threads=args.threads, workers=args.workers, analytes=list(ANALYTES))

    rows = []
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:  # side by side, like the children
        results = list(pool.map(full, top))
    for r, res in zip(top, results):
        res.pop("details")
        if args.score == "v2":
            from Stage4.v2_loop import apply_v2
            res = apply_v2(res, r["N_FOD"], args.fod_max)
        rows.append({"child_id": r["child_id"], "smiles": r["smiles"], "loop_score": r["sensing_score"],
                     "hexagons": json.dumps(r["child_hexagons"])} | res)
        print(f"  final check {r['child_id']}: loop {r['sensing_score']:.3f} -> full {res['sensing_score']:.3f} "
              f"(strongest interferent {res['strongest_interferent']})", flush=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, help="name of the results/<run> folder")
    parser.add_argument("--mutator", choices=["llm", "random"], default="llm")
    parser.add_argument("--generations", type=int, default=10)
    parser.add_argument("--children", type=int, default=10, help="xTB-scored children per generation")
    parser.add_argument("--population", type=int, default=8)
    parser.add_argument("--family-cap", type=int, default=3, help="max parents from one starting GQD (0 = off)")
    parser.add_argument("--history", type=int, default=1, help="show the LLM last generation's results (0 = off)")
    parser.add_argument("--final-check", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--parallel", type=int, default=3, help="children scored at the same time")
    parser.add_argument("--workers", type=int, default=6, help="xTB jobs at the same time per child")
    parser.add_argument("--threads", type=int, default=1, help="threads per xTB job")
    parser.add_argument("--score", choices=["v1", "v2"], default="v1", help="v2 = Stage 4 DFT-corrected score")
    parser.add_argument("--fod-max", type=float, default=None, help="score v2: N_FOD above this = open-shell")
    args = parser.parse_args()
    global GOAL, SYSTEM
    if args.score == "v2":
        if args.fod_max is None:
            sys.exit("--score v2 needs --fod-max")
        GOAL, SYSTEM = GOAL_V2, SYSTEM_V2

    run_dir = RESULTS / args.run
    run_dir.mkdir(parents=True, exist_ok=True)
    config = {k: v for k, v in vars(args).items()
              if k not in ("generations", "final_check", "parallel", "workers", "threads")}
    if args.score == "v1":  # keep old run folders resumable (their config.json has no score keys)
        config.pop("score"), config.pop("fod_max")
    config_path = run_dir / "config.json"
    if config_path.exists():
        old = json.loads(config_path.read_text())
        if {k: old.get(k) for k in config} != config:
            sys.exit(f"{run_dir} was started with different settings: {old}")
    else:
        llm = {"llm_model": os.getenv("AZURE_OPENAI_MODEL")} if args.mutator == "llm" else {}  # for reproducibility
        config_path.write_text(json.dumps(config | {"gap_window": GAP_WINDOW, "goal": GOAL, "system_prompt": SYSTEM,
                                                    "loop_analytes": LOOP_ANALYTES} | llm, indent=2))

    children_path, gens_path = run_dir / "children.jsonl", run_dir / "generations.jsonl"
    generations = [json.loads(x) for x in gens_path.read_text().splitlines()] if gens_path.exists() else []
    records = [json.loads(x) for x in children_path.read_text().splitlines()] if children_path.exists() else []
    done = generations[-1]["generation"] if generations else 0
    records = [r for r in records if r["generation"] <= done]  # drop a half-finished generation
    children_path.write_text("".join(to_json(r) + "\n" for r in records))

    pool = initial_pool(args.score, args.fod_max)
    pool += [member(r | {"id": r["child_id"], "hexagons": r["child_hexagons"]}) for r in records if r.get("evaluated")]
    ctx = {"known": known_smiles(), "predictor": GapPredictor(),
           "seen": {p["smiles"] for p in pool} | {r["smiles"] for r in records if r.get("smiles") and r["valid"]}}
    mutator = (LLMMutator if args.mutator == "llm" else RandomMutator)(run_dir / "llm_log.jsonl")
    print(f"run {args.run}: {len(pool)} scored GQDs in the pool, resuming after generation {done}", flush=True)

    for gen in range(done + 1, args.generations + 1):
        start = time.time()
        population = select(pool, args.population, args.family_cap)
        history = [r for r in records if r["generation"] == gen - 1][:30] if args.history else []
        new = run_generation(gen, population, {p["id"]: p for p in pool}, mutator, history, ctx, args)
        scored = [r for r in new if r.get("evaluated")]
        pool += [member(r | {"id": r["child_id"], "hexagons": r["child_hexagons"]}) for r in scored]
        records += new
        with children_path.open("a") as handle:
            handle.writelines(to_json(r) + "\n" for r in new)
        best = select(pool, args.population, args.family_cap)
        summary = {"generation": gen, "proposed": len(new), "valid": sum(r["valid"] for r in new),
                   "evaluated": len(scored), "xtb_scored_total": sum(bool(r.get("evaluated")) for r in records),
                   "best_this_gen": max((r["sensing_score"] for r in scored), default=float("nan")),
                   "best_so_far": best[0]["sensing_score"], "best_id": best[0]["id"],
                   "mean_scored": float(np.mean([r["sensing_score"] for r in scored])) if scored else float("nan"),
                   "population": [p["id"] for p in best], "seconds": round(time.time() - start, 1)}
        generations.append(summary)
        with gens_path.open("a") as handle:
            handle.write(json.dumps(summary) + "\n")
        write_summary(run_dir, generations, records, args)
        print(f"gen {gen}: {summary['valid']}/{summary['proposed']} valid, {len(scored)} scored, best this gen "
              f"{summary['best_this_gen']:.3f}, best so far {summary['best_so_far']:.3f} ({summary['best_id']}), "
              f"{summary['seconds'] / 60:.1f} min", flush=True)

    final_check(run_dir, records, args)
    write_summary(run_dir, generations, records, args)


if __name__ == "__main__":
    main()
