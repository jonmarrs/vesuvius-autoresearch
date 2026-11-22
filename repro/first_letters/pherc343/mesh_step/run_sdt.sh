#!/usr/bin/env bash
# Step 1 of the recipe's mesh step: villa make_surf_sdt.py on the m7 surface prediction at level 1
# (threshold 128), over z 9500-11000 +/- 64, masked by the CT occupancy at level 4 dilated by 1.
# CPU only. Resumable: a second call continues the same output. The distance field is shared by every
# fit arm, so its gate record is written for the arm named on the command line (default recipe).
#
# usage: run_sdt.sh [ARM]      (WORKERS=3 by default; each worker holds one block of the band)
set -u
. "$(dirname "$0")/env.sh"
ARM=${1:-recipe}
WORKERS=${WORKERS:-3}
mkdir -p "$(dirname "$SDT")"
cd "$SPIRAL" || exit 2
RESUME=()
[ -e "$SDT" ] && RESUME=(--resume)   # villa refuses --resume on a store that does not exist yet
echo "SDT_START $(date -Is) workers=$WORKERS ${RESUME[*]}"
t0=$(date +%s)
/usr/bin/time -v "$PY" make_surf_sdt.py \
  --surf "$SURF" --group 1 --out "$SDT" --threshold 128 \
  --working-voxel-um 8.64 --z-range "9436:11064" \
  --ct "$CT" --ct-group 4 --ct-dilate 1 \
  --codec none --workers "$WORKERS" --edt-threads 1 "${RESUME[@]}"
rc=$?
gate "$ARM" distance_field "$rc" "$(( $(date +%s) - t0 ))"
echo "SDT_EXIT $rc $(date -Is)"
exit $rc
