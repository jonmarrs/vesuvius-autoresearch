#!/usr/bin/env bash
# docs/preregistration/2026-09-27_step2_across_surfaces.md -- the published image re-samples each
# surface's OWN saved flat with --slice-step 2 (== a post-#1146 build, verified to rounding). Only the
# step differs from the surface's existing detfit_* score. Serial.
set -uo pipefail
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
HERE="$(cd "$(dirname "$0")" && pwd)"
export RENDER_VENV=/home/jon/openclaw-workspace/Neo-VM/villa-spiral/spiral-fitting/.venv/bin/python
export INK_METRIC_SERIAL_FOLDS=1 RENDER_REUSE_FLATTEN=1
unset FLATTEN_DETERMINISTIC
say() { echo "$*  $(date -Is)"; }
for p in /proc/[0-9]*; do [ "$(cat "$p/comm" 2>/dev/null)" = vc_render_tifxy ] && { say "STEP2_ABORTED a render is running"; exit 3; }; done
for A in s4 s5 s6; do
  SRC=$SO/detfit_$A; W=$SO/step2_$A; LOG=$W.render.log
  [ -e "$W" ] && { say "STEP2_ABORTED $W exists"; exit 5; }
  cp -a "$SRC" "$W"
  # The copied per-slice TIFFs MUST go: the published binary skips when they exist (finding 65).
  rm -rf "$W/meshes/ink" "$W/ink_metric" "$W/meshes/ink_metric" "$W/meshes/concat/w120-129_flat/ink"
  patch -p1 -d "$W" --batch -i "$HERE/reuse_flatten.patch" >/dev/null || { say "PATCH_FAILED $A"; exit 1; }
  sed -i 's#--scale-segmentation 4 "\$@"#--scale-segmentation 4 --slice-step 2 "$@"#' "$W/bin/vc_render_tifxyz"
  grep -q -- '--slice-step 2' "$W/bin/vc_render_tifxyz" || { say "WRAPPER_EDIT_FAILED $A"; exit 1; }
  cmp -s <(cat "$SRC"/meshes/concat/w120-129_flat/[xyz].tif) <(cat "$W"/meshes/concat/w120-129_flat/[xyz].tif) \
    || { say "FLAT_DIFFERS $A"; exit 1; }
  say "=========== ARM step2_$A starting ==========="
  VENV="$RENDER_VENV" "$HERE/run_render.sh" "$W" > "$LOG" 2>&1 || { say "RENDER_FAILED $A"; exit 1; }
  grep -q "reuse-flatten\] using existing $W/" "$LOG" || { say "REUSE_NOT_ENGAGED $A"; exit 1; }
  grep -q "all slices exist, skipping" "$LOG" && { say "SKIPPED_SAMPLING $A"; exit 1; }
  "$HERE/score_arms.sh" "$W" >> "$LOG" 2>&1 || { say "SCORE_FAILED $A"; exit 1; }
  say "ARM_DONE step2_$A"
done
say "STEP2_CHAIN_DONE"
