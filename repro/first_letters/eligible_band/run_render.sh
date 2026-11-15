#!/usr/bin/env bash
# The 66-layer render of one final winding, CT streamed from the public open-data bucket into a cache under R.
# No flipped normals: the ink step reads both sides. The render stays under R.
#
# usage: run_render.sh ARM WINDING
set -u
. "$(dirname "$0")/env.sh"
ARM=${1:?usage: run_render.sh ARM WINDING}; W=${2:?usage: run_render.sh ARM WINDING}
SEG=$(readlink -f "$R/work/final_$ARM/$W.tifxyz")
OUT=$R/work/render_$ARM/${W}_66.zarr
[ -f "$SEG/x.tif" ] || { echo "no final winding for $W" >&2; exit 2; }
[ -e "$OUT" ] && { echo "$OUT exists: a step is run once per arm" >&2; exit 2; }
IMG_SHA=$(docker run --rm --entrypoint cat "$RENDER_IMG" /opt/vcsrc/SAMPLER_SHA)
[ "$IMG_SHA" = "$RENDER_SHA" ] || { echo "image sampler sha $IMG_SHA != $RENDER_SHA" >&2; exit 2; }
mkdir -p "$B/vchome" "$R/work/ctcache" "$R/work/render_$ARM"
THREADS=${THREADS:-2}
echo "RENDER_START $(date -Is) arm=$ARM winding=$W"
t0=$(date +%s)
/usr/bin/time -v docker run --rm --name "fl-render-$SCROLL-$ARM-$W" --user "$(id -u):$(id -g)" \
  --memory "${MEM_CAP:-8g}" --cpus "$THREADS" \
  -e HOME="$B/vchome" -e QT_QPA_PLATFORM=offscreen -e OMP_NUM_THREADS="$THREADS" \
  -v "$B:$B" -v "$R:$R" --entrypoint vc_render_tifxyz "$RENDER_IMG" \
  --volume "$R/work/ctcache" --remote-url "$CT_URL" --group-idx 0 --scale 1 \
  --segmentation "$SEG" --num-slices 66 --slice-step 1 \
  --cache-gb "${CACHE_GB:-3}" --zarr-output "$OUT"
rc=$?
if [ $rc -eq 0 ] && [ ! -d "$OUT/2" ]; then echo "no level 2 in $OUT" >&2; rc=1; fi
gate "$ARM" "render_$W" "$rc" "$(( $(date +%s) - t0 ))"
echo "RENDER_EXIT $rc $(date -Is)"
exit $rc
