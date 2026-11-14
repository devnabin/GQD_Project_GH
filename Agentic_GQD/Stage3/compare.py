# Created date: 2026-11-12 (America/Chicago)
"""Compare evolution runs on the same xTB budget (e.g. LLM vs random edits, several seeds each).

    .venv/bin/python Stage3/compare.py llm_s0 random_s0
    .venv/bin/python Stage3/compare.py llm_v2_s1 llm_v2_s2 random_v2_s1 random_v2_s2 --name v2

Runs are grouped by their mutator. Writes results/compare[_NAME].md and .png.
"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import mannwhitneyu  # noqa: E402

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
sys.path.insert(0, str(HERE.parent))
from Stage3a.sensing import sensing_numbers  # noqa: E402

INK, MUTED, GRID, SURFACE = "#1f1f1e", "#6b6a65", "#e4e3df", "#fcfcfb"
COLOURS = {"llm": "#2a78d6", "random": "#eb6834"}  # validated categorical pair (light surface)


def start_best() -> float:
    """Best score in the starting population (the Stage 3a calibration set), shared by all runs."""
    cal = pd.read_csv(HERE.parent / "Stage3a" / "data" / "calibration.csv")
    return max(sensing_numbers(r)["sensing_score"] for r in cal.to_dict("records") if r["all_converged"])


def load(run):
    rows = pd.DataFrame([json.loads(x) for x in (RESULTS / run / "children.jsonl").read_text().splitlines()])
    config = json.loads((RESULTS / run / "config.json").read_text())
    return rows, config


def run_metrics(d, best0):
    scored = d[d.evaluated.fillna(False).astype(bool)]
    repaired = d["repair"].fillna("").astype(bool) if "repair" in d else pd.Series(False, index=d.index)
    return {"proposed": len(d), "valid": d.valid.mean(), "repaired by code": (repaired & d.valid).mean(),
            "xTB-scored": len(scored), "beat parent": (scored.sensing_score > scored.parent_score).mean(),
            "NO2 chemisorbed": scored.NO2_chemisorbed.mean(), "mean scored": scored.sensing_score.mean(),
            "best": scored.sensing_score.max(), f"above start ({best0:.3f})": int((scored.sensing_score > best0).sum())}


def fmt(key, value):
    if key in ("valid", "repaired by code", "beat parent", "NO2 chemisorbed"):
        return f"{float(value):.0%}"
    return f"{value:.3f}" if isinstance(value, float) else str(value)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--name", default="")
    args = ap.parse_args()
    suffix = f"_{args.name}" if args.name else ""
    best0 = start_best()
    data = {run: load(run) for run in args.runs}

    plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                         "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK})
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), facecolor=SURFACE)
    for ax in axes:
        ax.set_facecolor(SURFACE)
        ax.grid(True, color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)

    per_run, scores_by_mutator, labelled = {}, {}, set()
    for run, (d, config) in data.items():
        mutator = config["mutator"]
        colour = COLOURS.get(mutator, MUTED)
        scored = d[d.evaluated.fillna(False).astype(bool)].sort_values(["generation", "child_id"])
        best = np.maximum.accumulate(np.r_[best0, scored.sensing_score.to_numpy()])
        label = mutator if mutator not in labelled else None
        labelled.add(mutator)
        axes[0].step(np.arange(len(best)), best, where="post", color=colour, linewidth=2, alpha=0.85, label=label)
        per_gen = scored.groupby("generation").sensing_score.mean()
        axes[1].plot(per_gen.index, per_gen.values, color=colour, linewidth=2, alpha=0.85, marker="o",
                     markersize=8, markeredgecolor=SURFACE, markeredgewidth=1.5, label=label)
        per_run[run] = {"mutator": mutator} | run_metrics(d, best0)
        scores_by_mutator.setdefault(mutator, []).extend(scored.sensing_score.tolist())

    axes[0].set_title("Best NO₂ sensing score found so far (one line per run)", loc="left", fontsize=11)
    axes[0].set_xlabel("xTB-scored children")
    axes[1].set_title("Mean score of the scored children, per generation", loc="left", fontsize=11)
    axes[1].set_xlabel("generation")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=len(labels), frameon=False, bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(RESULTS / f"compare{suffix}.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)

    table = pd.DataFrame(per_run).T
    keys = [k for k in table.columns if k != "mutator"]
    lines = [f"# Stage 3: evolution runs compared{(' (' + args.name + ')') if args.name else ''}", "",
             f"All runs start from the same population (best score {best0:.3f}). The left plot's y-axis is zoomed in.",
             "", "## Per run", "", "| run | mutator | " + " | ".join(keys) + " |", "|---" * (len(keys) + 2) + "|"]
    for run, row in table.iterrows():
        lines.append(f"| {run} | {row.mutator} | " + " | ".join(fmt(k, row[k]) for k in keys) + " |")
    lines += ["", "## Per mutator (mean ± sd over runs)", "", "| mutator | runs | best | mean scored | valid |",
              "|---|---|---|---|---|"]
    for mutator, group in table.groupby("mutator"):
        b, m, v = (group[k].astype(float) for k in ("best", "mean scored", "valid"))
        sd = (lambda x: x.std(ddof=1)) if len(group) > 1 else (lambda x: 0.0)
        lines.append(f"| {mutator} | {len(group)} | {b.mean():.3f} ± {sd(b):.3f} | {m.mean():.3f} ± {sd(m):.3f} | "
                     f"{v.mean():.0%} |")
    if {"llm", "random"} <= set(scores_by_mutator):
        p = mannwhitneyu(scores_by_mutator["llm"], scores_by_mutator["random"], alternative="greater").pvalue
        lines += ["", f"Mann-Whitney (scores of all scored children, LLM > random): p = {p:.3g}. "
                  "Children within a run are not independent, so treat this as a rough guide; the per-run "
                  "best scores are the fairer comparison."]
    lines += ["", f"![compare](compare{suffix}.png)", ""]
    (RESULTS / f"compare{suffix}.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
