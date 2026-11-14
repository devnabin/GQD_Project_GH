# Created date: 2026-11-13 (America/Chicago)
"""Copy kept xTB geometries of linked designs into a dft_gpu.py benchmark folder.

    python Stage4/prepare_linked.py OUT_DIR design1 design2 ...

Same as Stage3d/prepare_dft.py, but with a chosen output folder.
"""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
out = Path(sys.argv[1])
recs = {json.loads(x)["design"]: json.loads(x)
        for x in (ROOT / "Stage3d" / "results" / "calibration_linked.jsonl").read_text().splitlines()}
shutil.copytree(ROOT / "Stage3a" / "data" / "dft_benchmark" / "refs", out / "refs", dirs_exist_ok=True)
for name in sys.argv[2:]:
    shutil.copytree(ROOT / "Stage3d" / "data" / "geometries" / name, out / name, dirs_exist_ok=True)
    (out / name / "xtb.json").write_text(json.dumps(recs[name], indent=1))
    print(f"{name}: {len(list((out / name).glob('*/xtbopt.xyz')))} geometries")
