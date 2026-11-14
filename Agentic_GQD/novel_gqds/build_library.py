# Created: 2026-11-13 22:45 CST
"""Build the library of new GQDs found by the evolution loop (decision D24, option A).

    .venv/bin/python novel_gqds/build_library.py      # -> novel_gqds/library.csv, novel_gqds/summary.md

One row per unique structure (canonical SMILES), merged across all runs in Stage3/results.
Only valid children are included; every one passed the agent's checks, is closed-shell (Kekulé),
has no holes and is not in the 91k dataset. Score and screening columns are filled where a
result exists (blank otherwise):
  score_v1          best Stage 3a loop score (old score; known to reward an xTB artefact)
  score_v2          Stage 4 score v2 (from Stage4/results/rescored.csv, or from score-v2 runs)
  N_FOD             xTB open-shell screen (Stage4/results/fod_candidates.csv or score-v2 runs)
  dft_status        "benchmark" / "candidate" if the structure went through GPU DFT
Rebuild at any time; the library is derived from the logs and never edited by hand.
"""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")
ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
DFT_BENCHMARK = {"llm_s0/g10c004", "random_s0/g02c004"}
DFT_CANDIDATES = {"random_v2_s2/g02c012", "llm_v2_s3/g01c013", "random_s0/g01c009"}


def inchikey(row) -> str:
    """InChIKey; RDKit's InChI step fails to kekulise some large GQDs (the Stage 1 limit), so fall back
    to our own Kekule structure from the hexagons, and to "" if that also fails."""
    try:
        return Chem.MolToInchiKey(Chem.MolFromSmiles(row["smiles"]))
    except Exception:
        pass
    try:
        import sys
        sys.path.insert(0, str(ROOT))
        from Stage1.gqd_hex import hex_to_mol
        return Chem.MolToInchiKey(hex_to_mol(json.loads(row["hexagons"]), feedback=False))
    except Exception:
        return ""


def main():
    rescored = OUT.parent / "Stage4" / "results" / "rescored.csv"
    v2 = pd.read_csv(rescored).set_index("id")["score_v2"].to_dict() if rescored.exists() else {}
    fodfile = OUT.parent / "Stage4" / "results" / "fod_candidates.csv"
    fods = pd.read_csv(fodfile).set_index("id")["N_FOD"].to_dict() if fodfile.exists() else {}

    lib = {}
    for path in sorted((ROOT / "Stage3" / "results").glob("*/children.jsonl")):
        run = path.parent.name
        if run.startswith("smoke"):
            continue
        for r in map(json.loads, path.read_text().splitlines()):
            if not r.get("valid") or not r.get("smiles"):
                continue
            key = f"{run}/{r['child_id']}"
            row = lib.setdefault(r["smiles"], {
                "smiles": r["smiles"], "n_hex": r.get("n_hex"), "hexagons": json.dumps(r["child_hexagons"]),
                "first_found": key, "found_by": r["mutator"], "times_found": 0, "runs": set(),
                "xtb_scored": False, "xtb_gap_eV": None, "E_NO2_eV": None, "NO2_bonded": None,
                "score_v1": None, "score_v2": None, "N_FOD": None, "open_shell": None, "dft_status": ""})
            row["times_found"] += 1
            row["runs"].add(run)
            if r.get("evaluated"):
                row["xtb_scored"] = True
                for k_out, k_in in [("xtb_gap_eV", "xtb_gap"), ("E_NO2_eV", "E_NO2_eV")]:
                    if row[k_out] is None:
                        row[k_out] = r.get(k_in)
                if row["NO2_bonded"] is None and r.get("dmin_NO2_A") is not None:
                    row["NO2_bonded"] = r["dmin_NO2_A"] < 1.9
                if "score_v2" in r:  # score-v2 runs record it directly
                    row["score_v2"] = max(row["score_v2"] or 0.0, r.get("score_v2") or 0.0)
                    row["N_FOD"] = r.get("N_FOD", row["N_FOD"])
                elif r.get("sensing_score") is not None:
                    row["score_v1"] = max(row["score_v1"] or 0.0, r["sensing_score"])
            if key in v2 and row["score_v2"] is None:
                row["score_v2"] = v2[key]
            if key in fods:
                row["N_FOD"] = fods[key]
            if key in DFT_BENCHMARK:
                row["dft_status"] = "benchmark"
            elif key in DFT_CANDIDATES:
                row["dft_status"] = "candidate"

    rows = []
    for row in lib.values():
        row["runs"] = ",".join(sorted(row.pop("runs")))
        row["open_shell"] = None if row["N_FOD"] is None else bool(row["N_FOD"] > 2.9)
        row["inchikey"] = inchikey(row)
        rows.append(row)
    df = pd.DataFrame(rows).sort_values(["score_v2", "score_v1"], ascending=False, na_position="last")
    df.insert(0, "library_id", [f"NG{i:05d}" for i in range(1, len(df) + 1)])
    df.to_csv(OUT / "library.csv", index=False)

    stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    lines = [f"# Novel GQD library (built {stamp})", "",
             f"- Unique new GQDs (valid, closed-shell, no holes, not in the 91k dataset): **{len(df)}**",
             f"- Found by LLM edits first: {(df.found_by == 'llm').sum()}; by random edits first: {(df.found_by == 'random').sum()}",
             f"- Scored by xTB: {df.xtb_scored.sum()}; with score v2: {df.score_v2.notna().sum()} "
             f"(> 0: {(df.score_v2 > 0).sum()})",
             f"- Open-shell screen done: {df.N_FOD.notna().sum()} (closed-shell, N_FOD ≤ 2.9: {(df.open_shell == False).sum()})",  # noqa: E712
             f"- InChIKey not available (RDKit InChI kekulisation limit): {(df.inchikey == '').sum()}",
             f"- Went through GPU DFT: {(df.dft_status != '').sum()}",
             f"- Runs included: {', '.join(sorted(set(','.join(df.runs).split(','))))}", "",
             "Columns are described in `build_library.py`. score_v1 is the old Stage 3a score, which DFT showed "
             "rewards an xTB artefact; use score_v2 and N_FOD."]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
