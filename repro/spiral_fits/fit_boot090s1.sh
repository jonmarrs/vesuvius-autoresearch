#!/usr/bin/env bash
# Converged baseline fit: the checkpoint the pre-registered injection study runs against.
# Identical to smoke.sh except optimizer_num_training_steps is left at its default 30,000.
set -u
D=/home/jon/openclaw-workspace/Neo-VM/data/spiral_s1_boot090
export CUDA_VISIBLE_DEVICES=0
export WANDB_MODE=disabled
export FIT_SPIRAL_OUT_DIR=/home/jon/openclaw-workspace/Neo-VM/spiral_out
export FIT_SPIRAL_RUN_TAG=boot090s1
export FIT_SPIRAL_CONFIG_OVERRIDES='{
  "z_begin": 13056,
  "z_end": 18432,
  "input_use_fibers": false,
  "input_use_tracks": false,
  "input_use_pcl_drawn_control_points": false,
  "optimizer_random_seed": 1
}'
cd /home/jon/openclaw-workspace/Neo-VM/villa-spiral/spiral-fitting
exec uv run python fit_spiral.py --dataset "$D"
