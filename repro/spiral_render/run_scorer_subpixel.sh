#!/usr/bin/env bash
# docs/preregistration/2026-09-24_scorer_subpixel.md -- one scoring-only arm, no render.
set -uo pipefail
SO=/home/jon/openclaw-workspace/Neo-VM/spiral_out
REPO=/home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
PY=$REPO/.venv/bin/python
SCORER=/home/jon/openclaw-workspace/Neo-VM/data/ink_scorer_venv/bin/python
SCRIPTS="${SCRIPTS:-$SO/sp_scripts}"   # byte-identical copies: the run does not depend on a merge
export INK_METRIC_SERIAL_FOLDS=1
say() { echo "$*  $(date -Is)"; }

pgrep -x vc_render_tifxy >/dev/null && { say "SP_ABORTED a render is running"; exit 3; }
for f in build_subpixel_image_arm.py build_shifted_strip_arm.py analyse_scorer_subpixel.py \
         analyse_resampling_or_distortion.py measure_layout_rescoring.py; do
  [ -f "$SCRIPTS/$f" ] || { say "SP_ABORTED missing $SCRIPTS/$f"; exit 4; }
done
ARM=$SO/sp_half
[ -e "$ARM" ] && { say "SP_ABORTED $ARM exists"; exit 5; }

"$PY" "$SCRIPTS/build_subpixel_image_arm.py" "$SO/flat_study_zero" "$ARM" || { say "BUILD_FAILED"; exit 1; }
say "BUILT sp_half"
( cd "$ARM/spiral-fitting" && "$SCORER" -u get_ink_metrics.py "$ARM/meshes/ink" --output "$ARM/ink_metric" ) \
  > "$SO/sp_half.score.log" 2>&1
rc=$?
[ "$rc" -eq 0 ] && [ -f "$ARM/ink_metric/metrics.json" ] || { say "SCORE_FAILED rc=$rc"; exit 1; }
say "ARM_DONE sp_half"
cd "$REPO"
"$PY" "$SCRIPTS/analyse_scorer_subpixel.py" --json reports/scorer_subpixel.json \
  && say "SP_DONE" || say "SP_ANALYSIS_FAILED rc=$?"
