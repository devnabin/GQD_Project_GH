<!-- Created date: 2026-11-12 (America/Chicago) -->

# Running on the college GPU server

The server is a shared Ubuntu machine: 16 cores / 32 threads, 2× A100 80 GB, no job scheduler. Other people use it, so jobs run at low priority (`nice`) on a limited number of cores. DFT uses GPU 0 only.

- **xTB evolution runs** (`Stage3/evolve.py`) use the CPU. The server CPU is shared and slower per core than the Mac, but runs there leave the Mac free.
- **DFT checks** use the GPU (GPU4PySCF), with the same method as Stage 3a (ωB97X-V/def2-SVP).

## Setup (once)

From the Mac (the SSH alias for the server is set in `~/.ssh/config`; key login, no password):

```bash
# copy the project, without the Python venv, secrets and large unused files
rsync -az --exclude .venv --exclude '.env' --exclude '.env.*' --exclude 'env' --exclude 'env-*' \
  --exclude snapshots --exclude filtered.csv --exclude __pycache__ --exclude .langgraph_api \
  ./ SERVER:~/Agentic_GQD/
ssh SERVER 'cd ~/Agentic_GQD && nohup bash server/setup_envs.sh > server/setup.log 2>&1 &'
```

`setup_envs.sh` creates two conda environments in `~/.conda/envs`:

- `gqd`: xTB, RDKit, the gap predictor and LangChain;
- `gqd-dft`: GPU4PySCF.

The rsync above never copies `studio/.env`. Random runs and DFT don't need the Azure key. For LLM runs, copy only the Azure lines by hand, readable only by the owner (done 2026-11-12):

```bash
grep -E '^AZURE_OPENAI_' studio/.env | ssh SERVER 'umask 077; cat > ~/Agentic_GQD/studio/.env'
```

## Measured on the server (2026-11-12)

| Test | Mac | Server |
|---|---|---|
| xTB sensing score, `gqd_18941` (NO₂ + CO) | ~65 s, score 0.322 | 394 s (shared CPU, `nice`), score 0.322 |
| DFT ωB97X-V/def2-SVP, benzene | 61 s (PySCF, 1 core) | 4.5 s (A100), same energy −232.014171 Ha |
| DFT, 30-ring GQD (134 atoms, closed-shell) | hours (estimate, not run) | 99 s |
| DFT, same GQD + NO₂ (137 atoms, open-shell) | hours (estimate, not run) | 366 s |

So: run xTB loops on the Mac, and DFT (and later ML training) on the server GPU.

## Running

```bash
ssh SERVER
cd ~/Agentic_GQD && conda activate gqd
nohup nice -n 10 python Stage3/evolve.py --run random_s1 --mutator random --seed 1 --parallel 2 > Stage3/results/random_s1.log 2>&1 &
```

`--parallel 2` with 6 single-thread jobs per child uses about 12 threads.

Results come back to the Mac with:

```bash
rsync -az SERVER:~/Agentic_GQD/Stage3/results/ Stage3/results/
```
