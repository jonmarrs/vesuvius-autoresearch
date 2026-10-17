#!/usr/bin/env bash
# Fetch instance-label cubes: each is a self-contained (CT, hand-labelled sheet
# instances) pair in ONE coordinate space, so no registration bridge is needed.
# Reads all_cubes.txt (one cube name per line) from beside this script; that list
# is not in the repository. Each file goes to a .part first and is moved into
# place only once complete, so an interrupted run leaves nothing a re-run would
# skip as already fetched.
set -u
B=https://dl.ash2txt.org/full-scrolls/Scroll1/PHercParis4.volpkg/volumetric-instance-labels/instance-labels-harmonized
D="$(cd "$(dirname "$0")" && pwd)"
N="${1:-12}"
head -n "$N" "$D/all_cubes.txt" | while read -r c; do
  mkdir -p "$D/$c"
  for f in "${c}_mask.nrrd" "${c}_volume.nrrd"; do
    [ -s "$D/$c/$f" ] && continue
    curl -sf --max-time 300 --retry 3 -o "$D/$c/$f.part" "$B/$c/$f" \
      && mv -f "$D/$c/$f.part" "$D/$c/$f" \
      || { rm -f "$D/$c/$f.part"; echo "MISS $c/$f"; }
  done
done
echo "DONE $(date -Is)"; du -sh "$D"
