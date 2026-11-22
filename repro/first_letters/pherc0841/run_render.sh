#!/usr/bin/env bash
# The 66-layer render of one published PHerc. 0841 segment on the 9.366 um scan, CT streamed from the public
# open-data bucket: the same binary, arguments and container as the PHerc. 343 renders. No normals are
# flipped; which side reads is settled on the development segment by run_sweep.sh.
#
# usage: run_render.sh SEGMENT
set -u
. "$(dirname "$0")/env.sh"
S=${1:?usage: run_render.sh SEGMENT}
SEG=$(segment_mesh "$S"); NAME=$(segment_name "$S")
OUT=$R/work/render/${NAME}_66.zarr
[ -f "$SEG/x.tif" ] || { echo "no mesh at $SEG" >&2; exit 2; }
[ -e "$OUT" ] && { echo "$OUT exists: a step is run once" >&2; exit 2; }
IMG_SHA=$(docker run --rm --entrypoint cat "$RENDER_IMG" /opt/vcsrc/SAMPLER_SHA)
[ "$IMG_SHA" = "$RENDER_SHA" ] || { echo "image sampler sha $IMG_SHA != $RENDER_SHA" >&2; exit 2; }
mkdir -p "$B/vchome" "$R/work/ctcache" "$R/work/render"
THREADS=${THREADS:-2}
echo "RENDER_START $(date -Is) segment=$S"
t0=$(date +%s)
/usr/bin/time -v docker run --rm --name "fl0841-render-$NAME" --user "$(id -u):$(id -g)" \
  --memory "${MEM_CAP:-8g}" --cpus "$THREADS" \
  -e HOME="$B/vchome" -e QT_QPA_PLATFORM=offscreen -e OMP_NUM_THREADS="$THREADS" \
  -v "$B:$B" -v "$R:$R" --entrypoint vc_render_tifxyz "$RENDER_IMG" \
  --volume "$R/work/ctcache" --remote-url "$CT_URL" --group-idx 0 --scale 1 \
  --segmentation "$SEG" --num-slices 66 --slice-step 1 \
  --cache-gb "${CACHE_GB:-3}" --zarr-output "$OUT"
rc=$?
if [ $rc -eq 0 ] && [ ! -d "$OUT/2" ]; then echo "no level 2 in $OUT" >&2; rc=1; fi
gate "render_$NAME" "$rc" "$(( $(date +%s) - t0 ))"
echo "RENDER_EXIT $rc $(date -Is)"
exit $rc
