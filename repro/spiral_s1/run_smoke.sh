#!/usr/bin/env bash
# Smoke run: does the fit start and take steps on this box, with this dataset?
# Not a result. 100 steps against 30000, purely to reach the training loop.
set -u
D=/home/jon/openclaw-workspace/Neo-VM/data/spiral_s1
export CUDA_VISIBLE_DEVICES=0
export WANDB_MODE=disabled
export FIT_SPIRAL_OUT_DIR=/home/jon/openclaw-workspace/Neo-VM/spiral_out
export FIT_SPIRAL_RUN_TAG=smoke01
export FIT_SPIRAL_CONFIG_OVERRIDES='{
  "z_begin": 13056,
  "z_end": 18432,
  "input_use_fibers": false,
  "input_use_tracks": false,
  "input_use_pcl_drawn_control_points": false,
  "optimizer_num_training_steps": 100
}'
cd /home/jon/openclaw-workspace/Neo-VM/villa-spiral/spiral-fitting
exec uv run python fit_spiral.py --dataset "$D"
