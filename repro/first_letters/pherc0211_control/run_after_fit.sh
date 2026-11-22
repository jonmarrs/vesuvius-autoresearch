#!/usr/bin/env bash
# Finding 119, the registered steps after `run_fit.sh full`, one at a time, each run only if the one before exited 0:
#   run_quality.sh full                  the sheet-following score of every raw winding (described)
#   winner_sheet.py choose               the chosen raw winding and the snap list (R/work/windings_full.txt)
#   run_snap.sh full                     the recipe's snap of the listed windings (skipped if none was chosen)
#   winner_sheet.py verdict              the snapped chosen winding against the winner's nodes in the band
# Each step's exit and seconds go to R/work/gate_full/<step>.json (run_snap.sh writes its own).
#
# usage: FL_SCROLL=PHerc0211 FL_BAND=z7650 FL_Z_BEGIN=7650 FL_Z_END=9150 run_after_fit.sh WINNER_TIFXYZ
#
# winner_sheet.py runs on this repository's environment (PYW), not villa's (PY): the winner's tifxyz files are
# LZW-compressed and villa's environment has no imagecodecs to read them.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
BAND=$(cd "$HERE/../eligible_band" && pwd)
. "$BAND/env.sh"
PYW=${PYW:-$(cd "$HERE/../../.." && pwd)/.venv/bin/python}
WINNER=${1:?usage: run_after_fit.sh WINNER_TIFXYZ}
[ -f "$WINNER/x.tif" ] || { echo "no tifxyz surface at $WINNER" >&2; exit 2; }
MESHES=$(fit_meshes full) || exit 2

step() {  # NAME LOG COMMAND...: run, record the gate, stop the chain on failure
  local name=$1 log=$2 t0 rc
  shift 2
  t0=$(date +%s)
  echo "STEP_START $name $(date -Is)"
  "$@" > "$log" 2>&1
  rc=$?
  gate full "$name" "$rc" "$(( $(date +%s) - t0 ))"
  echo "STEP_EXIT $name $rc $(date -Is)"
  [ "$rc" -eq 0 ] || exit "$rc"
}

step quality "$R/logs/quality_full.log" bash "$BAND/run_quality.sh" full
step choose "$R/logs/winner_choose.log" "$PYW" -I "$HERE/winner_sheet.py" choose \
  "$R/work/winner_choose.json" "$WINNER" "$MESHES" "$R/work/windings_full.txt" --sdt "$SDT"
if [ -s "$R/work/windings_full.txt" ]; then
  echo "STEP_START snap $(date -Is)"
  bash "$BAND/run_snap.sh" full > "$R/logs/snap_full.log" 2>&1
  rc=$?
  echo "STEP_EXIT snap $rc $(date -Is)"
  [ "$rc" -eq 0 ] || exit "$rc"
else
  echo "no winding chosen: no snap"
fi
step verdict "$R/logs/winner_verdict.log" "$PYW" -I "$HERE/winner_sheet.py" verdict \
  "$R/work/winner_verdict.json" "$WINNER" "$R/work/winner_choose.json" "$R/work/snap_full"
cat "$R/logs/winner_verdict.log"
