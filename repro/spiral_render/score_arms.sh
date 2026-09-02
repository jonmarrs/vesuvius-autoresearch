#!/usr/bin/env bash
# Score one or more rendered arms with get_ink_metrics.py, one arm at a time.
#
# Why serially, and why the patch: three fold subprocesses run concurrently (the
# stock behaviour) each hold the whole strip's logits. On a ten-winding OUTER
# strip (352M px) that peaks past 30GB on a 32GB box and the OOM killer takes a
# fold out with rc=-9. INK_METRIC_SERIAL_FOLDS=1 (serial_folds.patch) runs one
# fold at a time and accumulates the ensemble in place instead of stacking it.
#
# The scorer is not bit-deterministic on GPU, with or without the patch: three
# runs over one fixed strip gave total_fg_pixels 249913 / 249905 / 249906, a
# spread of 0.0032%. The gate does not move the answer by more than that.
#
# Usage: score_arms.sh <arm_dir> [arm_dir...]
#   each arm_dir holds meshes/ink/ (render output) and spiral-fitting/
set -uo pipefail
VENV="${VENV:-/home/jon/openclaw-workspace/Neo-VM/data/ink_scorer_venv/bin/python}"
export INK_METRIC_SERIAL_FOLDS="${INK_METRIC_SERIAL_FOLDS:-1}"

for ARM in "$@"; do
  ARM="$(cd "$ARM" && pwd)"
  echo "=================== SCORE $(basename "$ARM") $(date -Is) ==================="
  ls "$ARM/meshes/ink"/*.jpg >/dev/null 2>&1 || { echo "[fail] no ink strips in $ARM"; continue; }
  rm -rf "$ARM/ink_metric" "$ARM/meshes/ink_metric"
  # an OOM here is silent in the fold logs, so trace memory alongside
  ( while true; do
      free -m | awk '/^Mem:/{printf "[mem] used=%dMB avail=%dMB\n",$3,$7}'
      sleep 30
    done ) & MEMPID=$!
  ( cd "$ARM/spiral-fitting" && \
    "$VENV" -u get_ink_metrics.py "$ARM/meshes/ink" --output "$ARM/ink_metric" )
  echo "[exit] $(basename "$ARM") scoring rc=$?"
  kill $MEMPID 2>/dev/null
done
echo "=================== ALL DONE $(date -Is) ==================="
