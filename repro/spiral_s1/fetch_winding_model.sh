#!/usr/bin/env bash
# Fetch winding_model/ = the `winding_inference` input the default
# dense_spacing_mode=winding_model requires. Published under a different
# directory name than the fitter's conventional relative; bridged by
# path_overrides in spiral-scroll.json rather than by renaming.
set -u
B=https://dl.ash2txt.org/datasets/spiral_datasets/PHercParis4/winding_model
D="$(cd "$(dirname "$0")" && pwd)/winding_model"
mkdir -p "$D"
curl -sf -o "$D/manifest.json" "$B/manifest.json" || echo "MISS manifest.json"
for i in 0 1 2 3 4 5 6; do
  mkdir -p "$D/shard_$i"
  for f in manifest.json crossing_level.npy crossing_offsets.npy crossing_t.npy \
           ray_origin_zyx.npy ray_step_zyx.npy seed_winding.npy; do
    [ -s "$D/shard_$i/$f" ] && continue
    curl -sf --max-time 300 --retry 3 -o "$D/shard_$i/$f" "$B/shard_$i/$f" \
      || { rm -f "$D/shard_$i/$f"; echo "MISS shard_$i/$f"; }
  done
done
echo "DONE $(date -Is)"; du -sh "$D"
