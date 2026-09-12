#!/usr/bin/env bash
# Baseline on CURRENT villa spiral-fitting (submodule d8c5f488a), full 30,000 steps.
# The pinned-tree corpus (villa-spiral 6847063f) is 35 files / +3385 lines behind
# and fits measurably worse: 0.13466 vs 0.16149 satisfied_area at a matched 200
# steps. These arms are the reference for any optimisation attempt on current code.
set -u
D=/home/jon/openclaw-workspace/Neo-VM/data/spiral_s1
export CUDA_VISIBLE_DEVICES=0
export WANDB_MODE=disabled
export FIT_SPIRAL_OUT_DIR=/home/jon/openclaw-workspace/Neo-VM/spiral_out
export FIT_SPIRAL_RUN_TAG=curbase_s1
export PYTHONPATH=/home/jon/openclaw-workspace/Neo-VM/villa-spiral-current/vesuvius/src
export FIT_SPIRAL_CONFIG_OVERRIDES='{
  "z_begin": 13056,
  "z_end": 18432,
  "input_use_fibers": false,
  "input_use_tracks": false,
  "input_use_pcl_drawn_control_points": false,
  "optimizer_random_seed": 1
}'
cd /home/jon/openclaw-workspace/Neo-VM/villa-spiral-current/spiral-fitting
exec /home/jon/openclaw-workspace/Neo-VM/villa-spiral-current/spiral-fitting/.venv/bin/python fit_spiral.py --dataset "$D"
