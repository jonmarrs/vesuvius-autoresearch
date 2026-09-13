#!/usr/bin/env bash
# Second independent baseline triplet for the consensus forward prediction,
# docs/preregistration/2026-09-13_consensus_forward_prediction.md.
#
# Fit, render and score s4/s5/s6 end to end, strictly sequential: a render peaks
# near 26GB on a 32GB box and one render in six is OOM-killed here, so the retry
# wrapper matters.
set -uo pipefail
export VILLA=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa
exec "/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/repro/spiral_render/run_arm_sequence.sh" \
  "/home/jon/openclaw-workspace/Neo-VM/spiral_out" 120 129 \
  curbase_s4 curbase_s5 curbase_s6
