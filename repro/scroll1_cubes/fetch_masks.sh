#!/usr/bin/env bash
# Masks only (~0.84 MB each): enough to characterise the OUTCOME variable across
# the whole population before spending on 33 MB CT volumes.
set -u
B=https://dl.ash2txt.org/full-scrolls/Scroll1/PHercParis4.volpkg/volumetric-instance-labels/instance-labels-harmonized
D="$(cd "$(dirname "$0")" && pwd)"
export B D
one(){ c="$1"; o="$D/masks/${c}_mask.nrrd"; [ -s "$o" ] && return 0
  curl -sf --max-time 120 --retry 3 -o "$o" "$B/$c/${c}_mask.nrrd" || { rm -f "$o"; echo "MISS $c"; }; }
export -f one
xargs -P 8 -I{} bash -c 'one "$@"' _ {} < "$D/all_cubes.txt"
echo "DONE $(date -Is)  masks=$(ls -1 $D/masks | wc -l)"; du -sh "$D/masks"
