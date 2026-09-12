#!/usr/bin/env bash
# Five fits + five outer renders + five scorings for the n=6-per-arm second look.
# Registered in docs/preregistration/2026-09-02_gap_ink_second_look.md.
#
# Strictly sequential: two renders cannot share this box (26GB each on 32GB), and
# a fit competes with a render for both GPU and RAM.
#
# Waits on FILES the jobs actually produce, never on process names, and each
# render goes through run_with_retry.sh because one render in six is OOM-killed
# here. Resumable: anything already done is skipped.
set -uo pipefail
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
REPO=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch

for TAG in seed05 seed06 gap133s4 gap133s5 gap133s6; do
  echo "################ $TAG $(date -Is) ################"

  if [ -f "$SO/outer_$TAG/ink_metric/metrics.json" ]; then
    echo "[skip] $TAG already scored"; continue
  fi

  FITDIR=$(ls -d "$SO"/*patch_"$TAG" 2>/dev/null | head -1)
  MESHES=""
  [ -n "$FITDIR" ] && MESHES=$(ls -d "$FITDIR/meshes/fitted_$TAG" 2>/dev/null || true)

  if [ -z "$MESHES" ] || [ "$(find "$MESHES" -maxdepth 1 -name 'w12?_spliced_*' 2>/dev/null | wc -l)" -ne 10 ]; then
    echo "[fit] $TAG $(date -Is)"
    "$SO/fit_$TAG.sh" > "$SO/fit_$TAG.log" 2>&1
    echo "[fit] $TAG rc=$? $(date -Is)"
    # the meshes land AFTER the satisfaction json, so wait on the MESHES
    DEADLINE=$(( $(date +%s) + 3600 ))
    until [ "$(find "$SO"/*patch_"$TAG"/meshes/fitted_"$TAG" -maxdepth 1 -name 'w12?_spliced_*' 2>/dev/null | wc -l)" -eq 10 ]; do
      [ "$(date +%s)" -lt "$DEADLINE" ] || { echo "[fail] $TAG meshes never appeared"; break; }
      sleep 30
    done
    FITDIR=$(ls -d "$SO"/*patch_"$TAG" 2>/dev/null | head -1)
    MESHES="$FITDIR/meshes/fitted_$TAG"
  else
    echo "[skip] $TAG already fitted"
  fi

  n=$(find "$MESHES" -maxdepth 1 -name 'w12?_spliced_*' 2>/dev/null | wc -l)
  [ "$n" -eq 10 ] || { echo "[fail] $TAG has $n/10 outer meshes, skipping"; continue; }

  echo "[render+score] $TAG $(date -Is)"
  RETRY_WAIT_FIRST=0 "$REPO/repro/spiral_render/run_with_retry.sh" 3 "$SO" 120 129 "$TAG=$MESHES" \
    >> "$SO/second_look_$TAG.log" 2>&1
  echo "[render+score] $TAG rc=$? $(date -Is)"

  if [ -f "$SO/outer_$TAG/ink_metric/metrics.json" ]; then
    echo "[ok] $TAG scored"
  else
    echo "[fail] $TAG NOT scored after retries"
  fi
done
echo "################ SECOND LOOK ARMS DONE $(date -Is) ################"
