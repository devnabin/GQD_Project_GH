# Created date: 2026-11-12 (America/Chicago); updated 2026-11-13 for the full benchmark
"""Compare the GPU DFT benchmark with xTB (rank correlations, parity plot, O2, selectivity).

    .venv/bin/python Stage3a/dft_gpu.py Stage3a/data/dft_benchmark --summary-only   # first
    .venv/bin/python Stage3a/analyze_dft_benchmark.py

Reads Stage3a/data/dft_benchmark/summary.csv and <gqd>/dft.csv (written by dft_gpu.py), and
bs_check.jsonl if present (broken-symmetry UKS energies of bare GQDs). Writes
Stage3a/results/dft_benchmark.md, dft_benchmark.csv and dft_vs_xtb.png.
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import pearsonr, spearmanr  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from Stage3a.sensing import BOND_A  # noqa: E402

BENCH = HERE / "data" / "dft_benchmark"
RESULTS = HERE / "results"
INK, MUTED, GRID, SURFACE = "#1f1f1e", "#6b6a65", "#e4e3df", "#fcfcfb"
PHYS, CHEM = "#2a78d6", "#eb6834"  # same pair as the Stage 3a plots
CT_STATE = 0.3  # |charge on gas| above this in DFT = a charge-separated (ion-pair) SCF state


def md(df):
    """Markdown table without the optional tabulate package."""
    cells = [[f"{v:.3f}" if isinstance(v, float) else str(v) for v in row] for row in df.itertuples(index=False)]
    return "\n".join(["| " + " | ".join(map(str, df.columns)) + " |", "|---" * len(df.columns) + "|"]
                     + ["| " + " | ".join(r) + " |" for r in cells])


def stats(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.ptp(x) > 0 and np.ptp(y) > 0
    return {"n": len(x), "rho": spearmanr(x, y).statistic if ok else float("nan"),
            "r": pearsonr(x, y).statistic if ok else float("nan"),
            "MAE": float(np.mean(np.abs(x - y))), "bias": float(np.mean(y - x))}


def main():
    s = pd.read_csv(BENCH / "summary.csv")
    s["dmin_NO2_A"] = [json.loads((BENCH / n / "xtb.json").read_text())["dmin_NO2_A"] for n in s.name]
    s["chemisorbed"] = s.dmin_NO2_A < BOND_A
    g = pd.DataFrame({"name": s.name, "n_hex": s.n_hex, "gap_xTB": s.gap_xTB_eV, "chemisorbed": s.chemisorbed,
                      "converged_DFT": s.all_converged_DFT})
    for q, col in [("E_NO2", "E_NO2_eV"), ("q_NO2", "charge_to_NO2_e"), ("E_CO", "E_CO_eV"), ("E_H2O", "E_H2O_eV"),
                   ("E_NH3", "E_NH3_eV"), ("E_O2", "E_O2_eV"), ("margin", "selectivity_margin_eV"),
                   ("score", "sensing_score")]:
        g[f"{q}_xTB"], g[f"{q}_DFT"] = s[f"{col}_xTB"], s[f"{col}_DFT"]
    g["interferent_xTB"], g["interferent_DFT"] = s.strongest_interferent_xTB, s.strongest_interferent_DFT

    bs_path = BENCH / "bs_check.jsonl"
    bs = pd.DataFrame([json.loads(x) for x in bs_path.read_text().splitlines()]) if bs_path.exists() else None

    quantities = ["E_NO2", "q_NO2", "E_CO", "E_H2O", "E_NH3", "E_O2", "margin", "score"]
    per_gqd = {q: stats(g[f"{q}_xTB"], g[f"{q}_DFT"]) for q in quantities}
    phys = g[~g.chemisorbed]
    per_phys = {q: stats(phys[f"{q}_xTB"], phys[f"{q}_DFT"]) for q in ["E_NO2", "q_NO2", "score"]}

    cx = pd.concat([pd.read_csv(BENCH / n / "dft.csv").assign(name=n) for n in g.name])
    cx["state"] = np.where(cx.q_gas_DFT_e.abs() > CT_STATE, "charge-separated", "neutral")
    cx["regime"] = np.where(cx.d_min_A < BOND_A, "bonded", "physisorbed")
    per_cx = []
    for (analyte, regime, state), grp in cx.groupby(["analyte", "regime", "state"]):
        e, c = stats(grp.E_ads_xTB_eV, grp.E_ads_DFT_eV), stats(-grp.q_gas_xTB_e, -grp.q_gas_DFT_e)
        per_cx.append({"analyte": analyte, "geometry": regime, "DFT state": state, "n": e["n"],
                       "E xTB mean": grp.E_ads_xTB_eV.mean(), "E DFT mean": grp.E_ads_DFT_eV.mean(),
                       "E rho": e["rho"], "charge xTB mean": -grp.q_gas_xTB_e.mean(),
                       "charge DFT mean": -grp.q_gas_DFT_e.mean()})
    per_cx = pd.DataFrame(per_cx)

    # ------------------------------------------------------------- figure
    plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                         "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK})
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.4), facecolor=SURFACE)
    panels = [("E_NO2", "NO₂ adsorption energy (eV)"), ("q_NO2", "Charge moved to NO₂ (e)"),
              ("score", "Sensing score (e)")]
    for ax, (q, title) in zip(axes, panels):
        ax.set_facecolor(SURFACE)
        ax.grid(True, color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        lo = min(g[f"{q}_xTB"].min(), g[f"{q}_DFT"].min())
        hi = max(g[f"{q}_xTB"].max(), g[f"{q}_DFT"].max())
        pad = 0.06 * (hi - lo or 1)
        ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad], color=MUTED, linewidth=1, linestyle="--", zorder=1)
        for chem, colour, marker, label in [(False, PHYS, "o", "NO₂ physisorbed (xTB)"),
                                            (True, CHEM, "^", "NO₂ chemisorbed (xTB)")]:
            sub = g[g.chemisorbed == chem]
            ax.scatter(sub[f"{q}_xTB"], sub[f"{q}_DFT"], s=64, color=colour, marker=marker,
                       edgecolor=SURFACE, linewidth=1.5, zorder=3, label=label)
        st = per_gqd[q]
        ax.set_title(f"{title}\nSpearman ρ = {st['rho']:.2f}, n = {st['n']}", loc="left", fontsize=10.5)
        ax.set_xlabel("xTB")
        ax.set_ylabel("DFT (ωB97X-V/def2-SVP)")
        ax.set_xlim(lo - pad, hi + pad)
        ax.set_ylim(lo - pad, hi + pad)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    RESULTS.mkdir(exist_ok=True)
    fig.savefig(RESULTS / "dft_vs_xtb.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)

    # ------------------------------------------------------------- report
    lines = ["# GPU DFT benchmark vs xTB (all 162 single points)", "",
             "wB97X-V/def2-SVP single points (GPU4PySCF, one A100) at the xTB geometries of 12 GQDs, all five "
             "gases. Source: `Stage3a/data/dft_benchmark/` (summary.csv, <gqd>/dft.csv).", "",
             f"All DFT SCFs converged: {bool(g.converged_DFT.all())}.", "",
             "## Per GQD (n = 12): xTB vs DFT", "", "| quantity | Spearman rho | Pearson r | MAE | mean DFT - xTB |",
             "|---|---|---|---|---|"]
    for q, st in per_gqd.items():
        lines.append(f"| {q} | {st['rho']:.2f} | {st['r']:.2f} | {st['MAE']:.3f} | {st['bias']:+.3f} |")
    lines += ["", f"Physisorbing GQDs only (n = {len(phys)}):", "", "| quantity | Spearman rho | Pearson r | MAE | mean DFT - xTB |",
              "|---|---|---|---|---|"]
    for q, st in per_phys.items():
        lines.append(f"| {q} | {st['rho']:.2f} | {st['r']:.2f} | {st['MAE']:.3f} | {st['bias']:+.3f} |")
    lines += ["", "## Per complex", "", md(per_cx)]
    cols = ["name", "gap_xTB", "chemisorbed", "E_NO2_xTB", "E_NO2_DFT", "q_NO2_xTB", "q_NO2_DFT", "margin_xTB",
            "margin_DFT", "interferent_DFT", "E_O2_xTB", "E_O2_DFT", "score_xTB", "score_DFT"]
    lines += ["", "## Per GQD values (sorted by xTB score)", "",
              md(g.sort_values("score_xTB", ascending=False)[cols])]
    if bs is not None:
        lines += ["", "## Broken-symmetry check of bare GQDs (UKS from a HOMO/LUMO-mixed guess)", "",
                  md(bs),
                  "", "A positive `lowering_eV` means the closed-shell (RKS) GQD reference is too high by that amount, "
                  "so DFT adsorption energies computed against it are too negative by about the same amount "
                  "(if the complex is fully relaxed to the same open-shell character)."]
    lines += ["", "![parity](dft_vs_xtb.png)", ""]
    (RESULTS / "dft_benchmark.md").write_text("\n".join(lines))
    g.to_csv(RESULTS / "dft_benchmark.csv", index=False)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
