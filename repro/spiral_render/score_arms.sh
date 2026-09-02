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
# The gate only helps if the work dir HAS it. setup_workdir.sh extracts stock villa,
# so two arms were scored with INK_METRIC_SERIAL_FOLDS=1 set and nothing reading it:
# three folds ran concurrently, memory hit 30.6GB, and nnU-Net's export workers were
# OOM-killed ("Segmentation export worker died"). setup_workdir.sh now applies the
# patch and verifies it. --procs is left at the scorer's own default of 8, which is
# what the two published arms used and which fits in 18.8GB once folds are serial.
#
# Usage: score_arms.sh <arm_dir> [arm_dir...]
#   each arm_dir holds meshes/ink/ (render output) and spiral-fitting/
set -uo pipefail
FAILED=0
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
  # Capture on its OWN line. Written inline as rc=$? after a $(basename ...) the
  # command substitution runs first and clobbers $?, which reported rc=0 over a
  # scoring run that had just lost two of three folds.
  rc=$?
  echo "[exit] $(basename "$ARM") scoring rc=$rc"
  [ "$rc" -eq 0 ] && [ -f "$ARM/ink_metric/metrics.json" ] \
    || { echo "[fail] $(basename "$ARM"): no metrics.json, scoring did NOT succeed"; FAILED=1; }
  kill $MEMPID 2>/dev/null
done
echo "=================== ALL DONE $(date -Is) rc=$FAILED ==================="
exit "$FAILED"
