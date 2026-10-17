#!/usr/bin/env bash
# Fetch winding_model/ = the `winding_inference` input the default
# dense_spacing_mode=winding_model requires. Published under a different
# directory name than the fitter's conventional relative; bridged by
# path_overrides in spiral-scroll.json rather than by renaming.
# Each file goes to a .part until it is complete, so an interrupted run leaves
# nothing a re-run would skip as already fetched.
set -u
B=https://dl.ash2txt.org/datasets/spiral_datasets/PHercParis4/winding_model
D="$(cd "$(dirname "$0")" && pwd)/winding_model"
mkdir -p "$D"
get() {
  [ -s "$D/$1" ] && return 0
  curl -sf --max-time 300 --retry 3 -o "$D/$1.part" "$B/$1" \
    && mv -f "$D/$1.part" "$D/$1" \
    || { rm -f "$D/$1.part"; echo "MISS $1"; }
}
get manifest.json
for i in 0 1 2 3 4 5 6; do
  mkdir -p "$D/shard_$i"
  for f in manifest.json crossing_level.npy crossing_offsets.npy crossing_t.npy \
           ray_origin_zyx.npy ray_step_zyx.npy seed_winding.npy; do
    get "shard_$i/$f"
  done
done
echo "DONE $(date -Is)"; du -sh "$D"
