#!/usr/bin/env bash
# Triplet C, seed 7, for the CALIBRATED consensus re-test:
# docs/preregistration/2026-09-14_consensus_retest_calibrated.md
#
# Identical to curbase_s1..s6 except the seed. Gives two unseen comparisons,
# A-vs-C and B-vs-C; the A-vs-B comparison is RETIRED (already seen at 0.876).
#
# Predicted r = 0.877 for both, band 0.85-0.91, refuted below 0.79.
# Ink gate is the 95% prediction interval from s1-s6: 2,398,918-3,639,084.
#
# Baseline on CURRENT villa spiral-fitting, full 30,000 steps.
# The pinned-tree corpus (villa-spiral 6847063f) is 35 files / +3385 lines behind
# and fits measurably worse: 0.13466 vs 0.16149 satisfied_area at a matched 200
# steps. These arms are the reference for any optimisation attempt on current code.
set -u
D=/home/jon/openclaw-workspace/Neo-VM/data/spiral_s1
export CUDA_VISIBLE_DEVICES=0
export WANDB_MODE=disabled
export FIT_SPIRAL_OUT_DIR=/home/jon/openclaw-workspace/Neo-VM/spiral_out
export FIT_SPIRAL_RUN_TAG=curbase_s7
export PYTHONPATH=/home/jon/openclaw-workspace/Neo-VM/villa-spiral-current/vesuvius/src
export FIT_SPIRAL_CONFIG_OVERRIDES='{
  "z_begin": 13056,
  "z_end": 18432,
  "input_use_fibers": false,
  "input_use_tracks": false,
  "input_use_pcl_drawn_control_points": false,
  "optimizer_random_seed": 7
}'
cd /home/jon/openclaw-workspace/Neo-VM/villa-spiral-current/spiral-fitting
exec /home/jon/openclaw-workspace/Neo-VM/villa-spiral-current/spiral-fitting/.venv/bin/python fit_spiral.py --dataset "$D"
