#!/usr/bin/env python3
"""
Run GFN2-xTB on the top 50 candidate structures

Reads mol_id from the top 50 candidates file, finds the matching xyz
file for each one, and runs xTB to get the actual HOMO, LUMO, and
HOMO-LUMO gap.

Input:
  - top_50_candidates/top_50_fused_lowest_bandgap_structures.xlsx
  - top_50_xyz/ (xyz files for the top 50 structures)

Output:
  - top_50_xtb_results.csv (mol_id, homo_ev, lumo_ev, actual_gap_ev, status)

xTB settings:
  - Method: --opt loose --gfn 2 --norestart --json
  - Timeout: 600 seconds per molecule

Usage:
  python run_xtb_top50.py --workers 8
"""

import os
import sys
import subprocess
import pandas as pd
import json
import shutil
import argparse
from pathlib import Path
from multiprocessing import Pool, cpu_count

PROJECT_DIR = Path(__file__).resolve().parent.parent
TOP50_EXCEL = PROJECT_DIR / "Top_50_candidates" / "top_50_fused_lowest_bandgap_structures.xlsx"
XYZ_DIR = PROJECT_DIR / "top_50_xyz"

RESULTS_DIR = PROJECT_DIR / "top_50_xtb_results"
LOGS_DIR = RESULTS_DIR / "molecule_logs"
OUTPUT_CSV = RESULTS_DIR / "top_50_xtb_results.csv"

XTB_METHOD = "--opt loose --gfn 2 --norestart --json"
XTB_TIMEOUT = 900  
OMP_NUM_THREADS = "1"      
OMP_STACKSIZE = "4G"      

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def run_xtb_single(mol_info):
    mol_id = mol_info["mol_id"]
    xyz_filename = mol_info["xyz_filename"]
    xyz_path = mol_info["xyz_path"]

    mol_work_dir = LOGS_DIR / mol_id
    mol_work_dir.mkdir(parents=True, exist_ok=True)

    try:
        os.environ['OMP_NUM_THREADS'] = OMP_NUM_THREADS
        os.environ['OMP_STACKSIZE'] = OMP_STACKSIZE
        shutil.copy(xyz_path, mol_work_dir / xyz_filename)
        original_dir = os.getcwd()
        os.chdir(mol_work_dir)

        try:
            cmd = f"xtb {xyz_filename} {XTB_METHOD}"
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=XTB_TIMEOUT, env=os.environ.copy()
            )

            if result.returncode != 0:
                return {
                    "mol_id": mol_id, "homo_ev": None, "lumo_ev": None,
                    "actual_gap_ev": None, "status": "XTB_FAILED",
                    "error": result.stderr[:200]
                }

            json_file = mol_work_dir / "xtbout.json"
            if not json_file.exists():
                return {
                    "mol_id": mol_id, "homo_ev": None, "lumo_ev": None,
                    "actual_gap_ev": None, "status": "JSON_NOT_FOUND",
                    "error": "xtbout.json not found"
                }

            with open(json_file, "r") as f:
                data = json.load(f)

            gap_ev = data.get("HOMO-LUMO gap / eV")
            orbitals = data.get("orbital energies / eV", [])

            if gap_ev is not None and len(orbitals) > 0:
                homo_idx = len(orbitals) // 2 - 1
                lumo_idx = len(orbitals) // 2
                return {
                    "mol_id": mol_id, "homo_ev": orbitals[homo_idx],
                    "lumo_ev": orbitals[lumo_idx], "actual_gap_ev": gap_ev,
                    "status": "SUCCESS", "error": None
                }
            else:
                return {
                    "mol_id": mol_id, "homo_ev": None, "lumo_ev": None,
                    "actual_gap_ev": None, "status": "PARSE_FAILED",
                    "error": "Could not extract gap/orbitals from JSON"
                }

        finally:
            os.chdir(original_dir)

    except subprocess.TimeoutExpired:
        return {
            "mol_id": mol_id, "homo_ev": None, "lumo_ev": None,
            "actual_gap_ev": None, "status": "TIMEOUT",
            "error": f"xTB exceeded {XTB_TIMEOUT}s timeout"
        }
    except Exception as e:
        return {
            "mol_id": mol_id, "homo_ev": None, "lumo_ev": None,
            "actual_gap_ev": None, "status": "EXCEPTION", "error": str(e)[:200]
        }


def main():
    parser = argparse.ArgumentParser(description="Run GFN2-xTB on the top 50 candidates")
    parser.add_argument("--workers", type=int, default=max(1, cpu_count() // 2))
    args = parser.parse_args()

    print(f"Loading mol_ids from {TOP50_EXCEL.name}...")
    df = pd.read_excel(TOP50_EXCEL)
    print(f"Loaded {len(df)} candidates")

    molecules = []
    for mol_id in df["mol_id"]:
        mol_num = mol_id.split("_")[-1]
        xyz_filename = f"gqd_{mol_num}.xyz"
        xyz_path = XYZ_DIR / xyz_filename

        if xyz_path.exists():
            molecules.append({
                "mol_id": mol_id,
                "xyz_filename": xyz_filename,
                "xyz_path": xyz_path
            })
        else:
            print(f"  Missing xyz file for {mol_id}: {xyz_filename}")

    print(f"Found xyz files for {len(molecules)}/{len(df)} candidates")
    print(f"Running xTB with {args.workers} workers...\n")

    with Pool(processes=args.workers) as pool:
        results = pool.map(run_xtb_single, molecules)

    df_results = pd.DataFrame(results)
    df_results.to_csv(OUTPUT_CSV, index=False)

    success_count = (df_results["status"] == "SUCCESS").sum()
    print(f"\nDone: {success_count}/{len(df_results)} succeeded")
    print(f"Saved: {OUTPUT_CSV}")

    # Compare against the paper's reported values, if available
    if "actual_gap_ev" in df.columns:
        merged = df_results.merge(
            df[["mol_id", "actual_gap_ev"]].rename(columns={"actual_gap_ev": "paper_gap_ev"}),
            on="mol_id", how="left"
        )
        merged["diff_ev"] = merged["actual_gap_ev"] - merged["paper_gap_ev"]
        comparison_csv = RESULTS_DIR / "top_50_xtb_comparison.csv"
        merged.to_csv(comparison_csv, index=False)
        print(f"Saved comparison against paper values: {comparison_csv}")


if __name__ == "__main__":
    main()
