# Created date: 2026-11-10 (America/Chicago)
"""Stage 1: convert the full GQD dataset to hexagon coordinates and attach xTB gaps.

Input
  ../data/bigcsv/filtered.csv                              all generated GQDs (Structure_Name, SMILES, ...)
  ../GFN2-xTB _results/initial_5000_xtb_results.csv        xTB HOMO/LUMO/gap (mol_id = MOL_<n>)
  ../GFN2-xTB _results/ML_xtb_11000_structures.csv         xTB HOMO/LUMO/gap (mol_id = MOL_<n>)

Output (Stage1/data/)
  gqd_hex_dataset.csv         one row per structure: SMILES, hexagon list (JSON), xTB values if any
  xtb_ids_without_smiles.txt  xTB-labelled IDs that have no SMILES in filtered.csv

Every hexagon list is checked by converting it back (hex -> SMILES) and comparing
with the original canonical SMILES; hex_status records the result.

Usage (from Agentic_GQD/):  .venv/bin/python Stage1/build_hex_dataset.py
"""

import csv
import json
import time
from collections import Counter
from pathlib import Path

from rdkit import Chem

from gqd_hex import HexError, hex_to_smiles, mol_to_hex

HERE = Path(__file__).resolve().parent   # Agentic_GQD/Stage1
ROOT = HERE.parents[1]                   # GQD_Project_GH
SOURCE_CSV = ROOT / "data" / "bigcsv" / "filtered.csv"
XTB_FILES = {
    "initial_5000": (ROOT / "GFN2-xTB _results" / "initial_5000_xtb_results.csv",
                     "HOMO_eV", "LUMO_eV", "HOMO_LUMO_gap_eV"),
    "ml_11000": (ROOT / "GFN2-xTB _results" / "ML_xtb_11000_structures.csv",
                 "homo_ev", "lumo_ev", "actual_gap_ev"),
}
OUT_DIR = HERE / "data"
OUT_CSV = OUT_DIR / "gqd_hex_dataset.csv"
OUT_MISSING = OUT_DIR / "xtb_ids_without_smiles.txt"
FIELDS = ["Structure_Name", "SMILES", "n_hex", "hexagons",
          "xtb_homo_eV", "xtb_lumo_eV", "xtb_gap_eV", "xtb_source", "hex_status", "hex_error"]


def load_xtb() -> dict[str, dict]:
    """Map gqd_<n> -> xTB values from both result files."""
    xtb = {}
    for source, (path, homo, lumo, gap) in XTB_FILES.items():
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if row.get("status", "").lower() != "success":
                    continue
                name = row["mol_id"].replace("MOL_", "gqd_")
                xtb[name] = {"xtb_homo_eV": row[homo], "xtb_lumo_eV": row[lumo],
                             "xtb_gap_eV": row[gap], "xtb_source": source}
    return xtb


def convert(smiles: str) -> dict:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"hex_status": "error", "hex_error": "RDKit could not parse the SMILES"}
    canonical = Chem.MolToSmiles(mol, canonical=True)
    try:
        hexagons = mol_to_hex(mol)
        roundtrip = hex_to_smiles(hexagons)
    except HexError as error:
        return {"SMILES": canonical, "hex_status": "error", "hex_error": str(error)}
    status = "ok" if roundtrip == canonical else "mismatch"
    return {"SMILES": canonical, "n_hex": len(hexagons),
            "hexagons": json.dumps([list(cell) for cell in hexagons], separators=(",", ":")),
            "hex_status": status, "hex_error": "" if status == "ok" else "round-trip SMILES differs"}


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    xtb = load_xtb()
    seen_names = set()
    status = Counter()
    labelled = 0
    start = time.time()

    with SOURCE_CSV.open(newline="", encoding="utf-8") as source, \
         OUT_CSV.open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=FIELDS)
        writer.writeheader()
        for count, row in enumerate(csv.DictReader(source), start=1):
            name = row["Structure_Name"]
            seen_names.add(name)
            record = {"Structure_Name": name, "SMILES": row["SMILES"]} | convert(row["SMILES"])
            if name in xtb:
                record |= xtb[name]
                labelled += 1
            writer.writerow(record)
            status[record["hex_status"]] += 1
            if count % 10000 == 0:
                print(f"{count:,} rows  {dict(status)}  {time.time() - start:.0f}s", flush=True)

    missing = sorted(set(xtb) - seen_names)
    OUT_MISSING.write_text("\n".join(missing) + "\n")

    print(f"\nDone in {time.time() - start:.0f}s -> {OUT_CSV}")
    print(f"  structures:          {sum(status.values()):,}")
    print(f"  hex conversion:      {dict(status)}")
    print(f"  with xTB gap:        {labelled:,} of {len(xtb):,} xTB results")
    print(f"  xTB IDs not found:   {len(missing):,} (listed in {OUT_MISSING.name})")


if __name__ == "__main__":
    main()
