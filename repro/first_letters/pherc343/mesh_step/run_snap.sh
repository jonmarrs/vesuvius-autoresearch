#!/usr/bin/env bash
# Step 3 of the recipe's mesh step: the recipe's snap_meshes.py (defaults, level 0) on the chosen windings.
# First fetches the level-0 chunks of the surface prediction those windings can touch and checks that none
# is missing on disk (see snap_chunks.py for why that matters).
#
# usage: run_snap.sh ARM            windings from R/work/windings_ARM.txt (written by run_select.sh)
#        run_snap.sh smoke W [W..]  the smoke arm names its windings itself; they are picked by name only
set -u
. "$(dirname "$0")/env.sh"
HERE=$(cd "$(dirname "$0")" && pwd)
ARM=${1:?usage: run_snap.sh ARM [WINDING ...]}; shift
LIST=$R/work/windings_$ARM.txt
if [ $# -gt 0 ]; then
  [ "$ARM" = smoke ] || { echo "only the smoke arm names windings by hand" >&2; exit 2; }
  printf '%s\n' "$@" > "$LIST"
fi
[ -s "$LIST" ] || { echo "$LIST is missing or empty" >&2; exit 2; }
OUT=$R/work/snap_$ARM
[ -e "$OUT" ] && { echo "$OUT exists: a step is run once per arm" >&2; exit 2; }
MESHES=$(fit_meshes "$ARM") || exit 2
MANIFEST=$R/work/snap_chunks_$ARM.json
echo "SNAP_START $(date -Is) arm=$ARM windings=$(tr '\n' ' ' < "$LIST")"
t0=$(date +%s)
rc=0
"$PY" -I "$HERE/snap_chunks.py" "$MESHES" "$LIST" "$SURF" "$BUCKET_SURF/$SURF_NAME" "$MANIFEST" || rc=1
if [ $rc -eq 0 ]; then
  "$PY" -I "$HERE/snap_chunks.py" "$MESHES" "$LIST" "$SURF" "$BUCKET_SURF/$SURF_NAME" "$MANIFEST" --offline || rc=1
fi
if [ $rc -eq 0 ]; then
  SURF_ZARR=$SURF /usr/bin/time -v "$PY" -I "$RECIPE/mesh/snap_meshes.py" "$MESHES" PHerc0343 "$OUT" \
    --windings "$LIST" --procs "${PROCS:-3}" || rc=1
fi
if [ $rc -eq 0 ]; then
  while read -r w; do [ -f "$OUT/$w/x.tif" ] || { echo "no snapped mesh for $w" >&2; rc=1; }; done < "$LIST"
fi
gate "$ARM" snap "$rc" "$(( $(date +%s) - t0 ))"
echo "SNAP_EXIT $rc $(date -Is)"
exit $rc
