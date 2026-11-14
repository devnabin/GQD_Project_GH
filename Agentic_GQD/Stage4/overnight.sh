#!/bin/bash
# Created date: 2026-11-13 (America/Chicago)
# Overnight queue on the college server (all choices fixed in advance; see Stage4/PROGRESS.md).
#   GPU 0 : DFT of 4 linked + 4 fused closed-shell candidates, then a broken-symmetry check of all 8.
#   CPU   : xTB geometries of the 4 fused candidates; smoke test of the score-v2 loop; then 4 runs.
# Start:  nohup bash Stage4/overnight.sh > /dev/null 2>&1 < /dev/null & disown
# Log:    Stage4/overnight.log  (one line per step)

cd ~/Agentic_GQD || exit 1
source "$(conda info --base)/etc/profile.d/conda.sh" 2>/dev/null
LOG=Stage4/overnight.log
log() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

LINKED="gdy_row5 gy_hex7 gy_rhomb9 gdy_rhomb4"
FUSED_CAL="gqd_64256"
FUSED_CHILDREN="random_v2_s2:g02c012,llm_v2_s3:g01c013,random_s0:g01c009"
FUSED_NAMES="gqd_64256 random_v2_s2_g02c012 llm_v2_s3_g01c013 random_s0_g01c009"
LOOP="--generations 10 --children 10 --parallel 2 --workers 6 --score v2 --fod-max 2.9"

log "queue started"

# ---------------------------------------------------------------- GPU chain
(
  conda activate gqd 2>/dev/null
  python Stage4/prepare_linked.py Stage4/dft_linked $LINKED >> "$LOG" 2>&1
  conda activate gqd-dft 2>/dev/null
  log "GPU: DFT linked candidates start"
  CUDA_VISIBLE_DEVICES=0 python Stage3a/dft_gpu.py Stage4/dft_linked > Stage4/dft_linked.log 2>&1
  log "GPU: DFT linked candidates done (exit $?)"
  while [ ! -f Stage4/dft_fused/.geometries_done ]; do sleep 120; done
  log "GPU: DFT fused candidates start"
  CUDA_VISIBLE_DEVICES=0 python Stage3a/dft_gpu.py Stage4/dft_fused > Stage4/dft_fused.log 2>&1
  log "GPU: DFT fused candidates done (exit $?)"
  CUDA_VISIBLE_DEVICES=0 python Stage3a/bs_check.py Stage4/dft_linked $LINKED >> Stage4/bs_check.log 2>&1
  CUDA_VISIBLE_DEVICES=0 python Stage3a/bs_check.py Stage4/dft_fused $FUSED_NAMES >> Stage4/bs_check.log 2>&1
  log "GPU: broken-symmetry checks done"
) &

# ---------------------------------------------------------------- CPU chain 1: fused geometries
(
  conda activate gqd 2>/dev/null
  log "CPU: fused candidate geometries start"
  nice -n 10 python Stage3a/make_geometries.py Stage4/dft_fused --calibration "$FUSED_CAL" \
      --children "$FUSED_CHILDREN" --parallel 2 > Stage4/make_geometries.log 2>&1
  status=$?
  touch Stage4/dft_fused/.geometries_done
  log "CPU: fused candidate geometries done (exit $status)"
) &

# ---------------------------------------------------------------- CPU chain 2: score-v2 search
(
  conda activate gqd 2>/dev/null
  log "CPU: smoke test of the score-v2 loop"
  nice -n 10 python Stage3/evolve.py --run smoke_sv2 --mutator random --seed 9 --generations 1 --children 2 \
      --parallel 2 --workers 6 --score v2 --fod-max 2.9 --final-check 0 > Stage4/smoke_sv2.log 2>&1
  if [ $? -ne 0 ] || ! grep -q '"evaluated": true' Stage3/results/smoke_sv2/children.jsonl 2>/dev/null; then
    log "CPU: SMOKE TEST FAILED, evolution runs not started (see Stage4/smoke_sv2.log)"
    exit 1
  fi
  log "CPU: smoke test passed"
  for seed in 1 2; do
    log "CPU: runs llm_sv2_s$seed and random_sv2_s$seed start"
    nice -n 10 python Stage3/evolve.py --run llm_sv2_s$seed --mutator llm --seed $seed $LOOP \
        > Stage3/results/llm_sv2_s$seed.log 2>&1 &
    nice -n 10 python Stage3/evolve.py --run random_sv2_s$seed --mutator random --seed $seed $LOOP \
        > Stage3/results/random_sv2_s$seed.log 2>&1 &
    wait
    log "CPU: runs llm_sv2_s$seed and random_sv2_s$seed done"
  done
) &

wait
log "queue finished"
