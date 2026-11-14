# Created date: 2026-11-13 (America/Chicago)
"""Put the kept xTB geometries of chosen linked designs into the layout Stage3a/dft_gpu.py expects.

    .venv/bin/python Stage3d/prepare_dft.py gdy_rhomb4 naph_row4_n1      # -> Stage3d/data/dft_check/
Then (on the GPU server, gqd-dft env):  CUDA_VISIBLE_DEVICES=0 python Stage3a/dft_gpu.py Stage3d/data/dft_check
"""

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
out = HERE / "data" / "dft_check"
recs = {json.loads(x)["design"]: json.loads(x) for x in (HERE / "results" / "calibration_linked.jsonl").read_text().splitlines()}
shutil.copytree(ROOT / "Stage3a" / "data" / "dft_benchmark" / "refs", out / "refs", dirs_exist_ok=True)  # same xTB gas refs
for name in sys.argv[1:]:
    shutil.copytree(HERE / "data" / "geometries" / name, out / name, dirs_exist_ok=True)
    (out / name / "xtb.json").write_text(json.dumps(recs[name], indent=1))
    print(f"{name}: {len(list((out / name).glob('*/xtbopt.xyz')))} geometries")
