#!/usr/bin/env bash
# Follow-on to run_pooled_chain.sh: the ink-maximum offset sweep
# (docs/preregistration/2026-09-22_ink_maximum_offset.md), four arms, strictly serial.
#
# It WAITS for the pooled chain, because building arms mid-chain is unsafe (~1 GB RAM free,
# 12 GB swap; see docs/preregistration/TEMPLATE.md pre-launch checklist). Order on success:
#   1. the pooled chain's registered analysis, FIRST and alone (docs/RESUME_AFTER_RESTART.md)
#   2. build + verify all four offset surfaces on an idle box
#   3. render + score each arm, reusing the flatten; hard-fail if reuse does not engage
#   4. the offset study's registered analysis
# If the pooled chain did not end with POOLED_CHAIN_DONE it does NOTHING: a failed arm there
# needs a human decision (re-run it first?) before this study takes the machine.
set -uo pipefail
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
REPO=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
PY=$REPO/.venv/bin/python
CHAIN_PID="${CHAIN_PID:?set CHAIN_PID to the pid of run_pooled_chain.sh}"
POOLED_LOG=$SO/pooled_chain.log
TEMPLATE=$SO/flat_study_zero          # carries the reuse-flatten patch and the pinned provenance
SRC_FLAT=$SO/radial_work_rad0/meshes/concat/w120-129_flat
ZERO_FLAT=$SO/flat_study/flat0/w120-129_flat
export RENDER_VENV=/home/jon/openclaw-workspace/Neo-VM/villa-spiral/spiral-fitting/.venv/bin/python
export INK_METRIC_SERIAL_FOLDS=1
export RENDER_REUSE_FLATTEN=1
unset FLATTEN_DETERMINISTIC           # no flatten runs; the registration says it is unnecessary

say() { echo "$*  $(date -Is)"; }

# ---- 0. wait for the pooled chain, by pid AND cmdline (a bare pid can be reused) ----------
say "OFFSET_SWEEP waiting for pooled chain pid $CHAIN_PID"
while [ -d /proc/$CHAIN_PID ] && tr '\0' ' ' < /proc/$CHAIN_PID/cmdline 2>/dev/null | grep -q run_pooled_chain; do
  sleep 60
done
if ! grep -q '^POOLED_CHAIN_DONE' "$POOLED_LOG"; then
  say "OFFSET_SWEEP_ABORTED pooled chain ended WITHOUT POOLED_CHAIN_DONE -- nothing built, nothing run"
  exit 3
fi
sleep 30   # let the last scorer release memory

# ---- 1. the pooled study's registered analysis, first and alone -------------------------
say "POOLED_ANALYSIS starting"
( cd "$REPO" && "$PY" scripts/analyse_pooled_fit_only_floor.py --json reports/pooled_fit_only_floor.json ) \
  && say "POOLED_ANALYSIS_DONE" || say "POOLED_ANALYSIS_FAILED rc=$? (continuing: the sweep does not depend on it)"

# ---- 2. build and verify all four surfaces before rendering any ---------------------------
avail_gb=$(awk '/MemAvailable/ {print int($2/1048576)}' /proc/meminfo)
[ "$avail_gb" -ge 8 ] || { say "OFFSET_SWEEP_ABORTED only ${avail_gb} GB available before build"; exit 4; }
IMG_EXPECTED=$(grep -o 'image_id=[^ ]*' "$TEMPLATE/RENDER_IMAGE" | cut -d= -f2)

declare -A DELTA=( [m2]=-2 [p1]=1 [p2]=2 [p3]=3 )
for N in m2 p1 p2 p3; do
  D=${DELTA[$N]}; B=$SO/flat_study/flat$D; W=$SO/offset_$N
  [ -e "$W" ] && { say "OFFSET_SWEEP_ABORTED $W already exists; refusing to overwrite"; exit 5; }
  "$PY" "$REPO/scripts/build_radial_displacement_arm.py" --single \
      --src "$SRC_FLAT" --out "$B" --delta "$D" --json "$B.json" \
    || { say "BUILD_FAILED offset_$N"; exit 1; }
  # positive controls the registration relies on: z untouched, same valid points as ZERO
  cmp -s "$B/w120-129_flat/z.tif" "$ZERO_FLAT/z.tif" || { say "BUILD_FAILED offset_$N: z.tif not byte-identical to flat0"; exit 1; }
  "$PY" - "$B.json" "$SO/flat_study/flat0.json" <<'EOF' || { say "BUILD_FAILED offset_$N: valid-point count or axis differs"; exit 1; }
import json, sys
A, Z = (json.load(open(p)) for p in sys.argv[1:3])
na, nz = (sum(r["n_valid"] for r in x["windings"].values()) for x in (A, Z))
print(f"valid points {na} vs flat0 {nz}; axis {A['axis']} vs flat0 {Z['axis']}")
sys.exit(0 if na == nz and A["axis"] == Z["axis"] else 1)
EOF
  # stage: copy the ZERO work dir, drop every render/score output, swap in the new surface
  cp -a "$TEMPLATE" "$W"
  rm -rf "$W/meshes/ink" "$W/ink_metric" "$W/meshes/ink_metric" "$W/meshes/concat/w120-129_flat"
  cp -a "$B/w120-129_flat" "$W/meshes/concat/w120-129_flat"
  say "BUILT offset_$N delta=$D"
done

# ---- 3. render + score, serial ------------------------------------------------------------
cd "$REPO/repro/spiral_render"
for N in m2 p1 p2 p3; do
  W=$SO/offset_$N; ARMLOG=$SO/offset_$N.render.log
  IMG_NOW=$(docker image inspect vc-render:local --format '{{.Id}}')
  [ "$IMG_NOW" = "$IMG_EXPECTED" ] || { say "GUARD_FAILED offset_$N: image $IMG_NOW != $IMG_EXPECTED"; exit 2; }
  say "=========== ARM offset_$N starting ==========="
  VENV="$RENDER_VENV" ./run_render.sh "$W" > "$ARMLOG" 2>&1 &
  RP=$!
  ok=
  for i in $(seq 1 60); do
    sleep 5
    grep -q "reuse-flatten\] using existing $W/" "$ARMLOG" && { ok=1; break; }
    grep -q "reuse-flatten\] RENDER_REUSE_FLATTEN=1 but" "$ARMLOG" && break
    kill -0 $RP 2>/dev/null || break
  done
  if [ -z "$ok" ]; then
    say "GUARD_FAILED offset_$N: reuse-flatten did not engage (would re-flatten); killing"
    pkill -TERM -P $RP; kill $RP 2>/dev/null; exit 2
  fi
  say "GUARD_OK offset_$N"
  wait $RP || { say "RENDER_FAILED offset_$N (see $ARMLOG)"; exit 1; }
  ./score_arms.sh "$W" >> "$ARMLOG" 2>&1 || { say "SCORE_FAILED offset_$N"; exit 1; }
  [ -f "$W/ink_metric/metrics.json" ] || { say "SCORE_FAILED offset_$N: no metrics.json"; exit 1; }
  say "ARM_DONE offset_$N"
done

# ---- 4. the offset study's registered analysis ---------------------------------------------
cd "$REPO"
"$PY" scripts/analyse_ink_maximum_offset.py --json reports/ink_maximum_offset.json \
  && say "OFFSET_SWEEP_DONE" || say "OFFSET_ANALYSIS_FAILED rc=$?"
