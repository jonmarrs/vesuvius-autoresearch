#!/usr/bin/env bash
# ARM 3 of 3 for the anchor ablation, registered in
# docs/preregistration/2026-09-12_anchor_ablation.md.
#
# 10 z-coverage-matched anchors (1 @ z14268, 8 @ z15694, 1 @ z15976) against the
# 50 in-ROI anchors the curbase_s* baselines used. Seed 3, matching curbase_s3.
#
# Arm s1 is the anchor10cov_pilot fit: same dataset, same seed 1, so it IS arm 1
# and is reused rather than refitted. It carries no ink number (never rendered),
# so the reuse cannot be selected on the outcome.
#
# Every arm must pass scripts/measure_winding_identity.py against curbase_s1.
# A failing arm is EXCLUDED BY NAME via --excluded, never silently dropped.
set -u
D=/home/jon/openclaw-workspace/Neo-VM/data/spiral_s1_anchor10cov
export CUDA_VISIBLE_DEVICES=0
export WANDB_MODE=disabled
export FIT_SPIRAL_OUT_DIR=/home/jon/openclaw-workspace/Neo-VM/spiral_out
export FIT_SPIRAL_RUN_TAG=anchor10cov_s3
export PYTHONPATH=/home/jon/openclaw-workspace/Neo-VM/villa-spiral-current/vesuvius/src
export FIT_SPIRAL_CONFIG_OVERRIDES='{
  "z_begin": 13056,
  "z_end": 18432,
  "input_use_fibers": false,
  "input_use_tracks": false,
  "input_use_pcl_drawn_control_points": false,
  "optimizer_random_seed": 3
}'
cd /home/jon/openclaw-workspace/Neo-VM/villa-spiral-current/spiral-fitting
exec /home/jon/openclaw-workspace/Neo-VM/villa-spiral-current/spiral-fitting/.venv/bin/python fit_spiral.py --dataset "$D"
