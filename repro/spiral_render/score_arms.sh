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
HERE="$(cd "$(dirname "$0")" && pwd)"
FAILED=0
VENV="${SCORE_VENV:-${VENV:-/home/jon/openclaw-workspace/Neo-VM/data/ink_scorer_venv/bin/python}}"
[[ "$VENV" = /* ]] || VENV="$PWD/$VENV"
export INK_METRIC_SERIAL_FOLDS="${INK_METRIC_SERIAL_FOLDS:-1}"
[ "$#" -gt 0 ] || { echo "usage: score_arms.sh <arm_dir> [arm_dir...]" >&2; exit 2; }
MEMPID=""
cleanup() {
  if [ -n "$MEMPID" ]; then
    kill "$MEMPID" 2>/dev/null || true
    wait "$MEMPID" 2>/dev/null || true
    MEMPID=""
  fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

for ARM in "$@"; do
  ARM="$(cd "$ARM" && pwd)" || { echo "[fail] no such arm directory" >&2; FAILED=1; continue; }
  echo "=================== SCORE $(basename "$ARM") $(date -Is) ==================="
  ls "$ARM/meshes/ink"/*.jpg >/dev/null 2>&1 || { echo "[fail] no ink strips in $ARM"; FAILED=1; continue; }
  [ -d "$ARM/spiral-fitting" ] && [ -x "$VENV" ] \
    || { echo "[fail] missing spiral-fitting directory or scorer interpreter: $VENV"; FAILED=1; continue; }
  rm -rf "$ARM/ink_metric" "$ARM/meshes/ink_metric" \
    || { echo "[fail] could not clear old metrics for $ARM"; FAILED=1; continue; }
  # an OOM here is silent in the fold logs, so trace memory alongside
  ( SLEEP_PID=""
    trap '[ -z "$SLEEP_PID" ] || kill "$SLEEP_PID" 2>/dev/null; exit 0' TERM INT
    while true; do
      free -m | awk '/^Mem:/{printf "[mem] used=%dMB avail=%dMB\n",$3,$7}'
      sleep 30 & SLEEP_PID=$!
      wait "$SLEEP_PID"
    done ) & MEMPID=$!
  ( cd "$ARM/spiral-fitting" && \
    "$VENV" -u get_ink_metrics.py "$ARM/meshes/ink" --output "$ARM/ink_metric" )
  # Capture on its OWN line. Written inline as rc=$? after a $(basename ...) the
  # command substitution runs first and clobbers $?, which reported rc=0 over a
  # scoring run that had just lost two of three folds.
  rc=$?
  echo "[exit] $(basename "$ARM") scoring rc=$rc"
  [ "$rc" -eq 0 ] && python3 "$HERE/artifacts.py" metrics "$ARM/ink_metric/metrics.json" \
    || { echo "[fail] $(basename "$ARM"): scoring did NOT succeed";
         rm -f "$ARM/ink_metric/metrics.json"; FAILED=1; }
  cleanup
done
echo "=================== ALL DONE $(date -Is) rc=$FAILED ==================="
exit "$FAILED"
