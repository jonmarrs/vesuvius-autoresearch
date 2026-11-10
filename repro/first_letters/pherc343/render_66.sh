#!/usr/bin/env bash
# Kill test step 2: the 66-layer render of the published PHerc. 343 mesh, CT streamed from the public
# open-data bucket. Same arguments as the cloned repo's mesh/render_66_layers.sh; the binary is our
# source build at villa 75c79ac5f, whose volume-cartographer tree is identical to 41701aa (the commit
# of the author's AppImage, which villa no longer serves): 75c79ac5f = 41701aa + one docs commit.
#
# HOME is a persistent host directory because this build streams --remote-url chunks into
# $HOME/.VC3D/remote_cache (see repro/spiral_render/run_sampler_from_source_rerun.sh). The memory cap
# makes an overrun fail inside the container instead of through the host's pressure killer.
set -euo pipefail
B=/home/jon/openclaw-workspace/Neo-VM/spiral_out/first_letters/pherc343_repro
N=concat_w047-w048_R5B2_z9500-11000
IMG=vc-render:sampler-75c79ac5f
SHA=75c79ac5f506d4b9a89bcfbef8e8c0f2f0c3acb3
URL=https://vesuvius-challenge-open-data.s3.us-east-1.amazonaws.com/PHerc0343/volumes/20250521140437-8.640um-1.2m-116keV-masked.zarr
THREADS=${THREADS:-2}
CACHE_GB=${CACHE_GB:-3}
MEM_CAP=${MEM_CAP:-8g}
OUT=$B/work/${N}_66.zarr

[ -e "$OUT" ] && { echo "RENDER_ABORTED $OUT exists"; exit 3; }
IMG_SHA=$(docker run --rm --entrypoint cat "$IMG" /opt/vcsrc/SAMPLER_SHA)
[ "$IMG_SHA" = "$SHA" ] || { echo "RENDER_ABORTED image sampler sha $IMG_SHA != $SHA"; exit 3; }
mkdir -p "$B/vchome" "$B/work/ctcache"
echo "RENDER_START $(date -Is) image=$(docker image inspect "$IMG" --format '{{.Id}}') threads=$THREADS cache_gb=$CACHE_GB mem=$MEM_CAP"
/usr/bin/time -v docker run --rm --name fl343-render --user "$(id -u):$(id -g)" \
  --memory "$MEM_CAP" --cpus "$THREADS" \
  -e HOME="$B/vchome" -e QT_QPA_PLATFORM=offscreen -e OMP_NUM_THREADS="$THREADS" \
  -v "$B:$B" --entrypoint vc_render_tifxyz "$IMG" \
  --volume "$B/work/ctcache" --remote-url "$URL" --group-idx 0 --scale 1 \
  --segmentation "$B/work/mesh/$N.tifxyz" --num-slices 66 --slice-step 1 \
  --cache-gb "$CACHE_GB" --zarr-output "$OUT"
echo "RENDER_EXIT $? $(date -Is)"
du -sb "$OUT" "$B/vchome" | cat
echo RENDER_DONE
