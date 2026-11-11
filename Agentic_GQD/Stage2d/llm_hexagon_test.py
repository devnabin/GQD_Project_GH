# Created date: 2026-11-10 (America/Chicago)
"""Stage 2d: can the LLM write valid GQDs as hexagon coordinates?

Asks the agent's LLM (same Azure deployment, same `build_gqd_from_hexagons`
tool, same validation checks as studio/agent.py) for N GQDs, one independent
request each, with a varied size and shape. If a design fails, the error is sent
back and the LLM may retry (up to --retries times).

Nothing is written to accepted_gqds/: this is a measurement, not generation.

Output (Stage2d/results/):
    attempts.csv   one row per LLM attempt (request, attempt, hexagons, valid,
                   failed_check, reason, n_hex, smiles, ...)
    designs.csv    one row per request: final outcome + novelty, holes, predicted gap
    summary.md     pass rates and most common rejection reasons
Usage : .venv/bin/python Stage2d/llm_hexagon_test.py --n 50 --retries 2
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

import agent  # noqa: E402  (the real agent: its LLM, tool and check functions)
from Stage1.gqd_hex import HexError, hex_to_smiles  # noqa: E402

RESULTS = HERE / "results"
SHAPES = ["roughly round (compact, like a disc)", "elongated (a ribbon about 3 hexagons wide)",
          "triangular", "rectangular", "irregular / asymmetric", "with armchair edges as far as possible",
          "with zigzag edges as far as possible", "L-shaped"]

SYSTEM = SystemMessage(content=(
    "You design graphene quantum dots (GQDs) as sets of fused hexagons on a honeycomb grid. "
    "Call build_gqd_from_hexagons exactly once with your hexagon list (never write SMILES). "
    "Coordinates are axial [q, r]; the six neighbours of [q, r] are "
    "[q+1, r], [q-1, r], [q, r+1], [q, r-1], [q+1, r-1], [q-1, r+1]. "
    "All hexagons must form one connected piece, with no duplicates. "
    f"A valid GQD has {agent.MIN_HEX}-{agent.MAX_HEX} hexagons."
))


def validate(hexagons) -> dict:
    """Run the agent's checks (except saving). Returns valid / failed_check / reason / n_hex / smiles."""
    try:
        smiles = hex_to_smiles(hexagons)
    except HexError as error:
        return {"valid": False, "failed_check": "molecular graph", "reason": str(error)}
    except Exception as error:  # malformed coordinates (not pairs of ints, etc.)
        return {"valid": False, "failed_check": "malformed input", "reason": repr(error)[:200]}

    state = {"smiles": smiles}
    for name, check in [("molecular graph", None), ("ring count", agent.check_ring_count),
                        ("sp2 fraction", agent.check_sp2), ("SA score", agent.check_sa_score)]:
        if check is None:
            mol = Chem.MolFromSmiles(smiles)
            if mol is None or "." in Chem.MolToSmiles(mol):
                return {"valid": False, "failed_check": name, "reason": "RDKit could not parse the SMILES"}
            continue
        result = check(state)
        state |= result
        if result.get("rejection"):
            return {"valid": False, "failed_check": name, "reason": result["rejection"],
                    "n_hex": state.get("n_hex"), "smiles": smiles}
    return {"valid": True, "failed_check": "", "reason": "", "n_hex": state["n_hex"], "smiles": smiles,
            "sp2": state.get("sp2"), "sa_score": state.get("sa_score")}


async def one_request(llm, request_id: int, size: int, shape: str, retries: int, semaphore) -> list[dict]:
    prompt = f"Design one GQD with about {size} hexagons, {shape}."
    messages = [SYSTEM, HumanMessage(content=prompt)]
    rows = []
    async with semaphore:
        for attempt in range(1, retries + 2):
            base = {"request": request_id, "attempt": attempt, "target_size": size, "shape": shape}
            try:
                reply = await llm.ainvoke(messages)
            except Exception as error:
                rows.append(base | {"valid": False, "failed_check": "llm error", "reason": repr(error)[:200]})
                break
            if not reply.tool_calls:
                rows.append(base | {"valid": False, "failed_check": "no tool call",
                                    "reason": str(reply.content)[:200]})
                break
            call = reply.tool_calls[0]
            hexagons = call["args"].get("hexagons")
            result = validate(hexagons)
            rows.append(base | {"hexagons": json.dumps(hexagons), "n_listed": len(hexagons or [])} | result)
            if result["valid"]:
                break
            feedback = f"Rejected at {result['failed_check']} check: {result['reason']}. Fix it and try again."
            messages += [reply, ToolMessage(content=feedback, tool_call_id=call["id"], status="error")]
    print(f"request {request_id:3d}: {'PASS' if rows[-1]['valid'] else 'FAIL'} after {len(rows)} attempt(s)",
          flush=True)
    return rows


