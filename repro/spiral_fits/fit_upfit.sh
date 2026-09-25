#!/usr/bin/env bash
# Upstream-fitter arm: docs/preregistration/2026-09-24_upstream_fitter.md.
#
# Identical to curbase_s1..s9 in dataset, z-ROI and overrides; the ONLY difference is
# the fitting tree: villa 75c79ac5f (after the 09-14 series and #1871 "Spiral
# simplification"), extracted to villa-spiral-upstream with its own venv.
# Usage: fit_upfit.sh <seed>   -> run tag upfit_s<seed>
set -u
SEED=${1:?seed}
TREE=/home/jon/openclaw-workspace/Neo-VM/villa-spiral-upstream
D=/home/jon/openclaw-workspace/Neo-VM/data/spiral_s1
grep -q '^75c79ac5f' "$TREE/VILLA_SHA" || { echo "FIT_TREE_WRONG: $(cat "$TREE/VILLA_SHA")"; exit 2; }
export CUDA_VISIBLE_DEVICES=0
export WANDB_MODE=disabled
export FIT_SPIRAL_OUT_DIR=/home/jon/openclaw-workspace/Neo-VM/spiral_out
export FIT_SPIRAL_RUN_TAG=upfit_s$SEED
export PYTHONPATH=$TREE/vesuvius/src
export FIT_SPIRAL_CONFIG_OVERRIDES='{
  "z_begin": 13056,
  "z_end": 18432,
  "input_use_fibers": false,
  "input_use_tracks": false,
  "input_use_pcl_drawn_control_points": false,
  "optimizer_random_seed": '"$SEED"'
}'
cd $TREE/spiral-fitting
exec $TREE/spiral-fitting/.venv/bin/python fit_spiral.py --dataset "$D"
