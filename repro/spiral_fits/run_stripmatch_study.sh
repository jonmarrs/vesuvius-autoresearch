#!/usr/bin/env bash
# Three arms for the STRIPMATCH follow-up, registered in
# docs/preregistration/2026-09-04_stripmatch_followup.md.
# Compared against the EXISTING boot090s1..s3 arms; no new BOOTSTRAP fits.
# fit -> render -> score, strictly sequential, resumable, renders retried on OOM.
set -uo pipefail
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
REPO=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
exec "$REPO/repro/spiral_render/run_arm_sequence.sh" "$SO" 120 129 \
  strip090s1 strip090s2 strip090s3
