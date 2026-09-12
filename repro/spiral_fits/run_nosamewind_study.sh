#!/usr/bin/env bash
# Three arms for the same-winding ablation, registered in
# docs/preregistration/2026-09-06_same_winding_ablation.md.
# Compared against the SIX EXISTING full-input baselines; no new baseline fits.
# fit -> render -> score, strictly sequential, resumable, renders retried on OOM.
set -uo pipefail
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
REPO=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
exec "$REPO/repro/spiral_render/run_arm_sequence.sh" "$SO" 120 129 \
  nosame_s1 nosame_s2 nosame_s3