def summarise(attempts: pd.DataFrame, designs: pd.DataFrame, retries: int, seconds: float) -> str:
    n = len(designs)
    first = attempts[attempts.attempt == 1]
    lines = [
        "# Stage 2d results: LLM writes hexagons", "",
        f"- Model: Azure deployment from `studio/.env`; {n} independent requests; up to {retries} retries "
        f"with the error fed back; {seconds / 60:.1f} min.",
        f"- **First-try pass rate: {first.valid.mean():.0%}** ({first.valid.sum()}/{len(first)})",
        f"- **Pass rate after retries: {designs.valid.mean():.0%}** ({designs.valid.sum()}/{n}); "
        f"mean attempts {attempts.groupby('request').size().mean():.2f}",
        "", "## Rejection reasons (all failed attempts)", "",
        "| Check | Count |", "|---|---|",
    ]
    fails = attempts[~attempts.valid]
    for check, count in Counter(fails.failed_check).most_common():
        lines.append(f"| {check} | {count} |")
    lines += ["", "Most common messages:", ""]
    short = fails.reason.str.replace(r"\[.*", "", regex=True).str.slice(0, 90)
    for reason, count in Counter(short).most_common(8):
        lines.append(f"- ({count}×) {reason}")

    ok = designs[designs.valid]
    if len(ok):
        lines += ["", "## Valid designs", "",
                  f"- Size accuracy: requested vs built hexagons, mean |difference| "
                  f"{(ok.n_hex - ok.target_size).abs().mean():.1f}",
                  f"- Hexagon count stated by LLM vs ring count: {(ok.n_listed == ok.n_hex).mean():.0%} equal "
                  "(differs when the shape has holes)",
                  f"- Unique among themselves: {ok.inchikey.nunique()}/{len(ok)}",
                  f"- Already in the 91k dataset: {ok.in_dataset.sum()}/{len(ok)}",
                  f"- With holes: {(ok.holes > 0).sum()}/{len(ok)}",
                  f"- Predicted gap (eV): min {ok.gap_pred_eV.min():.2f}, median {ok.gap_pred_eV.median():.2f}, "
                  f"max {ok.gap_pred_eV.max():.2f}",
                  "", "| Shape asked | Valid / asked |", "|---|---|"]
        for shape, group in designs.groupby("shape"):
            lines.append(f"| {shape} | {group.valid.sum()}/{len(group)} |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=50)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    jobs = [(i, rng.randint(agent.MIN_HEX, agent.MAX_HEX), SHAPES[i % len(SHAPES)]) for i in range(args.n)]
    llm = agent.llm.bind_tools([agent.build_gqd_from_hexagons], tool_choice="build_gqd_from_hexagons")

    async def run_all():
        semaphore = asyncio.Semaphore(args.concurrency)
        return await asyncio.gather(*[one_request(llm, i, s, sh, args.retries, semaphore) for i, s, sh in jobs])

    start = time.time()
    attempts = pd.DataFrame([row for rows in asyncio.run(run_all()) for row in rows])
    seconds = time.time() - start
    attempts["valid"] = attempts["valid"].astype(bool)
    for column in ["hexagons", "smiles", "n_hex", "n_listed", "reason", "failed_check"]:
        if column not in attempts:
            attempts[column] = None

    designs = attempts.sort_values("attempt").groupby("request").tail(1).sort_values("request").reset_index(drop=True)
    designs["inchikey"] = [Chem.MolToInchiKey(Chem.MolFromSmiles(s)) if v else None
                           for s, v in zip(designs.smiles, designs.valid)]

    # Novelty vs the 91k dataset, holes and predicted gap (Stage 2 predictor)
    known = pd.read_csv(ROOT / "Stage1" / "data" / "gqd_hex_dataset.csv", usecols=["SMILES"]).SMILES
    known = {Chem.CanonSmiles(s) for s in known}
    designs["in_dataset"] = [bool(v) and s in known for s, v in zip(designs.smiles, designs.valid)]
    designs["holes"], designs["gap_pred_eV"], designs["sigma_eV"] = None, None, None
    ok = designs.valid
    if ok.any():
        from Stage2.features import compute_features
        from Stage2.predictor import GapPredictor
        designs.loc[ok, "holes"] = [compute_features(Chem.MolFromSmiles(s))["hole_count"] for s in designs.smiles[ok]]
        table = GapPredictor().predict(smiles=designs.smiles[ok].tolist())
        designs.loc[ok, "gap_pred_eV"] = table.gap_pred_eV.values
        designs.loc[ok, "sigma_eV"] = table.sigma_eV.values

    RESULTS.mkdir(exist_ok=True)
    attempts.to_csv(RESULTS / "attempts.csv", index=False)
    designs.to_csv(RESULTS / "designs.csv", index=False)
    summary = summarise(attempts, designs, args.retries, seconds)
    (RESULTS / "summary.md").write_text(summary)
    print("\n" + summary)


if __name__ == "__main__":
    main()
