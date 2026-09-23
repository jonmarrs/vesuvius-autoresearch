#!/usr/bin/env bash
# docs/preregistration/2026-09-22_does_the_flatten_transmit_a_mesh_offset.md -- two flatten-only
# arms, deterministic, render stubbed, queued behind the --cache-gb check so nothing overlaps a render.
# Stages flatten_rin / flatten_rout from flatten_det_a (same tree, stub render bin) with the displaced
# meshes of radial_work_in / radial_work_out, verifies the lineage by bytes, and kills an arm whose
# determinism shim does not activate. Then runs the registered analysis.
set -uo pipefail
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
REPO=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
SHIM=$REPO/repro/spiral_render/determinism_shim
RENDER_VENV=/home/jon/openclaw-workspace/Neo-VM/villa-spiral/spiral-fitting/.venv/bin/python
say() { echo "$*  $(date -Is)"; }

# NO_WAIT=1 starts at once, for when the job ahead was stopped by the operator (it is logged, never
# silent). Otherwise wait for the cache check and require it to have finished cleanly.
if [ "${NO_WAIT:-}" = "1" ]; then
  pgrep -x vc_render_tifxy >/dev/null && { say "TRANSMISSION_ABORTED NO_WAIT but a render is running"; exit 3; }
  say "TRANSMISSION starting WITHOUT waiting (NO_WAIT=1, operator decision)"
else
  WAIT_PID="${WAIT_PID:?set WAIT_PID to the pid of run_cache_gb_check_after_sweep.sh, or NO_WAIT=1}"
  say "TRANSMISSION waiting for cache check pid $WAIT_PID"
  while [ -d /proc/$WAIT_PID ] && tr '\0' ' ' < /proc/$WAIT_PID/cmdline 2>/dev/null | grep -q run_cache_gb_check; do
    sleep 60
  done
  grep -q '^CACHE_CHECK_DONE' "$SO/cache_gb_check.log" || {
    say "TRANSMISSION_ABORTED cache check did not end with CACHE_CHECK_DONE -- the box may be needed"; exit 3; }
  sleep 30
fi

for pair in "rin radial_work_in" "rout radial_work_out"; do
  set -- $pair; A=$1; SRC=$SO/$2; W=$SO/flatten_$A
  [ -e "$W" ] && { say "TRANSMISSION_ABORTED $W exists"; exit 5; }
  cp -a "$SO/flatten_det_a" "$W"
  rm -rf "$W/meshes/concat" "$W/meshes/ink" "$W"/meshes/w1*_spliced_* "$W/FLATTEN_MODE"
  cp -a "$SRC"/meshes/w1*_spliced_* "$W/meshes/"
  for m in "$SRC"/meshes/w1*_spliced_*; do
    n=$(basename "$m")
    cmp -s "$W/meshes/$n/z.tif" "$SO/flatten_det_a/meshes/$n/z.tif" \
      || { say "STAGE_FAILED $A $n z.tif differs from det_a"; exit 1; }
    cmp -s "$W/meshes/$n/x.tif" "$SO/flatten_det_a/meshes/$n/x.tif" \
      && { say "STAGE_FAILED $A $n x.tif is NOT displaced"; exit 1; }
  done
  say "STAGED flatten_$A from $2"
done

cd "$REPO/repro/spiral_render"
for A in rin rout; do
  W=$SO/flatten_$A; LOG=$SO/flatten_$A.log
  say "=========== FLATTEN $A starting ==========="
  FLATTEN_DETERMINISTIC=1 PYTHONPATH="$SHIM:$W/vesuvius/src" \
    "$RENDER_VENV" -u "$W/spiral-fitting/render_ink.py" "$W/meshes" \
      --volume "$W/inkcache" --vc-render-bin "$W/bin/vc_render_tifxyz" \
      --tifxyz-trim-bin "$W/bin/vc_tifxyz_trim" \
      --lasagna-dir "$W/lasagna" --lasagna-device cuda --num-processes 1 > "$LOG" 2>&1 &
  RP=$!
  ok=
  for i in $(seq 1 60); do
    sleep 5
    grep -q "determinism-shim\] torch.use_deterministic" "$LOG" && { ok=1; break; }
    kill -0 $RP 2>/dev/null || break
  done
  [ -n "$ok" ] || { say "GUARD_FAILED $A: determinism shim never activated"; pkill -TERM -P $RP; kill $RP 2>/dev/null; exit 2; }
  wait $RP; RC=$?   # the stubbed render makes render_ink exit nonzero by design
  [ -f "$W/meshes/concat/w120-129_flat/x.tif" ] || { say "FLATTEN_FAILED $A rc=$RC (see $LOG)"; exit 1; }
  echo deterministic > "$W/FLATTEN_MODE"
  say "FLATTEN_DONE $A rc=$RC"
done

cd "$REPO"
./.venv/bin/python scripts/analyse_flatten_transmission.py --json reports/flatten_transmission.json \
  && say "TRANSMISSION_DONE" || say "TRANSMISSION_ANALYSIS_FAILED rc=$?"
