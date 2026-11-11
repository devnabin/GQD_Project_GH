"""Return one randomly selected SMILES string from pilot.csv."""

import csv
import random
from pathlib import Path

PILOT_CSV = Path(__file__).with_name("pilot.csv")

def random_smiles() -> str:
    """Choose a nonempty SMILES value from pilot.csv."""
    with PILOT_CSV.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None or "SMILES" not in reader.fieldnames:
            raise ValueError(f"No SMILES column found in {PILOT_CSV}")
        smiles = [row["SMILES"].strip() for row in reader if row["SMILES"].strip()]

    if not smiles:
        raise ValueError(f"No SMILES values found in {PILOT_CSV}")
    return random.choice(smiles)