#!/usr/bin/env bash
# Re-render curbase_s1's EXISTING meshes with the CURRENT villa code, to settle
# whether the 2026-09-11 render-code split biases ink.
# docs/preregistration/2026-09-14_render_code_rerender_test.md
#
# Same fit, same seed, same meshes. Only the render and scoring code differ.
# Original curbase_s1 total_fg_pixels = 2,904,520. Inert if within +/-2%.
# Writes to a NEW tag; outer_curbase_s1 is not touched.
set -uo pipefail
export VILLA=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa
exec "/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/repro/spiral_render/run_with_retry.sh" 3 "/home/jon/openclaw-workspace/Neo-VM/spiral_out" 120 129 \
  curbase_s1rr=/home/jon/openclaw-workspace/Neo-VM/spiral_out/2026-09-07_s1_slice-13056-18432_38442-patch_curbase_s1/meshes/fitted_curbase_s1
