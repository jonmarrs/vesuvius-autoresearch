#!/usr/bin/env bash
# 200-step smoke on CURRENT villa spiral-fitting, to see whether our data and
# environment still run it after 10 commits / +3385 lines since our pinned tree.
set -u
D=/home/jon/openclaw-workspace/Neo-VM/data/spiral_s1
export CUDA_VISIBLE_DEVICES=0
export WANDB_MODE=disabled
export FIT_SPIRAL_OUT_DIR=/home/jon/openclaw-workspace/Neo-VM/spiral_out
export FIT_SPIRAL_RUN_TAG=smoke_current
export PYTHONPATH=/home/jon/openclaw-workspace/Neo-VM/villa-spiral-current/vesuvius/src
export FIT_SPIRAL_CONFIG_OVERRIDES='{
  "z_begin": 13056,
  "z_end": 18432,
  "input_use_fibers": false,
  "input_use_tracks": false,
  "input_use_pcl_drawn_control_points": false,
  "optimizer_random_seed": 1,
  "optimizer_num_training_steps": 200
}'
cd /home/jon/openclaw-workspace/Neo-VM/villa-spiral-current/spiral-fitting
exec /home/jon/openclaw-workspace/Neo-VM/villa-spiral-current/spiral-fitting/.venv/bin/python fit_spiral.py --dataset "$D"
