#!/usr/bin/env bash
# Triplet C for the calibrated consensus re-test.
# docs/preregistration/2026-09-14_consensus_retest_calibrated.md
#
# VILLA_REF is PINNED for the whole run. A mid-study fetch moved origin/main twice
# this week -- once from a submodule bump, once from a background monitor -- and
# each arm would otherwise render from whatever the ref happened to be.
set -uo pipefail
export VILLA=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa
export VILLA_REF=be09a8503
exec "/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/repro/spiral_render/run_arm_sequence.sh" \
  "/home/jon/openclaw-workspace/Neo-VM/spiral_out" 120 129 \
  curbase_s7 curbase_s8 curbase_s9
