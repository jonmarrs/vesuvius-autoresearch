#!/usr/bin/env bash
# Six arms for the patch-bootstrap study, registered in
# docs/preregistration/2026-09-03_patch_bootstrap.md.
# fit -> render -> score, strictly sequential, resumable, renders retried on OOM.
set -uo pipefail
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
REPO=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
exec "$REPO/repro/spiral_render/run_arm_sequence.sh" "$SO" 120 129 \
  boot090s1 boot090s2 boot090s3 rand090s1 rand090s2 rand090s3
