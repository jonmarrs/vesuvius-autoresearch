#!/usr/bin/env bash
# docs/preregistration/2026-09-22_scorer_translation.md -- ten scoring-only arms of rad0's strip,
# offset on the canvas, queued behind the flatten-transmission study so nothing overlaps a render.
# Scores the way score_arms.sh does (scorer venv, serial folds, from the arm's spiral-fitting),
# without its .jpg-only check: these arms are lossless PNG on purpose.
set -uo pipefail
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
REPO=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
PY=$REPO/.venv/bin/python
SCORER=/home/jon/openclaw-workspace/Neo-VM/data/ink_scorer_venv/bin/python
export INK_METRIC_SERIAL_FOLDS=1
WAIT_PID="${WAIT_PID:?set WAIT_PID to the pid of run_flatten_transmission_after_cache_check.sh}"
say() { echo "$*  $(date -Is)"; }

say "SCORER_TRANSLATION waiting for transmission pid $WAIT_PID"
while [ -d /proc/$WAIT_PID ] && tr '\0' ' ' < /proc/$WAIT_PID/cmdline 2>/dev/null | grep -q run_flatten_transmission; do
  sleep 60
done
grep -q '^TRANSMISSION_DONE' "$SO/flatten_transmission.log" || {
  say "SCORER_TRANSLATION_ABORTED transmission did not end with TRANSMISSION_DONE -- the box may be needed"; exit 3; }
sleep 30

ARMS="stx_d0a:0:0 stx_d0b:0:0 stx_x1:1:0 stx_x2:2:0 stx_x8:8:0 stx_x64:64:0 stx_x512:512:0 stx_y1:0:1 stx_y8:0:8 stx_y64:0:64"
for spec in $ARMS; do
  IFS=: read -r N DX DY <<< "$spec"
  "$PY" "$REPO/scripts/build_shifted_strip_arm.py" "$SO/radial_work_rad0" "$SO/$N" --dx "$DX" --dy "$DY" \
    || { say "BUILD_FAILED $N"; exit 1; }
done
say "BUILT all ten"

for spec in $ARMS; do
  IFS=: read -r N DX DY <<< "$spec"
  ARM=$SO/$N
  say "=========== SCORE $N (dx=$DX dy=$DY) ==========="
  ( cd "$ARM/spiral-fitting" && "$SCORER" -u get_ink_metrics.py "$ARM/meshes/ink" --output "$ARM/ink_metric" ) \
    > "$SO/$N.score.log" 2>&1
  rc=$?
  [ "$rc" -eq 0 ] && [ -f "$ARM/ink_metric/metrics.json" ] || { say "SCORE_FAILED $N rc=$rc"; exit 1; }
  say "ARM_DONE $N"
done

cd "$REPO"
"$PY" scripts/analyse_scorer_translation.py --json reports/scorer_translation.json \
  && say "SCORER_TRANSLATION_DONE" || say "SCORER_TRANSLATION_ANALYSIS_FAILED rc=$?"
