#!/usr/bin/env bash
# The numbered strips for the reader (blind_tiles.py), from every winding in R/work/windings_read.txt and the
# anchors of PHerc. 0841's development segment. The strips are this scroll's ink maps: they stay under R.
# The key goes to R/work/blind_key_ARM.json; the reader opens R/work/strips_ARM/sheet.html and not the key.
#
# usage: run_tiles.sh ARM D_LO D_HI
set -u
. "$(dirname "$0")/env.sh"
HERE=$(cd "$(dirname "$0")" && pwd)
ARM=${1:?usage: run_tiles.sh ARM D_LO D_HI}; LO=${2:?D_LO}; HI=${3:?D_HI}
A=${FL0841_DIR:-$FL_ROOT/pherc0841_control}
DEV=20260220213127-w00
SHORT=s${DEV%%-*}
ARGS=()
while read -r W; do
  ARGS+=(--target "$W" "$(readlink -f "$R/work/final_$ARM/$W.tifxyz")" "$R/work/maps_$ARM/$W"
         "$R/work/render_$ARM/${W}_66.zarr")
done < "$R/work/windings_read.txt"
MPLBACKEND=Agg "$PY" -I "$HERE/blind_tiles.py" "$R/work/strips_$ARM" "$R/work/blind_key_$ARM.json" \
  --depths "$LO" "$HI" "${ARGS[@]}" \
  --anchor "$DEV" "$A/published/$DEV/mesh/${DEV%%-*}-on-20250821151531-9.366um.tifxyz" \
  "$A/work/maps/$SHORT" "$A/work/render/${SHORT}_66.zarr" \
  "$A/published/$DEV/ink-labels/2.403um-volume-20260319124803/20260918"
