# Created date: 2026-11-12 (America/Chicago)
"""Stage 3c: a simple virtual NO2 sensor ("sensor twin") on top of the Stage 3a numbers.

    .venv/bin/python Stage3c/twin.py            # calibration GQDs + best GQDs of the evolution runs

Molecule -> film -> signal, at real gas concentrations:
  1. Molecule: adsorption energy E_g and charge q_g of each gas (xTB, Stage 3a; DFT later).
  2. Film: competitive Langmuir coverage of one site type at 298 K,
         theta_g = K_g p_g / (1 + sum_j K_j p_j),   K_g = exp(-(E_g - T dS_g) / kT)  [1/bar]
     with the entropy lost on adsorption from Campbell and Sellers (JACS 2012):
         S_ads = 0.70 S_gas - 3.3 R   ->   dS_g = -0.30 S_gas - 3.3 R.
  3. Signal: electrons withdrawn from the GQD per site, n = sum_g theta_g * (-q_g).
     The NO2 response is n(with NO2) - n(same air without NO2).
  4. Recovery: tau = exp(-E_NO2 / kT) / nu, nu = 1e12 1/s (as in Stage 3a).
  5. Humidity: the change in n when the air goes from 30% to 70% relative humidity, expressed
     as the NO2 concentration that gives the same response ("humidity-equivalent NO2").

O2 is left out (xTB binds it wrongly; DFT values come later). All numbers are per adsorption site
and relative; the model has no film thickness, contacts or carrier density.
"""

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS = HERE / "results"

KB_EV = 8.617333e-5          # eV/K
R_J = 8.314462               # J/(mol K)
EV_PER_J_MOL = 1.0 / 96485.33
T = 298.15
KT = KB_EV * T
NU = 1e12                    # attempt frequency for desorption (1/s)
P_SAT_H2O = 0.03169          # bar, water at 25 C
GAS_ENTROPY = {"NO2": 240.06, "H2O": 188.83, "NH3": 192.77, "CO": 197.67}  # J/(mol K), 298 K, 1 bar
GASES = list(GAS_ENTROPY)

# Typical outdoor air (bar, at about 1 bar total). NO2 and relative humidity are set per case.
BACKGROUND = {"NH3": 10e-9, "CO": 0.5e-6}
TARGET_PPB = 20.0            # NO2 level to detect (WHO 24-h guideline is about 13 ppb)
SPEC_RECOVERY_S = 300.0      # sensor spec: recover within 5 minutes


def entropy_loss_ev(gas: str) -> float:
    """T * dS of adsorption in eV (negative), Campbell-Sellers correlation."""
    s_gas = GAS_ENTROPY[gas]
    return T * (-0.30 * s_gas - 3.3 * R_J) * EV_PER_J_MOL


def equilibrium_constants(energies: dict) -> dict:
    """K_g in 1/bar from adsorption energies (eV), using dG = E - T dS."""
    return {g: math.exp(-(energies[g] - entropy_loss_ev(g)) / KT) for g in energies}


def pressures(no2_ppb: float, rh: float) -> dict:
    return {"NO2": no2_ppb * 1e-9, "H2O": rh * P_SAT_H2O} | BACKGROUND


def coverage(k: dict, p: dict) -> dict:
    load = {g: k[g] * p[g] for g in k}
    total = 1.0 + sum(load.values())
    return {g: load[g] / total for g in k}


def withdrawn(k: dict, q: dict, p: dict) -> float:
    """Electrons withdrawn from the GQD per site (positive = p-type doping, like NO2)."""
    theta = coverage(k, p)
    return sum(theta[g] * -q[g] for g in theta)


def response(k, q, no2_ppb, rh) -> float:
    return withdrawn(k, q, pressures(no2_ppb, rh)) - withdrawn(k, q, pressures(0.0, rh))


def humidity_equivalent_ppb(k, q, rh_low=0.3, rh_high=0.7) -> float:
    """NO2 concentration (ppb) whose response equals the drift from rh_low to rh_high."""
    drift = abs(withdrawn(k, q, pressures(0.0, rh_high)) - withdrawn(k, q, pressures(0.0, rh_low)))
    if drift == 0:
        return 0.0
    lo, hi = 1e-6, 1e9
    if response(k, q, hi, 0.5) < drift:
        return float("inf")
    for _ in range(200):  # bisection in log space
        mid = math.sqrt(lo * hi)
        lo, hi = (mid, hi) if response(k, q, mid, 0.5) < drift else (lo, mid)
    return math.sqrt(lo * hi)


def twin(record: dict) -> dict:
    energies = {g: float(record[f"E_{g}_eV"]) for g in GASES}
    charges = {g: float(record[f"q_{g}_e"]) for g in GASES}
    k = equilibrium_constants(energies)
    tau = math.exp(-energies["NO2"] / KT) / NU
    p_target = pressures(TARGET_PPB, 0.5)
    theta = coverage(k, p_target)
    signal = response(k, charges, TARGET_PPB, 0.5)
    return {"theta_NO2_20ppb_RH50": theta["NO2"], "theta_H2O_RH50": theta["H2O"],
            "response_20ppb_RH50_e": signal, "recovery_s": tau,
            "meets_recovery_spec": tau <= SPEC_RECOVERY_S,
            "humidity_equiv_ppb": humidity_equivalent_ppb(k, charges),
            "twin_score": signal if tau <= SPEC_RECOVERY_S else 0.0}


