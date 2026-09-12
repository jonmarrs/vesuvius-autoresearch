#!/usr/bin/env bash
# Three ablated arms on CURRENT villa, registered in
# docs/preregistration/2026-09-11_decoupling_on_current_code.md.
# Compared against the existing curbase_s1..s3; no new baselines.
set -uo pipefail
export VILLA=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa
exec "/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/repro/spiral_render/run_arm_sequence.sh" "/home/jon/openclaw-workspace/Neo-VM/spiral_out" 120 129 \
  nosamecur_s1 nosamecur_s2 nosamecur_s3
