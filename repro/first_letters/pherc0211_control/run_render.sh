#!/usr/bin/env bash
# Finding 118: the 66-layer render of the winning PHerc. 211 surface (three rows, revision 9), with the image and
# settings of the eligible-band renders, CT streamed from the public open-data bucket into a cache under C.
# Not flipped: this surface's normals point away from the scroll axis (99.5% of its nodes), as PHerc. 343's
# fitted windings do, so its layers are already in PHerc. 343's order.
#
# usage: run_render.sh
set -u
. "$(dirname "$0")/env.sh"
[ -f "$SEG/x.tif" ] || { echo "no surface at $SEG: run fetch_winner.sh" >&2; exit 2; }
[ -e "$RENDER" ] && { echo "$RENDER exists: the render is made once" >&2; exit 2; }
IMG_SHA=$(docker run --rm --entrypoint cat "$RENDER_IMG" /opt/vcsrc/SAMPLER_SHA)
[ "$IMG_SHA" = "$RENDER_SHA" ] || { echo "image sampler sha $IMG_SHA != $RENDER_SHA" >&2; exit 2; }
mkdir -p "$B/vchome" "$C/work/ctcache" "$(dirname "$RENDER")"
THREADS=${THREADS:-2}
echo "RENDER_START $(date -Is) surface=$SEG_NAME"
t0=$(date +%s)
/usr/bin/time -v docker run --rm --name "fl-render-pherc0211-control-$SEG_NAME" --user "$(id -u):$(id -g)" \
  --memory "${MEM_CAP:-8g}" --cpus "$THREADS" \
  -e HOME="$B/vchome" -e QT_QPA_PLATFORM=offscreen -e OMP_NUM_THREADS="$THREADS" \
  -v "$B:$B" -v "$C:$C" --entrypoint vc_render_tifxyz "$RENDER_IMG" \
  --volume "$C/work/ctcache" --remote-url "$CT_URL" --group-idx 0 --scale 1 \
  --segmentation "$SEG" --num-slices 66 --slice-step 1 \
  --cache-gb "${CACHE_GB:-3}" --zarr-output "$RENDER"
rc=$?
if [ $rc -eq 0 ] && [ ! -d "$RENDER/2" ]; then echo "no level 2 in $RENDER" >&2; rc=1; fi
control_gate render "$rc" "$(( $(date +%s) - t0 ))" "\"flipped\": false"
echo "RENDER_EXIT $rc $(date -Is)"
exit $rc