def md_table(df: pd.DataFrame) -> str:
    """Markdown table without extra dependencies (3 significant digits for floats)."""
    fmt = lambda v: f"{v:.3g}" if isinstance(v, float) else str(v)
    rows = ["| " + " | ".join(df.columns) + " |", "|" + "---|" * len(df.columns)]
    rows += ["| " + " | ".join(fmt(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join(rows)


def load_records() -> pd.DataFrame:
    """Calibration GQDs (Stage 3a) plus the fully checked best GQDs of every evolution run."""
    import sys
    sys.path.insert(0, str(ROOT))
    from Stage3a.sensing import sensing_numbers

    cal = pd.read_csv(ROOT / "Stage3a" / "data" / "calibration.csv")
    cal = cal[cal.all_converged].assign(source="calibration", id=cal.Structure_Name)
    frames = [cal]
    for path in sorted((ROOT / "Stage3" / "results").glob("*/final_check.csv")):
        f = pd.read_csv(path)
        frames.append(f.assign(source=path.parent.name, id=path.parent.name + "/" + f.child_id))
    data = pd.concat(frames, ignore_index=True)
    data["score_stage3a"] = [sensing_numbers(r)["sensing_score"] for r in data.to_dict("records")]
    data["NO2_chemisorbed"] = data.dmin_NO2_A < 1.9
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.parse_args()
    RESULTS.mkdir(exist_ok=True)
    data = load_records()
    out = pd.concat([data[["id", "source", "n_hex", "gqd_gap_eV", "E_NO2_eV", "q_NO2_e", "E_H2O_eV",
                           "q_H2O_e", "NO2_chemisorbed", "score_stage3a"]],
                     pd.DataFrame([twin(r) for r in data.to_dict("records")])], axis=1)
    out.to_csv(RESULTS / "twin_results.csv", index=False)

    from scipy.stats import spearmanr
    ok = out[out.meets_recovery_spec]
    rho = spearmanr(out.score_stage3a, out.twin_score).statistic
    cols = ["id", "gqd_gap_eV", "E_NO2_eV", "NO2_chemisorbed", "score_stage3a", "recovery_s",
            "response_20ppb_RH50_e", "humidity_equiv_ppb"]
    lines = ["# Stage 3c sensor twin: first results", "",
             f"{len(out)} GQDs (Stage 3a calibration + full checks of the evolution runs). Conditions: "
             f"{TARGET_PPB:.0f} ppb NO2, 50% RH, 10 ppb NH3, 0.5 ppm CO, 298 K. Spec: recovery <= "
             f"{SPEC_RECOVERY_S:.0f} s. O2 not included. xTB energies and charges.", "",
             f"- Entropy cost T*dS at 298 K (eV): " + ", ".join(f"{g} {entropy_loss_ev(g):+.2f}" for g in GASES),
             f"- GQDs meeting the recovery spec: {len(ok)} of {len(out)}",
             f"- Spearman rank correlation, Stage 3a score vs twin score: {rho:.2f}", "",
             "## Top 10 by twin score", "", md_table(out.sort_values("twin_score", ascending=False)[cols].head(10)), "",
             "## Top 10 by Stage 3a score", "", md_table(out.sort_values("score_stage3a", ascending=False)[cols].head(10)), ""]
    (RESULTS / "summary.md").write_text("\n".join(lines))
    print("\n".join(lines))
    plot(out)


def plot(out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ink, muted, grid, surface = "#1f1f1e", "#6b6a65", "#e4e3df", "#fcfcfb"
    phys, chem = "#2a78d6", "#eb6834"
    plt.rcParams.update({"font.size": 10, "axes.edgecolor": muted, "axes.labelcolor": ink,
                         "xtick.color": muted, "ytick.color": muted, "text.color": ink})
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), facecolor=surface)
    e_spec = -KT * math.log(SPEC_RECOVERY_S * NU)  # binding energy where recovery = spec
    for ax in axes:
        ax.set_facecolor(surface)
        ax.grid(True, color=grid, linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.axvspan(-2.2, e_spec, color=grid, alpha=0.6, zorder=0)
        ax.set_xlim(-2.1, -0.2)
        ax.set_xlabel("NO₂ adsorption energy, xTB (eV)")
    for flag, colour, marker, label in [(False, phys, "o", "NO₂ physisorbed"),
                                        (True, chem, "^", "NO₂ chemisorbed")]:
        sub = out[out.NO2_chemisorbed == flag]
        axes[0].scatter(sub.E_NO2_eV, sub.response_20ppb_RH50_e, s=46, color=colour, marker=marker,
                        edgecolor=surface, linewidth=1.2, label=label, zorder=3)
        axes[1].scatter(sub.E_NO2_eV, sub.recovery_s, s=46, color=colour, marker=marker,
                        edgecolor=surface, linewidth=1.2, zorder=3)
    axes[0].set_yscale("log")
    axes[0].set_title("Predicted response to 20 ppb NO₂ at 50% RH (e per site)", loc="left", fontsize=11)
    axes[1].set_yscale("log")
    axes[1].axhline(SPEC_RECOVERY_S, color=muted, linewidth=1, linestyle="--")
    axes[1].text(-0.25, SPEC_RECOVERY_S * 1.6, "5 min spec", ha="right", color=muted, fontsize=9)
    axes[1].set_title("Predicted recovery time (s)", loc="left", fontsize=11)
    for ax in axes:
        ax.text(-2.05, ax.get_ylim()[0] * 3, "too slow to recover (> 5 min)", color=muted, fontsize=9, va="bottom")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(RESULTS / "twin_response_vs_binding.png", dpi=150, facecolor=surface)
    plt.close(fig)


if __name__ == "__main__":
    main()
