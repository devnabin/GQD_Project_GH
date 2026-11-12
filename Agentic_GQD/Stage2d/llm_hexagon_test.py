# Created date: 2026-11-10 (America/Chicago)
"""Stage 2d: can the LLM write valid GQDs as hexagon coordinates?

Asks the agent's LLM (same Azure deployment, same `build_gqd_from_hexagons`
tool, same validation checks as studio/agent.py) for N GQDs, one independent
request each, with a varied size and shape. If a design fails, the rejection
message is sent back and the LLM may retry (up to --retries times).

Ablation: each condition = prompt x feedback, run on the SAME list of requests.
    prompt   basic : coordinates + connectivity + size only (the original prompt)
             rule  : + the closed-shell (sublattice) rule and the point-symmetry tip
                     (agent.HEXAGON_RULES, the prompt the agent now uses)
    feedback plain : open-shell rejection says only "no Kekulé form"
             fixes : + the sublattice imbalance and hexagon edits that fix it

Nothing is written to accepted_gqds/: this is a measurement, not generation.

Output (Stage2d/results/<prompt>-<feedback>/): attempts.csv, designs.csv, summary.md
        Stage2d/results/ablation.md: comparison of all conditions
Usage : .venv/bin/python Stage2d/llm_hexagon_test.py --n 80 --retries 2
"""

import argparse
import asyncio
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from rdkit import Chem

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "studio"))
load_dotenv(ROOT / "studio" / ".env")

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage  # noqa: E402

import agent  # noqa: E402  (the real agent: its LLM, tool, rules and check functions)
from Stage1.gqd_hex import HexError, hex_to_smiles  # noqa: E402

RESULTS = HERE / "results"
SHAPES = ["roughly round (compact, like a disc)", "elongated (a ribbon about 3 hexagons wide)",
          "triangular", "rectangular", "irregular / asymmetric", "with armchair edges as far as possible",
          "with zigzag edges as far as possible", "L-shaped"]

TASK = ("You design graphene quantum dots (GQDs) as sets of fused hexagons on a honeycomb grid. "
        "Call build_gqd_from_hexagons exactly once with your hexagon list (never write SMILES). ")
PROMPTS = {
    "basic": TASK + (
        "Coordinates are axial [q, r]; the six neighbours of [q, r] are "
        "[q+1, r], [q-1, r], [q, r+1], [q, r-1], [q+1, r-1], [q-1, r+1]. "
        "All hexagons must form one connected piece, with no duplicates. "
        f"A valid GQD has {agent.MIN_HEX}-{agent.MAX_HEX} hexagons."),
    "rule": TASK + agent.HEXAGON_RULES,
}


def validate(hexagons, feedback: bool) -> dict:
    """Run the agent's checks (except saving). Returns valid / failed_check / reason / n_hex / smiles."""
    try:
        smiles = hex_to_smiles(hexagons, feedback=feedback)
    except HexError as error:
        return {"valid": False, "failed_check": "molecular graph", "reason": str(error)}
    except Exception as error:  # malformed coordinates (not pairs of ints, etc.)
        return {"valid": False, "failed_check": "malformed input", "reason": repr(error)[:300]}

    mol = Chem.MolFromSmiles(smiles)
    if mol is None or "." in Chem.MolToSmiles(mol):
        return {"valid": False, "failed_check": "molecular graph", "reason": "RDKit could not parse the SMILES"}
    state = {"smiles": smiles}
    for name, check in [("ring count", agent.check_ring_count), ("sp2 fraction", agent.check_sp2),
                        ("SA score", agent.check_sa_score)]:
        result = check(state)
        state |= result
        if result.get("rejection"):
            return {"valid": False, "failed_check": name, "reason": result["rejection"],
                    "n_hex": state.get("n_hex"), "smiles": smiles}
    return {"valid": True, "failed_check": "", "reason": "", "n_hex": state["n_hex"], "smiles": smiles}


def point_symmetric(hexagons) -> bool:
    """True if the set is unchanged by [q, r] -> [a - q, b - r] for some integers a, b."""
    cells = {tuple(c) for c in hexagons}
    n = len(cells)
    sum_q, sum_r = sum(q for q, _ in cells), sum(r for _, r in cells)
    if (2 * sum_q) % n or (2 * sum_r) % n:
        return False
    a, b = 2 * sum_q // n, 2 * sum_r // n
    return all((a - q, b - r) in cells for q, r in cells)


