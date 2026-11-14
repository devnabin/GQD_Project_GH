# Created date: 2026-11-13 (America/Chicago)
"""L2 analysis: linked-carbon calibration vs the 50 fused GQDs of Stage 3a, with both scores.

    .venv/bin/python Stage3d/analyze_linked.py
-> results/calibration_linked.csv, results/summary.md, results/linked_vs_fused.png
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "Stage3c"))
from Stage3a.sensing import BOND_A, sensing_numbers  # noqa: E402
from twin import SPEC_RECOVERY_S, twin  # noqa: E402

RES = HERE / "results"


def md_table(df):
    fmt = lambda v: f"{v:.3g}" if isinstance(v, float) else str(v)  # noqa: E731
    rows = ["| " + " | ".join(df.columns) + " |", "|" + "---|" * len(df.columns)]
    rows += ["| " + " | ".join(fmt(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join(rows)


def load():
    recs = [json.loads(x) for x in (RES / "calibration_linked.jsonl").read_text().splitlines()]
    rows = []
    for r in recs:
        row = {k: v for k, v in r.items() if k not in ("details", "structure")}
        row |= twin(r)
        # NO2 per site type: chemisorbed or not
        for kind in ("ring", "triple", "pore"):
            d = r.get(f"dmin_NO2_{kind}_A")
            row[f"NO2_{kind}_chemisorbed"] = (d is not None and not (isinstance(d, float) and np.isnan(d)) and d < BOND_A)
        rows.append(row)
    linked = pd.DataFrame(rows)
    fused = pd.read_csv(ROOT / "Stage3a" / "data" / "calibration.csv")
    fused = fused[fused.all_converged].copy()
    fused = pd.concat([fused.reset_index(drop=True),
                       pd.DataFrame([sensing_numbers(r) | twin(r) for r in fused.to_dict("records")])], axis=1)
    fused = fused.loc[:, ~fused.columns.duplicated(keep="last")]
    return linked, fused, recs


def site_table(recs):
    """Best NO2 binding at every site of every design (min over the two NO2 orientations)."""
    out = []
    for r in recs:
        for site in r["sites"].split(","):
            sub = [d for d in r["details"] if d["analyte"] == "NO2" and d["site"] == site]
            best = min(sub, key=lambda d: d["E_ads_eV"])
            out.append({"design": r["design"], "site": site, "site_type": best["site_type"],
                        "E_NO2_eV": best["E_ads_eV"], "q_NO2_e": best["q_gas_e"], "dmin_A": best["d_min_A"],
                        "chemisorbed": best["d_min_A"] < BOND_A, "converged": best["converged"]})
    return pd.DataFrame(out)


def describe(df, label):
    chem = df.NO2_chemisorbed.astype(bool)
    return {"set": label, "n": len(df), "all converged": int(df.all_converged.sum()),
            "gap median (eV)": float(df.gqd_gap_eV.median()),
            "E_NO2 median (eV)": float(df.E_NO2_eV.median()),
            "NO2 chemisorbed": f"{int(chem.sum())}/{len(df)}",
            "q_NO2 median (e)": float(df.q_NO2_e.median()),
            "strongest interferent": ", ".join(f"{k} {v}" for k, v in df.strongest_interferent.value_counts().items()),
            "NO2-CO margin median (eV)": float((df.E_CO_eV - df.E_NO2_eV).median()),
            "score > 0": int((df.sensing_score > 0).sum()),
            "score median": float(df.sensing_score.median()), "score max": float(df.sensing_score.max()),
            "meet 5-min recovery": int(df.meets_recovery_spec.sum()),
            "twin response max (e/site)": float(df.response_20ppb_RH50_e.max())}


def plot(linked, fused, sites):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ink, muted, grid, surface = "#1f1f1e", "#6b6a65", "#e4e3df", "#fcfcfb"
    colour = {"fused GQDs (Stage 3a)": "#2a78d6", "linked carbon (Stage 3d)": "#eb6834"}
    plt.rcParams.update({"font.size": 10, "axes.edgecolor": muted, "axes.labelcolor": ink,
                         "xtick.color": muted, "ytick.color": muted, "text.color": ink})
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), facecolor=surface)
    for ax in axes:
        ax.set_facecolor(surface)
        ax.grid(True, color=grid, linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    for label, df in [("fused GQDs (Stage 3a)", fused), ("linked carbon (Stage 3d)", linked)]:
        for chem, marker in [(False, "o"), (True, "^")]:
            sub = df[df.NO2_chemisorbed.astype(bool) == chem]
            kw = dict(s=48, color=colour[label], marker=marker, edgecolor=surface, linewidth=1.2, zorder=3)
            axes[0].scatter(sub.gqd_gap_eV, sub.E_NO2_eV, label=f"{label}, NO₂ {'chemisorbed' if chem else 'physisorbed'}", **kw)
            axes[1].scatter(sub.E_NO2_eV, sub.sensing_score, **kw)
    axes[0].set_title("Strongest NO₂ binding vs gap", loc="left", fontsize=11)
    axes[0].set_xlabel("HOMO-LUMO gap, xTB (eV)")
    axes[0].set_ylabel("E_ads NO₂, xTB (eV)")
    axes[1].set_title("Stage 3a sensing score", loc="left", fontsize=11)
    axes[1].set_xlabel("E_ads NO₂, xTB (eV)")
    axes[1].set_ylabel("score (e)")
    order = ["ring", "triple", "pore"]
    for i, kind in enumerate(order):
        sub = sites[sites.site_type == kind]
        x = i + np.linspace(-0.25, 0.25, len(sub)) if len(sub) > 1 else np.array([i])
        for chem, marker in [(False, "o"), (True, "^")]:
            m = sub.chemisorbed.values == chem
            axes[2].scatter(x[m], sub.E_NO2_eV.values[m], s=44, color=colour["linked carbon (Stage 3d)"],
                            marker=marker, edgecolor=surface, linewidth=1.2, zorder=3)
    axes[2].set_xticks(range(3), [f"{k}\n(n={int((sites.site_type == k).sum())})" for k in order])
    axes[2].set_title("Linked carbon: NO₂ binding by site type", loc="left", fontsize=11)
    axes[2].set_ylabel("E_ads NO₂, xTB (eV)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 1.0), fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(RES / "linked_vs_fused.png", dpi=150, facecolor=surface)
    plt.close(fig)


def main():
    linked, fused, recs = load()
    sites = site_table(recs)
    keep = ["design", "formula", "n_carbon", "n_units", "n_links", "has_pore", "gqd_gap_eV", "E_NO2_eV", "q_NO2_e",
            "site_NO2", "NO2_chemisorbed", "E_NO2_ring_eV", "E_NO2_triple_eV", "E_NO2_pore_eV", "E_CO_eV", "E_H2O_eV",
            "E_NH3_eV", "E_O2_eV", "strongest_interferent", "selectivity_margin_eV", "sensing_score",
            "recovery_s", "response_20ppb_RH50_e", "humidity_equiv_ppb", "twin_score", "all_converged", "seconds"]
    linked[keep].to_csv(RES / "calibration_linked.csv", index=False)
    sites.to_csv(RES / "calibration_linked_sites.csv", index=False)
    comp = pd.DataFrame([describe(fused, "fused GQDs, Stage 3a (50)"), describe(linked, f"linked carbon ({len(linked)})")])
    by_site = sites.groupby("site_type").agg(n=("E_NO2_eV", "size"), E_NO2_median=("E_NO2_eV", "median"),
                                             E_NO2_min=("E_NO2_eV", "min"), E_NO2_max=("E_NO2_eV", "max"),
                                             chemisorbed=("chemisorbed", "sum"), q_NO2_median=("q_NO2_e", "median")).reset_index()
    show = ["design", "formula", "gqd_gap_eV", "E_NO2_eV", "site_NO2", "NO2_chemisorbed", "q_NO2_e",
            "selectivity_margin_eV", "sensing_score", "recovery_s", "response_20ppb_RH50_e", "humidity_equiv_ppb"]
    lines = ["# Stage 3d L2: linked-carbon calibration (GFN2-xTB)", "",
             f"{len(linked)} hand-made designs (`designs.py`), all five gases, sites ring centre/edge, triple bond, pore. "
             f"Twin: Stage 3c `twin()` unchanged (20 ppb NO2, 50% RH, recovery spec {SPEC_RECOVERY_S:.0f} s). "
             "Fused comparison: the 50 Stage 3a calibration GQDs (same xTB protocol).", "",
             "## Linked vs fused", "", md_table(comp.T.reset_index().rename(columns={"index": "", 0: "fused", 1: "linked"})), "",
             "## NO2 binding by site type (best orientation at each site, all linked designs)", "", md_table(by_site), "",
             "## All linked designs (by Stage 3a score)", "",
             md_table(linked.sort_values("sensing_score", ascending=False)[show]), "",
             "## Top 5 by twin score", "",
             md_table(linked.sort_values("twin_score", ascending=False)[show].head(5)), ""]
    (RES / "summary.md").write_text("\n".join(lines))
    print("\n".join(lines))
    plot(linked, fused, sites)


if __name__ == "__main__":
    main()
