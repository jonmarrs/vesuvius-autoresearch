#!/usr/bin/env bash
# Masks only (~0.84 MB each): enough to characterise the OUTCOME variable across
# the whole population before spending on 33 MB CT volumes. Reads all_cubes.txt
# as fetch_cubes.sh does; each mask goes to a .part until it is complete.
set -u
B=https://dl.ash2txt.org/full-scrolls/Scroll1/PHercParis4.volpkg/volumetric-instance-labels/instance-labels-harmonized
D="$(cd "$(dirname "$0")" && pwd)"
export B D
mkdir -p "$D/masks"
one(){ c="$1"; o="$D/masks/${c}_mask.nrrd"; [ -s "$o" ] && return 0
  curl -sf --max-time 120 --retry 3 -o "$o.part" "$B/$c/${c}_mask.nrrd" \
    && mv -f "$o.part" "$o" || { rm -f "$o.part"; echo "MISS $c"; }; }
export -f one
xargs -P 8 -I{} bash -c 'one "$@"' _ {} < "$D/all_cubes.txt"
echo "DONE $(date -Is)  masks=$(ls -1 $D/masks | grep -vc '\.part$')"; du -sh "$D/masks"
