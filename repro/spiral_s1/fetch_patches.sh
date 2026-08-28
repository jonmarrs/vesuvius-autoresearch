#!/usr/bin/env bash
# Fetch the 5 files of each in-ROI verified patch. Resumable; skips complete dirs.
set -u
B=https://dl.ash2txt.org/datasets/spiral_datasets/PHercParis4/verified_patches
D="$(cd "$(dirname "$0")" && pwd)"
export B D
one() {
  n="$1"; o="$D/verified_patches/$n"
  mkdir -p "$o"
  for f in meta.json x.tif y.tif z.tif generations.tif; do
    [ -s "$o/$f" ] && continue
    curl -sf --max-time 120 --retry 3 --retry-delay 2 -o "$o/$f" "$B/$n/$f" \
      || { rm -f "$o/$f"; echo "MISS $n/$f" >> "$D/patch_misses.txt"; }
  done
}
export -f one
xargs -P 16 -I{} bash -c 'one "$@"' _ {} < "$D/patches_in_roi.txt"
echo "DONE $(date -Is)  dirs=$(ls -1 "$D/verified_patches" 2>/dev/null|wc -l)  misses=$(wc -l < "$D/patch_misses.txt" 2>/dev/null||echo 0)"
du -sh "$D/verified_patches"
