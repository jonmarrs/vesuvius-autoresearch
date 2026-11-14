#!/usr/bin/env bash
# Development segment only: score every depth and both sides against the labels and pick the best.
# Run once, after run_render.sh and run_ink.sh DEVELOPMENT D_MIN D_MAX.
#
# usage: run_sweep.sh            writes R/work/sweep.json
set -u
. "$(dirname "$0")/env.sh"
HERE=$(cd "$(dirname "$0")" && pwd)
S=$DEVELOPMENT; NAME=$(segment_name "$S")
"$PY" -I "$HERE/surface_control.py" sweep "$R/work/sweep.json" --depths "$D_MIN" "$D_MAX" \
  --segment "$S" "$(segment_mesh "$S")" "$R/work/maps/$NAME" "$R/work/render/${NAME}_66.zarr" \
  "$R/published/$S/ink-labels/2.403um-volume-20260319124803/20260918"
