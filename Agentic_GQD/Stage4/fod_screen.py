# Created date: 2026-11-13 (America/Chicago)
"""xTB fractional-occupation (FOD) screen for open-shell character. Runs on the server CPU.

    python Stage4/fod_screen.py XYZ_DIR_OR_FILES... --out Stage4/results/fod.csv [--workers 8]

For each bare-GQD geometry (xyz), runs `xtb --gfn 2 --fod` (single point, Fermi smearing) and
records N_FOD and the xTB gap. A larger N_FOD means more static correlation / open-shell
character; the threshold is calibrated against the broken-symmetry DFT check (bs_check.jsonl).
"""

import argparse
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd


def fod(xyz: Path) -> dict:
    with tempfile.TemporaryDirectory() as work:
        (Path(work) / "m.xyz").write_text(xyz.read_text())
        out = subprocess.run(["xtb", "m.xyz", "--gfn", "2", "--fod"], cwd=work, capture_output=True, text=True,
                             env={"OMP_NUM_THREADS": "1", "PATH": __import__("os").environ["PATH"]}).stdout
    nfod = re.search(r"NFOD\s*:\s*([-\d.]+)", out)
    gap = re.search(r"HOMO-LUMO GAP\s+([-\d.]+)\s+eV", out)
    return {"xyz": str(xyz), "N_FOD": float(nfod.group(1)) if nfod else float("nan"),
            "gap_fod_eV": float(gap.group(1)) if gap else float("nan")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    files = [p for path in args.paths for p in (sorted(path.glob("*.xyz")) if path.is_dir() else [path])]
    with ThreadPoolExecutor(args.workers) as pool:
        rows = list(pool.map(fod, files))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.out, index=False)
    print(pd.DataFrame(rows).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
