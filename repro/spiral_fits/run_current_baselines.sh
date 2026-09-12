#!/usr/bin/env bash
# Three baselines on CURRENT villa (submodule d8c5f488a), fit AND render/score,
# establishing the reference for optimisation attempts. villa's autoresearch.md:
# "Your very first run should always establish the baseline."
#
# VILLA points at the SUBMODULE, not villa-spiral: setup_workdir.sh archives
# $VILLA's origin/main, and the submodule is current while villa-spiral stays
# pinned at 6847063f for the existing 24-fit corpus.
set -uo pipefail
export VILLA=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa
exec "/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/repro/spiral_render/run_arm_sequence.sh" "/home/jon/openclaw-workspace/Neo-VM/spiral_out" 120 129 \
  curbase_s1 curbase_s2 curbase_s3
