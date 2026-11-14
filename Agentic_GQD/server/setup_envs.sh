#!/usr/bin/env bash
# Created date: 2026-11-12 (America/Chicago)
# Create the two conda environments on the Linux GPU server (run on the server):
#   gqd      the Stage 3 loop: xTB, RDKit, gap predictor, LangChain (CPU only)
#   gqd-dft  GPU DFT with GPU4PySCF (CUDA 12)
#     bash server/setup_envs.sh > server/setup.log 2>&1
set -eo pipefail
source "$(conda info --base)/etc/profile.d/conda.sh"

has_env() { conda env list | awk '{print $1}' | grep -qx "$1"; }

if ! has_env gqd; then
  conda create -y -n gqd --override-channels -c conda-forge \
    python=3.12 xtb rdkit numpy scipy pandas pyarrow matplotlib lightgbm xgboost
fi
conda activate gqd
pip install --quiet torch --index-url https://download.pytorch.org/whl/cpu
pip install --quiet python-dotenv pydantic langgraph langchain-core langchain-openai
echo "== gqd env =="
xtb --version 2>&1 | grep -m1 -i "version"
python -c "import rdkit, lightgbm, xgboost, torch, langgraph; from rdkit import RDConfig; import os; \
print('rdkit', rdkit.__version__, '| lightgbm', lightgbm.__version__, '| xgboost', xgboost.__version__, \
'| torch', torch.__version__, '| SA scorer', os.path.exists(os.path.join(RDConfig.RDContribDir, 'SA_Score')))"
conda deactivate

if ! has_env gqd-dft; then
  conda create -y -n gqd-dft --override-channels -c conda-forge python=3.11
fi
conda activate gqd-dft
# [ctk] adds the CUDA headers CuPy needs to compile its GPU kernels (no system CUDA toolkit here)
pip install --quiet gpu4pyscf-cuda12x cutensor-cu12 "cupy-cuda12x[ctk]" pandas rdkit  # rdkit: dft_gpu.py imports Stage3a.sensing
echo "== gqd-dft env =="
python -c "import pyscf, gpu4pyscf, cupy; print('pyscf', pyscf.__version__, '| gpu4pyscf', gpu4pyscf.__version__, '| cupy', cupy.__version__)"
echo "setup done"
