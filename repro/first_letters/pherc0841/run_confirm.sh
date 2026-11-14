#!/usr/bin/env bash
# Held-out segments at the one depth and side run_sweep.sh chose: the registered readings and the verdict.
# Run once, after run_render.sh and run_ink.sh on each held-out segment at the chosen depth.
#
# usage: run_confirm.sh          writes R/work/confirm.json
set -u
. "$(dirname "$0")/env.sh"
HERE=$(cd "$(dirname "$0")" && pwd)
ARGS=()
for S in $HELD_OUT; do
  NAME=$(segment_name "$S")
  ARGS+=(--segment "$S" "$(segment_mesh "$S")" "$R/work/maps/$NAME" "$R/work/render/${NAME}_66.zarr"
         "$R/published/$S/ink-labels/2.403um-volume-20260319124803/20260918")
done
"$PY" -I "$HERE/surface_control.py" confirm "$R/work/confirm.json" --choice "$R/work/sweep.json" \
  --gate "$R/work/gate" "${ARGS[@]}"
