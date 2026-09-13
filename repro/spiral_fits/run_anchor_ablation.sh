#!/usr/bin/env bash
# Anchor ablation: 10 z-coverage-matched anchors vs the 50 in-ROI anchors the
# curbase_s* baselines used. Registered in
# docs/preregistration/2026-09-12_anchor_ablation.md; gate passed, see
# reports/anchor_gate_verdict.md.
#
# Compared against the existing curbase_s1..s3. No new baselines.
#
# anchor10cov_pilot IS arm 1 (same dataset, seed 1) and is already fitted, so
# run_arm_sequence.sh skips its fit and goes straight to render+score. It keeps
# the pilot tag deliberately: renaming it would mean passing a file whose path
# says "pilot" under a tag that does not.
#
# Strictly sequential. A render peaks near 26GB on a 32GB box; nothing else of
# substance may run beside it.
set -uo pipefail
export VILLA=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa
exec "/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/repro/spiral_render/run_arm_sequence.sh" \
  "/home/jon/openclaw-workspace/Neo-VM/spiral_out" 120 129 \
  anchor10cov_pilot anchor10cov_s2 anchor10cov_s3