async def one_request(llm, system, feedback, request_id, size, shape, retries, semaphore) -> list[dict]:
    messages = [SystemMessage(content=system), HumanMessage(content=f"Design one GQD with about {size} hexagons, {shape}.")]
    rows = []
    async with semaphore:
        for attempt in range(1, retries + 2):
            base = {"request": request_id, "attempt": attempt, "target_size": size, "shape": shape}
            try:
                reply = await llm.ainvoke(messages)
            except Exception as error:
                rows.append(base | {"valid": False, "failed_check": "llm error", "reason": repr(error)[:300]})
                break
            if not reply.tool_calls:
                rows.append(base | {"valid": False, "failed_check": "no tool call", "reason": str(reply.content)[:300]})
                break
            call = reply.tool_calls[0]
            hexagons = call["args"].get("hexagons")
            result = validate(hexagons, feedback)
            rows.append(base | {"hexagons": json.dumps(hexagons), "n_listed": len(hexagons or [])} | result)
            if result["valid"]:
                break
            message = f"Rejected at {result['failed_check']} check: {result['reason']}. Fix it and try again."
            messages += [reply, ToolMessage(content=message, tool_call_id=call["id"], status="error")]
    return rows


def short_reason(reason: str) -> str:
    reason = str(reason)
    if "no Kekulé form" in reason:
        return "open-shell (no Kekulé form)"
    if "re-read" in reason:
        return "RDKit cannot re-read SMILES"
    return reason.split("[")[0].split("(")[0].strip()[:70]


def condition_metrics(attempts: pd.DataFrame, designs: pd.DataFrame) -> dict:
    first = attempts[attempts.attempt == 1]
    ok = designs[designs.valid]
    fails = attempts[~attempts.valid]
    return {
        "first_try_pass": first.valid.mean(),
        "final_pass": designs.valid.mean(),
        "mean_attempts": attempts.groupby("request").size().mean(),
        "open_shell_attempts": (fails.reason.map(short_reason) == "open-shell (no Kekulé form)").sum(),
        "other_failed_attempts": (fails.reason.map(short_reason) != "open-shell (no Kekulé form)").sum(),
        "valid": len(ok),
        "distinct_valid": ok.inchikey.nunique(),
        "new_vs_91k": int((~ok.in_dataset).sum()),
        "point_symmetric": ok.symmetric.mean() if len(ok) else float("nan"),
        "size_error": (ok.n_hex - ok.target_size).abs().mean() if len(ok) else float("nan"),
        "with_holes": int((ok.holes > 0).sum()),
        "gap_min": ok.gap_pred_eV.min(), "gap_median": ok.gap_pred_eV.median(), "gap_max": ok.gap_pred_eV.max(),
    }


