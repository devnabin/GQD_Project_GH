# Created date: 2026-11-12 (America/Chicago)
"""Summarise the calibration run: how do the NO2 sensing numbers depend on the GQD?

    .venv/bin/python Stage3a/analyze.py

Reads data/calibration.csv, writes results/summary.md and results/sensing_vs_gap.png.
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
sys.path.insert(0, str(HERE.parent))
from Stage3a.sensing import BOND_A, E_HARD, E_SOFT, SEL_MARGIN, sensing_numbers  # noqa: E402

# validated categorical pair (light surface): slot 1 blue, slot 2 orange
COLOURS = {"physisorbed": "#2a78d6", "chemisorbed": "#eb6834"}
MARKERS = {"physisorbed": "o", "chemisorbed": "^"}
INK, MUTED, GRID, SURFACE = "#1f1f1e", "#6b6a65", "#e4e3df", "#fcfcfb"


def md_table(df):
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, row in df.iterrows():
        cells = [f"{v:.2f}" if isinstance(v, (float, np.floating)) else str(v) for v in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def load():
    d = pd.read_csv(HERE / "data" / "calibration.csv")
    # recompute the derived numbers with the current score definition
    derived = pd.DataFrame([sensing_numbers(row) for row in d.to_dict("records")])
    d = d.drop(columns=[c for c in derived.columns if c in d.columns]).join(derived)
    d["NO2_bond"] = np.where(d.dmin_NO2_A < BOND_A, "chemisorbed", "physisorbed")
    d["O2_bond"] = np.where(d.dmin_O2_A < BOND_A, "chemisorbed", "physisorbed")
    return d


def plot(d, path, panels=None, shape=(2, 2), size=(10, 7.5)):
    panels = panels or [("E_NO2_eV", "NO₂ adsorption energy (eV)"),
                        ("charge_to_NO2_e", "Charge moved to NO₂ (e)"),
                        ("E_O2_eV", "O₂ adsorption energy (eV) — xTB unreliable, not scored"),
                        ("humidity_margin_eV", "NO₂ preference over H₂O (eV)")]
    plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                         "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK})
    fig, axes = plt.subplots(*shape, figsize=size, facecolor=SURFACE, squeeze=False)
    for ax, (col, title) in zip(axes.flat, panels):
        ax.set_facecolor(SURFACE)
        ax.grid(True, color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for kind in ("physisorbed", "chemisorbed"):
            sub = d[d.NO2_bond == kind]
            ax.scatter(sub.dataset_gap_eV, sub[col], s=42, c=COLOURS[kind], marker=MARKERS[kind],
                       edgecolors=SURFACE, linewidths=1.5, label=f"NO₂ {kind}", zorder=3)
        ax.axhline(0, color=MUTED, linewidth=0.8, zorder=1)
        ax.set_title(title, loc="left", fontsize=11, color=INK)
        ax.set_xlabel("GQD HOMO–LUMO gap, xTB (eV)")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def main():
    RESULTS.mkdir(exist_ok=True)
    d = load()
    plot(d, RESULTS / "sensing_vs_gap.png")
    plot(d, RESULTS / "score_vs_gap.png", panels=[("sensing_score", "NO₂ sensing score (e)")],
         shape=(1, 1), size=(6.5, 4.5))
    top = d.sort_values("sensing_score", ascending=False)[
        ["Structure_Name", "n_hex", "dataset_gap_eV", "E_NO2_eV", "NO2_bond", "charge_to_NO2_e",
         "reversibility", "selectivity_margin_eV", "sensing_score"]].head(10)

    gap_err = (d.gqd_gap_eV - d.dataset_gap_eV)
    d["gap_bin"] = pd.cut(d.dataset_gap_eV, bins=[0, 0.4, 0.8, 1.2, 1.6, 2.1])
    by_bin = d.groupby("gap_bin", observed=True).agg(
        n=("Structure_Name", "size"),
        E_NO2=("E_NO2_eV", "median"), charge_NO2=("charge_to_NO2_e", "median"),
        NO2_chemisorbed=("NO2_bond", lambda s: f"{(s == 'chemisorbed').sum()}/{len(s)}"),
        E_O2=("E_O2_eV", "median"),
        O2_chemisorbed=("O2_bond", lambda s: f"{(s == 'chemisorbed').sum()}/{len(s)}"),
        E_H2O=("E_H2O_eV", "median"), E_NH3=("E_NH3_eV", "median"), E_CO=("E_CO_eV", "median"),
        score_median=("sensing_score", "median"), score_max=("sensing_score", "max"),
    ).reset_index().rename(columns={"gap_bin": "gap (eV)"})
    by_bin["gap (eV)"] = by_bin["gap (eV)"].astype(str)

    cols = ["E_NO2_eV", "charge_to_NO2_e", "E_O2_eV", "E_H2O_eV", "humidity_margin_eV", "selectivity_margin_eV",
            "sensing_score"]
    corr = pd.DataFrame({x: [d[c].corr(d[x], method="spearman") for c in cols]
                         for x in ["dataset_gap_eV", "dataset_homo_eV", "n_hex"]}, index=cols).reset_index()
    corr = corr.rename(columns={"index": "descriptor", "dataset_gap_eV": "vs gap",
                                "dataset_homo_eV": "vs HOMO", "n_hex": "vs size"})

    text = [
        "# Stage 3a calibration: NO₂ sensing numbers for dataset GQDs", "",
        f"{len(d)} GQDs, gap-stratified, {d.n_hex.min()}-{d.n_hex.max()} hexagons. "
        f"All optimisations converged: {int(d.all_converged.sum())}/{len(d)}. "
        f"Mean time per GQD: {d.seconds.mean():.0f} s.", "",
        "## Check: our GQD gap vs the dataset xTB gap", "",
        f"Mean difference {gap_err.mean():+.3f} eV, mean absolute {gap_err.abs().mean():.3f} eV, "
        f"Pearson r = {d.gqd_gap_eV.corr(d.dataset_gap_eV):.3f}.", "",
        "## By gap range (medians; energies in eV, charge in e)", "", md_table(by_bin), "",
        f"Chemisorbed = shortest gas-GQD distance < {BOND_A} Å after optimisation (a covalent bond formed).", "",
        "## Spearman correlation of each descriptor with gap, HOMO and size", "", md_table(corr), "",
        "![sensing vs gap](sensing_vs_gap.png)", "",
        "## NO₂ sensing score", "",
        f"score = charge to NO₂ × reversibility × selectivity. Reversibility is 1 for E_NO2 ≥ {E_SOFT} eV and "
        f"falls linearly to 0 at {E_HARD} eV. Selectivity is 1 when NO₂ binds ≥ {SEL_MARGIN} eV more strongly "
        "than H₂O, NH₃ and CO. O₂ is not scored (xTB unreliable for O₂).", "",
        f"Score > 0 for {(d.sensing_score > 0).sum()}/{len(d)} GQDs; "
        f"selectivity < 1 for {(d.selectivity < 1).sum()}/{len(d)}.", "",
        "### Top 10", "", md_table(top), "",
        "![score vs gap](score_vs_gap.png)", "",
    ]
    (RESULTS / "summary.md").write_text("\n".join(text))
    print("\n".join(text))


if __name__ == "__main__":
    sys.exit(main())
