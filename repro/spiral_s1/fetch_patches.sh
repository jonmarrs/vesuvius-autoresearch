#!/usr/bin/env bash
# Fetch the 5 files of each in-ROI verified patch. Resumable; skips complete dirs.
# Each file goes to a .part until it is complete, so an interrupted run leaves
# nothing a re-run would skip as already fetched. patch_misses.txt and
# patch_no_generations.txt hold this run's entries only: a re-run retries both.
set -u
B=https://dl.ash2txt.org/datasets/spiral_datasets/PHercParis4/verified_patches
D="$(cd "$(dirname "$0")" && pwd)"
export B D
: > "$D/patch_misses.txt"
: > "$D/patch_no_generations.txt"
# generations.tif is OPTIONAL: many patches simply do not have one (the server
# lists only meta.json + x/y/z.tif for them), and nothing in spiral-fitting reads
# it. Logging its absence as a miss buried real misses under ~100% noise, which
# is a check that cannot see the thing it exists for. Absences are counted
# separately and only the four required files can produce a MISS.
one() {
  n="$1"; o="$D/verified_patches/$n"
  mkdir -p "$o"
  for f in meta.json x.tif y.tif z.tif; do
    [ -s "$o/$f" ] && continue
    curl -sf --max-time 120 --retry 3 --retry-delay 2 -o "$o/$f.part" "$B/$n/$f" \
      && mv -f "$o/$f.part" "$o/$f" \
      || { rm -f "$o/$f.part"; echo "MISS $n/$f" >> "$D/patch_misses.txt"; }
  done
  if [ ! -s "$o/generations.tif" ]; then
    curl -sf --max-time 120 -o "$o/generations.tif.part" "$B/$n/generations.tif" \
      && mv -f "$o/generations.tif.part" "$o/generations.tif" \
      || { rm -f "$o/generations.tif.part"; echo "$n" >> "$D/patch_no_generations.txt"; }
  fi
}
export -f one
xargs -P 16 -I{} bash -c 'one "$@"' _ {} < "$D/patches_in_roi.txt"
echo "DONE $(date -Is)  dirs=$(ls -1 "$D/verified_patches" 2>/dev/null|wc -l)  misses=$(wc -l < "$D/patch_misses.txt")"
du -sh "$D/verified_patches"