def condition_summary(name, attempts, designs, metrics, seconds) -> str:
    lines = [f"# Stage 2d: {name}", "",
             f"- {len(designs)} requests, {seconds / 60:.1f} min",
             f"- First-try pass rate: {metrics['first_try_pass']:.0%}",
             f"- Pass rate after retries: {metrics['final_pass']:.0%} (mean attempts {metrics['mean_attempts']:.2f})",
             f"- Distinct valid: {metrics['distinct_valid']}; new vs 91k: {metrics['new_vs_91k']}; "
             f"point-symmetric: {metrics['point_symmetric']:.0%}; with holes: {metrics['with_holes']}",
             "", "## Rejection reasons (all failed attempts)", "", "| Reason | Count |", "|---|---|"]
    for reason, count in Counter(attempts[~attempts.valid].reason.map(short_reason)).most_common():
        lines.append(f"| {reason} | {count} |")
    lines += ["", "## Pass rate by requested shape", "", "| Shape | First try | Final |", "|---|---|---|"]
    first = attempts[attempts.attempt == 1].set_index("request").valid
    for shape, group in designs.groupby("shape"):
        lines.append(f"| {shape} | {first[group.request].sum()}/{len(group)} | {group.valid.sum()}/{len(group)} |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=80)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--conditions", default="basic-plain,basic-fixes,rule-plain,rule-fixes")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    jobs = [(i, rng.randint(agent.MIN_HEX, agent.MAX_HEX), SHAPES[i % len(SHAPES)]) for i in range(args.n)]
    llm = agent.llm.bind_tools([agent.build_gqd_from_hexagons], tool_choice="build_gqd_from_hexagons")

    known = pd.read_csv(ROOT / "Stage1" / "data" / "gqd_hex_dataset.csv", usecols=["SMILES"]).SMILES
    known = {Chem.CanonSmiles(s) for s in known}
    from Stage2.features import compute_features
    from Stage2.predictor import GapPredictor
    predictor = GapPredictor()

    conditions = args.conditions.split(",")

    async def run_conditions():  # one event loop for all conditions (the LLM client is bound to it)
        runs = {}
        for condition in conditions:
            prompt, feedback = condition.split("-")
            semaphore = asyncio.Semaphore(args.concurrency)
            start = time.time()
            rows = await asyncio.gather(*[one_request(llm, PROMPTS[prompt], feedback == "fixes", i, s, sh,
                                                      args.retries, semaphore) for i, s, sh in jobs])
            runs[condition] = (rows, time.time() - start)
            print(f"{condition}: LLM calls done in {runs[condition][1] / 60:.1f} min", flush=True)
        return runs

    runs = asyncio.run(run_conditions())
    table = {}
    for condition in conditions:
        rows, seconds = runs[condition]
        attempts = pd.DataFrame([row for request_rows in rows for row in request_rows])
        attempts["valid"] = attempts["valid"].astype(bool)
        for column in ["hexagons", "smiles", "n_hex", "n_listed", "reason", "failed_check"]:
            if column not in attempts:
                attempts[column] = None

        designs = (attempts.sort_values("attempt").groupby("request").tail(1)
                   .sort_values("request").reset_index(drop=True))
        ok = designs.valid
        designs["inchikey"] = [Chem.MolToInchiKey(Chem.MolFromSmiles(s)) if v else None
                               for s, v in zip(designs.smiles, ok)]
        designs["in_dataset"] = [bool(v) and s in known for s, v in zip(designs.smiles, ok)]
        designs["symmetric"] = [bool(v) and point_symmetric(json.loads(h)) for h, v in zip(designs.hexagons, ok)]
        designs["holes"], designs["gap_pred_eV"], designs["sigma_eV"] = float("nan"), float("nan"), float("nan")
        if ok.any():
            designs.loc[ok, "holes"] = [compute_features(Chem.MolFromSmiles(s))["hole_count"]
                                        for s in designs.smiles[ok]]
            predicted = predictor.predict(smiles=designs.smiles[ok].tolist())
            designs.loc[ok, "gap_pred_eV"] = predicted.gap_pred_eV.values
            designs.loc[ok, "sigma_eV"] = predicted.sigma_eV.values

        metrics = condition_metrics(attempts, designs)
        table[condition] = metrics
        folder = RESULTS / condition
        folder.mkdir(parents=True, exist_ok=True)
        attempts.to_csv(folder / "attempts.csv", index=False)
        designs.to_csv(folder / "designs.csv", index=False)
        (folder / "summary.md").write_text(condition_summary(condition, attempts, designs, metrics, seconds))
        print(f"first try {metrics['first_try_pass']:.0%}, final {metrics['final_pass']:.0%}", flush=True)

    def cell(value):
        return f"{value:.3f}" if isinstance(value, float) else str(value)

    names = list(table)
    lines = ["# Stage 2d ablation: prompt x feedback", "",
             f"{args.n} requests per condition (same sizes and shapes, seed {args.seed}), up to {args.retries} retries.",
             "", "| Metric | " + " | ".join(names) + " |", "|---" * (len(names) + 1) + "|"]
    for metric in table[names[0]]:
        lines.append(f"| {metric} | " + " | ".join(cell(table[n][metric]) for n in names) + " |")
    (RESULTS / "ablation.md").write_text("\n".join(lines) + "\n")
    print("\n" + "\n".join(lines))


if __name__ == "__main__":
    main()
