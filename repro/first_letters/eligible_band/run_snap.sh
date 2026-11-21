#!/usr/bin/env bash
# The recipe's snap_meshes.py (defaults, level 0) on the windings listed in R/work/windings_ARM.txt, one name a
# line. First fetches the level-0 chunks of the surface prediction those windings can touch and checks that
# none is missing on disk (see ../pherc343/mesh_step/snap_chunks.py for why that matters).
# The windings are snapped SNAP_BATCH at a time (default 12) into the same folder. snap_meshes.py treats each winding
# on its own and holds every listed winding's samples at once (about 4 KB a node), so batches bound its memory on a
# denser grid without changing a byte: two of PHerc. 0826's windings snapped together and apart gave identical
# x, y, z and report, and the same as finding 125's snap.
# FL_SNAP_PASSES=N (1 to 5, default 1) snaps N times, each pass snapping the one before (finding 134): pass k < N
# writes snap_ARM.passk, its chunk manifest snap_chunks_ARM.passk.json (pass 1: snap_chunks_ARM.json), and the last
# pass writes snap_ARM. With 1, the commands and outputs are those of every snap before finding 134.
#
# usage: [FL_SNAP_PASSES=N] run_snap.sh ARM
set -u
. "$(dirname "$0")/env.sh"
ARM=${1:?usage: run_snap.sh ARM}
LIST=$R/work/windings_$ARM.txt
[ -s "$LIST" ] || { echo "$LIST is missing or empty" >&2; exit 2; }
OUT=$R/work/snap_$ARM
[ -e "$OUT" ] && { echo "$OUT exists: a step is run once per arm" >&2; exit 2; }
MESHES=$(fit_meshes "$ARM") || exit 2
MANIFEST=$R/work/snap_chunks_$ARM.json
PASSES=${FL_SNAP_PASSES:-1}
case "$PASSES" in
  1|2|3|4|5) ;;
  *) echo "FL_SNAP_PASSES is 1 to 5, not '$PASSES'" >&2; exit 2 ;;
esac
for k in $(seq 1 $(( PASSES - 1 ))); do
  [ -e "$OUT.pass$k" ] && { echo "$OUT.pass$k exists: a step is run once per arm" >&2; exit 2; }
done

snap_pass() {  # MESHES OUT MANIFEST: fetch and check the chunks the windings can touch, then snap them in batches
  local BATCHES batch rc=0
  "$PY" -I "$TOOLS/snap_chunks.py" "$1" "$LIST" "$SURF" "$BUCKET_SURF/$SURF_NAME" "$3" || return 1
  "$PY" -I "$TOOLS/snap_chunks.py" "$1" "$LIST" "$SURF" "$BUCKET_SURF/$SURF_NAME" "$3" --offline || return 1
  BATCHES=$(mktemp -d)
  split -l "${SNAP_BATCH:-12}" -d -a 3 "$LIST" "$BATCHES/batch_"
  for batch in "$BATCHES"/batch_*; do
    SURF_ZARR=$SURF /usr/bin/time -v "$PY" -I "$RECIPE/mesh/snap_meshes.py" "$1" "$SCROLL" "$2" \
      --windings "$batch" --procs "${PROCS:-3}" || { rc=1; break; }
  done
  rm -r "$BATCHES"
  return $rc
}

echo "SNAP_START $(date -Is) arm=$ARM passes=$PASSES windings=$(tr '\n' ' ' < "$LIST")"
t0=$(date +%s)
rc=0
IN=$MESHES
for k in $(seq 1 "$PASSES"); do
  if [ "$k" -eq "$PASSES" ]; then DEST=$OUT; else DEST=$OUT.pass$k; fi
  if [ "$k" -eq 1 ]; then M=$MANIFEST; else M=$R/work/snap_chunks_$ARM.pass$k.json; fi
  snap_pass "$IN" "$DEST" "$M" || { rc=1; break; }
  IN=$DEST
done
if [ $rc -eq 0 ]; then
  while read -r w; do [ -f "$OUT/$w/x.tif" ] || { echo "no snapped mesh for $w" >&2; rc=1; }; done < "$LIST"
fi
gate "$ARM" snap "$rc" "$(( $(date +%s) - t0 ))"
echo "SNAP_EXIT $rc $(date -Is)"
exit $rc
