# Created date: 2026-11-13 (America/Chicago)
"""Rescore every xTB-scored structure we already have with score v2 (no new calculations).

    python Stage4/rescore.py      # -> Stage4/results/rescored.csv, rescore_summary.md

Sources: Stage 3a calibration (50 GQDs, all gases), every scored child of every Stage 3 run
(NO2 + CO only; H2O/NH3 filled with calibration medians, flagged), the full checks of the best
children (all gases), and the 21 linked-carbon designs of Stage 3d (all gases).
"""

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from Stage4.score_v2 import OFFSETS, fill_interferents, score_v2  # noqa: E402

OUT = ROOT / "Stage4" / "results"
KEEP = ["E_NO2_eV", "q_NO2_e", "dmin_NO2_A", "E_CO_eV", "q_CO_e", "E_H2O_eV", "q_H2O_e", "E_NH3_eV", "q_NH3_e"]


def main():
    cal = pd.read_csv(ROOT / "Stage3a" / "data" / "calibration.csv")
    defaults = {k: float(cal[k].median()) for k in ["E_H2O_eV", "q_H2O_e", "E_NH3_eV", "q_NH3_e"]}
    records = []
    for r in cal[cal.all_converged].to_dict("records"):
        records.append(r | {"id": r["Structure_Name"], "source": "calibration", "kind": "fused", "gap": r["gqd_gap_eV"]})
    for path in sorted((ROOT / "Stage3" / "results").glob("*/children.jsonl")):
        run = path.parent.name
        full = {}
        if (path.parent / "final_check.csv").exists():
            full = {r["child_id"]: r for r in pd.read_csv(path.parent / "final_check.csv").to_dict("records")}
        for line in path.read_text().splitlines():
            r = json.loads(line)
            if not r.get("evaluated") or not r.get("all_converged"):
                continue
            r = full.get(r["child_id"], r) | {"child_hexagons": r["child_hexagons"]}
            records.append(fill_interferents(r, defaults) | {
                "id": f"{run}/{r['child_id']}", "source": run, "kind": "fused",
                "gap": r.get("xtb_gap", r.get("gqd_gap_eV")), "hexagons": json.dumps(r["child_hexagons"])})
    linked = ROOT / "Stage3d" / "results" / "calibration_linked.jsonl"
    if linked.exists():
        for r in map(json.loads, linked.read_text().splitlines()):
            records.append(r | {"id": f"linked/{r['design']}", "source": "Stage3d", "kind": "linked",
                                "gap": r.get("gqd_gap_eV")})
    rows = []
    for r in records:
        rows.append({k: r.get(k) for k in ["id", "source", "kind", "gap", "hexagons"] + KEEP}
                    | {"interferents_filled": bool(r.get("interferents_filled", False))} | score_v2(r))
    df = pd.DataFrame(rows).drop_duplicates("id")
    df["NO2_bonded"] = df.dmin_NO2_A < 1.9
    OUT.mkdir(parents=True, exist_ok=True)
    df.sort_values("score_v2", ascending=False).to_csv(OUT / "rescored.csv", index=False)

    top = df.sort_values("score_v2", ascending=False).head(25)
    cols = ["id", "kind", "gap", "E_NO2_eV", "NO2_bonded", "score_v2", "v2_recovery_s", "v2_humidity_equiv_ppb"]
    lines = ["# Score v2 rescoring of all existing xTB results", "",
             f"Corrections from the GPU DFT benchmark: bonded NO2 energy shift {OFFSETS['bonded']:+.3f} eV "
             f"(n = {OFFSETS['n_bonded']} complexes); physisorbed NO2 charge set to 0.",
             f"Structures rescored: {len(df)} ({(df.kind == 'fused').sum()} fused, {(df.kind == 'linked').sum()} linked); "
             f"with score_v2 > 0: {(df.score_v2 > 0).sum()}; interferents filled from medians: {df.interferents_filled.sum()}.",
             "No open-shell (N_FOD) filter applied yet.", "", "## Top 25 by score v2", "",
             "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in top[cols].itertuples(index=False):
        lines.append("| " + " | ".join(f"{v:.3g}" if isinstance(v, float) else str(v) for v in r) + " |")
    (OUT / "rescore_summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
