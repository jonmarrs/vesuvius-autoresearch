#!/usr/bin/env bash
# P3 and the verdict: carry the ink of our windings into the frame of the published segment, compare it
# with the kill test's maps of that segment, and apply the registered decision table.
#
# usage: run_compare.sh ARM         writes R/work/{agreement,gate,verdict}_ARM.json
set -u
. "$(dirname "$0")/env.sh"
HERE=$(cd "$(dirname "$0")" && pwd)
ARM=${1:?usage: run_compare.sh recipe|reduced}
case "$ARM" in recipe|reduced) ;; *) echo "the comparison is for the registered arms only" >&2; exit 2 ;; esac
LIST=$R/work/windings_$ARM.txt
[ -f "$LIST" ] || { echo "run run_select.sh first" >&2; exit 2; }
mapfile -t WINDINGS < "$LIST"
"$PY" -I "$HERE/mesh_step_analysis.py" gate "$R/work/gate_$ARM.json" --dir "$R/work/gate_$ARM" \
  --fit-config "$ARM" --windings "${WINDINGS[@]}" || exit 1
FINAL=$R/work/final_select_$ARM.json
AGREEMENT=$R/work/agreement_$ARM.json
if [ "${#WINDINGS[@]}" -eq 0 ]; then
  # no fitted winding covers half of either published winding: P1 fails for both and there is no ink to carry
  FINAL=$R/work/select_$ARM.json
  echo '{"evaluable": false, "p3": false, "reason": "no winding was chosen"}' > "$AGREEMENT"
elif "$PY" -I -c 'import json, sys; sys.exit(0 if all(s["exit"] == 0 for s in json.load(open(sys.argv[1]))["steps"].values()) else 1)' "$R/work/gate_$ARM.json"; then
  OURS=()
  for w in "${WINDINGS[@]}"; do
    FLAG=--ours
    grep -q '"flipped": true' "$R/work/gate_$ARM/render_$w.json" && FLAG=--ours-flipped
    OURS+=("$FLAG" "$R/work/final_$ARM/$w.tifxyz" "$R/work/maps_$ARM/$w" "$R/work/render_$ARM/${w}_66.zarr")
  done
  "$PY" -I "$HERE/transfer_maps.py" "$AGREEMENT" \
    --published-mesh "$B/work/mesh/$SEGMENT.tifxyz" --published-maps "$B/work/maps_plain" \
    --published-render "$B/work/${SEGMENT}_66.zarr" \
    --letter-boxes "$RECIPE/inputs/${SEGMENT}_letter_boxes.json" "${OURS[@]}" || exit 1
fi
"$PY" -I "$HERE/mesh_step_analysis.py" verdict "$R/work/gate_$ARM.json" "$FINAL" "$AGREEMENT" \
  "$R/work/verdict_$ARM.json"
