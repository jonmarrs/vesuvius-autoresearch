#!/usr/bin/env bash
# PILOT, not an arm: one converged fit on the COVERAGE-MATCHED 10-anchor dataset
# (10 of the 50 in-ROI anchors, keeping all three populated z-planes), current
# villa, seed 1 -- matched to curbase_s1 in every other respect.
#
# It exists to settle ONE question before any study is registered: does the
# winding-number drift that blocks this ablation survive to convergence?
# Supersedes the anchor10_pilot run, which used the z-COLLAPSED hand-built set.
# That gate would have needed reinterpretation to govern these arms, and a gate
# whose failure needs reinterpretation is not a gate. Restarted after 9m.
# The blocking measurement (memory: winding-ablation-design-confound) was ~15vx
# at 200 STEPS on the PINNED tree, against a median winding spacing of ~12.6vx --
# too close to call. This is 30,000 steps on current code.
#
# NO RENDER. The drift is read off the fitted meshes, so this costs a fit (~3h)
# and not the ~6h a scored arm costs. If drift is small the study is runnable;
# if it is not, the study is dead and cost one fit instead of twelve.
set -u
D=/home/jon/openclaw-workspace/Neo-VM/data/spiral_s1_anchor10cov
export CUDA_VISIBLE_DEVICES=0
export WANDB_MODE=disabled
export FIT_SPIRAL_OUT_DIR=/home/jon/openclaw-workspace/Neo-VM/spiral_out
export FIT_SPIRAL_RUN_TAG=anchor10cov_pilot
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
