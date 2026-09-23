#!/usr/bin/env bash
# docs/preregistration/2026-09-23_resampling_or_distortion.md -- two arms, serial, flatten reused.
# Each arm is flat_study_zero's work dir with its flat surface replaced by an in-plane re-sample of
# itself (t = 0.05 cell primary, t = 0.5 secondary), built by scripts/build_inplane_resampled_arm.py.
# Kills an arm unless the reuse-flatten line names ITS work dir (the fallback silently re-flattens).
set -uo pipefail
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
REPO=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
PY=$REPO/.venv/bin/python
SCRIPTS="${SCRIPTS:-$SO/rsd_scripts}"   # byte-identical copies, so the run does not depend on a merge
TEMPLATE=$SO/flat_study_zero
SRC_FLAT=$TEMPLATE/meshes/concat/w120-129_flat
export RENDER_VENV=/home/jon/openclaw-workspace/Neo-VM/villa-spiral/spiral-fitting/.venv/bin/python
export INK_METRIC_SERIAL_FOLDS=1
export RENDER_REUSE_FLATTEN=1
unset FLATTEN_DETERMINISTIC
say() { echo "$*  $(date -Is)"; }

pgrep -x vc_render_tifxy >/dev/null && { say "RSD_ABORTED a render is already running"; exit 3; }
for f in build_inplane_resampled_arm.py analyse_resampling_or_distortion.py measure_layout_rescoring.py; do
  [ -f "$SCRIPTS/$f" ] || { say "RSD_ABORTED missing $SCRIPTS/$f"; exit 4; }
done

for spec in rs_t005:0.05 rs_t05:0.5; do
  IFS=: read -r N T <<< "$spec"
  W=$SO/$N
  [ -e "$W" ] && { say "RSD_ABORTED $W exists"; exit 5; }
  cp -a "$TEMPLATE" "$W"
  rm -rf "$W/meshes/ink" "$W/ink_metric" "$W/meshes/ink_metric" "$W/meshes/concat/w120-129_flat"
  "$PY" "$SCRIPTS/build_inplane_resampled_arm.py" "$SRC_FLAT" "$W/meshes/concat/w120-129_flat" --t "$T" \
    || { say "BUILD_FAILED $N"; exit 1; }
  say "BUILT $N t=$T"
done

cd "$REPO/repro/spiral_render"
for N in rs_t005 rs_t05; do
  W=$SO/$N; LOG=$SO/$N.render.log
  say "=========== ARM $N starting ==========="
  VENV="$RENDER_VENV" ./run_render.sh "$W" > "$LOG" 2>&1 &
  RP=$!
  ok=
  for i in $(seq 1 60); do
    sleep 5
    grep -q "reuse-flatten\] using existing $W/" "$LOG" && { ok=1; break; }
    grep -q "reuse-flatten\] RENDER_REUSE_FLATTEN=1 but" "$LOG" && break
    kill -0 $RP 2>/dev/null || break
  done
  [ -n "$ok" ] || { say "GUARD_FAILED $N: reuse-flatten did not engage; killing"; pkill -TERM -P $RP; kill $RP 2>/dev/null; exit 2; }
  say "GUARD_OK $N"
  wait $RP || { say "RENDER_FAILED $N (see $LOG)"; exit 1; }
  ./score_arms.sh "$W" >> "$LOG" 2>&1 || { say "SCORE_FAILED $N"; exit 1; }
  [ -f "$W/ink_metric/metrics.json" ] || { say "SCORE_FAILED $N: no metrics.json"; exit 1; }
  say "ARM_DONE $N"
done

cd "$REPO"
"$PY" "$SCRIPTS/analyse_resampling_or_distortion.py" --json reports/resampling_or_distortion.json \
  && say "RSD_DONE" || say "RSD_ANALYSIS_FAILED rc=$?"
