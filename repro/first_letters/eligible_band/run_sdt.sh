#!/usr/bin/env bash
# villa make_surf_sdt.py on the m7 surface prediction at level 1 (threshold 128), over the band +/- 64 slices,
# masked by the CT occupancy at level 4 dilated by 1. CPU only. Resumable. Run on an idle host: the first fit
# after it packs a multi-GiB pool, and doing that beside another large process got a fit killed on PHerc. 343.
#
# usage: run_sdt.sh      (WORKERS=3 by default)
set -u
. "$(dirname "$0")/env.sh"
WORKERS=${WORKERS:-3}
mkdir -p "$(dirname "$SDT")"
cd "$SPIRAL" || exit 2
RESUME=()
[ -e "$SDT" ] && RESUME=(--resume)
echo "SDT_START $(date -Is) workers=$WORKERS ${RESUME[*]}"
t0=$(date +%s)
/usr/bin/time -v "$PY" make_surf_sdt.py \
  --surf "$SURF" --group 1 --out "$SDT" --threshold 128 \
  --working-voxel-um "$VOXEL_UM" --z-range "$((Z_BEGIN - 64)):$((Z_END + 64))" \
  --ct "$CT" --ct-group 4 --ct-dilate 1 \
  --codec none --workers "$WORKERS" --edt-threads 1 "${RESUME[@]}"
rc=$?
gate setup distance_field "$rc" "$(( $(date +%s) - t0 ))"
echo "SDT_EXIT $rc $(date -Is)"
exit $rc
