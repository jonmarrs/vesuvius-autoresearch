#!/usr/bin/env bash
# The render of one final winding, CT streamed from the public open-data bucket into a cache under R: 66 layers, or
# with RENDER_SLICES=N an even N from 18 to 66, the centred N of them (layers (66 - N) / 2 to (66 + N) / 2 - 1 of
# the 66-layer frame, byte for byte; render_frame.py), written to wNNN_N.zarr.
# No flipped normals by default: the ink step reads both sides. A third argument `flip` renders with
# --flip-normals, for a comparison that needs layer k on the same side as a reference surface's (finding 121
# decides it from the geometry, before any ink). The render stays under R.
#
# usage: run_render.sh ARM WINDING [flip]
set -u
. "$(dirname "$0")/env.sh"
ARM=${1:?usage: run_render.sh ARM WINDING [flip]}; W=${2:?usage: run_render.sh ARM WINDING [flip]}
SLICES=${RENDER_SLICES:-66}
case "$SLICES" in
  ''|*[!0-9]*) SLICES=0 ;;
esac
if [ "$SLICES" -lt 18 ] || [ "$SLICES" -gt 66 ] || [ $(( SLICES % 2 )) -ne 0 ]; then
  echo "RENDER_SLICES is an even number from 18 to 66 (it must hold Studio's layers 26 to 41), not '${RENDER_SLICES:-}'" >&2
  exit 2
fi
FLIP=(); FLIPPED=false
case "${3:-}" in
  "") ;;
  flip) FLIP=(--flip-normals); FLIPPED=true ;;
  *) echo "the third argument is 'flip' or nothing, not '$3'" >&2; exit 2 ;;
esac
SEG=$(readlink -f "$R/work/final_$ARM/$W.tifxyz")
OUT=$R/work/render_$ARM/${W}_${SLICES}.zarr
[ -f "$SEG/x.tif" ] || { echo "no final winding for $W" >&2; exit 2; }
[ -e "$OUT" ] && { echo "$OUT exists: a step is run once per arm" >&2; exit 2; }
IMG_SHA=$(docker run --rm --entrypoint cat "$RENDER_IMG" /opt/vcsrc/SAMPLER_SHA)
[ "$IMG_SHA" = "$RENDER_SHA" ] || { echo "image sampler sha $IMG_SHA != $RENDER_SHA" >&2; exit 2; }
mkdir -p "$B/vchome" "$R/work/ctcache" "$R/work/render_$ARM"
THREADS=${THREADS:-2}
echo "RENDER_START $(date -Is) arm=$ARM winding=$W flipped=$FLIPPED"
t0=$(date +%s)
/usr/bin/time -v docker run --rm --name "fl-render-$SCROLL-$ARM-$W" --user "$(id -u):$(id -g)" \
  --memory "${MEM_CAP:-8g}" --cpus "$THREADS" \
  -e HOME="$B/vchome" -e QT_QPA_PLATFORM=offscreen -e OMP_NUM_THREADS="$THREADS" \
  -v "$B:$B" -v "$R:$R" --entrypoint vc_render_tifxyz "$RENDER_IMG" \
  --volume "$R/work/ctcache" --remote-url "$CT_URL" --group-idx 0 --scale 1 \
  --segmentation "$SEG" --num-slices "$SLICES" --slice-step 1 "${FLIP[@]}" \
  --cache-gb "${CACHE_GB:-3}" --zarr-output "$OUT"
rc=$?
if [ $rc -eq 0 ] && [ ! -d "$OUT/2" ]; then echo "no level 2 in $OUT" >&2; rc=1; fi
gate "$ARM" "render_$W" "$rc" "$(( $(date +%s) - t0 ))" "\"flipped\": $FLIPPED, \"slices\": $SLICES"
echo "RENDER_EXIT $rc $(date -Is)"
exit $rc
