#!/usr/bin/env bash
# Minimal, self-contained comparison of two vc_render_tifxyz builds on ONE crop of ONE flat surface,
# with exactly the arguments villa's render_ink.py passes (--remote-url to the public S3 ink zarr).
#
#   sampler_repro.sh <out_dir> <image>:<label> [<image>:<label> ...]
#
# Per image: fresh empty --volume and HOME (so no cache carries over between runs), a hard memory
# cap, and a disk watchdog that kills the container if its HOME passes DISK_CAP_GB. Records wall
# time, peak container memory (cgroup v2 memory.peak), bytes persisted under HOME, exit status.
# Env: FLAT (flat tifxyz dir), CROP_X, CROP_W (px), CACHE_GB (unset = binary default), MEM_CAP.
set -uo pipefail
OUT=${1:?out dir}; shift
FLAT=${FLAT:-/home/jon/openclaw-workspace/Neo-VM/spiral_out/detfit_up1/meshes/concat/w120-129_flat}
URL=https://vesuvius-challenge-open-data.s3.amazonaws.com/PHercParis4/representations/predictions/ink-3d/20260411134726-ink3d-20260428123845-v3-78k-fullsup.zarr
CROP_X=${CROP_X:-0}; CROP_W=${CROP_W:-5182}; MEM_CAP=${MEM_CAP:-24g}; DISK_CAP_GB=${DISK_CAP_GB:-150}
mkdir -p "$OUT"
[ -e "$OUT/results.tsv" ] || printf 'label\timage_id\tcache_gb\texit\twall_s\tpeak_mem_gib\thome_gib\n' > "$OUT/results.tsv"
for spec in "$@"; do
  IMG=${spec%:*}; LAB=${spec##*:}
  R=$OUT/$LAB; [ -e "$R" ] && { echo "exists: $R"; exit 3; }
  mkdir -p "$R/home" "$R/volume" "$R/tif"
  NAME=samplerrepro_${LAB}_$$
  EXTRA=(); [ -n "${CACHE_GB:-}" ] && EXTRA=(--cache-gb "$CACHE_GB")
  T0=$(date +%s)
  docker run -d --name "$NAME" --user "$(id -u):$(id -g)" --memory "$MEM_CAP" -e HOME="$R/home" \
    -v /home/jon/openclaw-workspace:/home/jon/openclaw-workspace --entrypoint vc_render_tifxyz "$IMG" \
    --scale-segmentation 4 --segmentation "$FLAT" --scale 0.25 --group-idx 1 --volume "$R/volume" \
    --tif-output "$R/tif" --num-slices 5 --remote-url "$URL" \
    --crop-x "$CROP_X" --crop-y 0 --crop-width "$CROP_W" --crop-height 0 "${EXTRA[@]}" > "$R/cid" || exit 1
  CID=$(cat "$R/cid"); CG=/sys/fs/cgroup/system.slice/docker-$CID.scope
  PEAK=0
  while [ "$(docker inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null)" = true ]; do
    [ -r "$CG/memory.peak" ] && PEAK=$(cat "$CG/memory.peak")
    HG=$(du -s --block-size=1G "$R/home" 2>/dev/null | cut -f1)
    if [ "${HG:-0}" -gt "$DISK_CAP_GB" ]; then echo "DISK_CAP $LAB: home ${HG}G > ${DISK_CAP_GB}G, killing"; docker kill "$NAME" >/dev/null; fi
    sleep 2
  done
  EXIT=$(docker inspect -f '{{.State.ExitCode}}' "$NAME"); OOM=$(docker inspect -f '{{.State.OOMKilled}}' "$NAME")
  docker logs "$NAME" > "$R/log.txt" 2>&1; docker rm "$NAME" >/dev/null
  WALL=$(( $(date +%s) - T0 ))
  HGB=$(du -s --block-size=1M "$R/home" | awk '{printf "%.2f", $1/1024}')
  printf '%s\t%s\t%s\t%s%s\t%s\t%s\t%s\n' "$LAB" "$(docker image inspect "$IMG" -f '{{.Id}}' | cut -c8-19)" \
    "${CACHE_GB:-default}" "$EXIT" "$([ "$OOM" = true ] && echo ' OOMKilled')" "$WALL" \
    "$(awk -v p="$PEAK" 'BEGIN{printf "%.2f", p/1073741824}')" "$HGB" >> "$OUT/results.tsv"
  echo "DONE $LAB exit=$EXIT oom=$OOM wall=${WALL}s"
done
